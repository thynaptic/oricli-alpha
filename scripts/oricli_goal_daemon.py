#!/usr/bin/env python3
"""
OricliAlpha Sovereign Goal Daemon - Persistent Proactive Execution.
Monitors global_objectives.jsonl and orchestrates execution across available resources.
"""

import os
import sys
import json
import time
import subprocess
import logging
import signal
import re
from pathlib import Path
from datetime import datetime

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.registry import ModuleRegistry
from oricli_core.services.budget_manager import BudgetManager

LOG_FILE = REPO_ROOT / "goal_daemon.log"
CHECKPOINT_FILE = REPO_ROOT / "goal_daemon_state.json"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("oricli-goals")

class OricliAlphaGoalDaemon:
    def __init__(self):
        self.running = True
        self.check_interval = 300  # Check every 5 minutes
        self.active_processes = {}  # {goal_id: subprocess.Popen}
        self.budget_manager = BudgetManager()
        self._load_goal_service()
        self._ensure_modules()

    def _ensure_modules(self):
        ModuleRegistry.discover_modules()
        try:
            self.cog_gen = ModuleRegistry.get_module("cognitive_generator")
        except Exception as e:
            logger.error(f"Failed to load cognitive_generator: {e}")
            self.cog_gen = None

    def _load_goal_service(self):
        try:
            from oricli_core.services.goal_service import GoalService
            self.service = GoalService()
        except ImportError:
            logger.error("Failed to load GoalService. Daemon cannot run.")
            sys.exit(1)

    def _check_active_processes(self):
        """Monitor running processes and handle resilience/migration."""
        completed_goals = []
        for goal_id, process in self.active_processes.items():
            retcode = process.poll()
            if retcode is not None:
                # Process finished
                completed_goals.append(goal_id)
                if retcode == 0:
                    logger.info(f"Goal {goal_id} execution process completed successfully.")
                else:
                    logger.warning(f"Goal {goal_id} execution process exited with code {retcode}.")
                    # If it was a remote execution that failed (e.g., pod preemption),
                    # the goal is still 'active' or 'pending' in the service,
                    # so it will be picked up again in the next cycle,
                    # automatically migrating to a new region via runpod_bridge's --auto flag.
                    logger.info(f"Goal {goal_id} will be retried/migrated on next cycle if not completed.")
        
        for goal_id in completed_goals:
            del self.active_processes[goal_id]

    def process_pending_goals(self):
        """Find pending goals and initiate execution."""
        self._check_active_processes()
        
        pending = self.service.list_objectives(status="pending")
        active = self.service.list_objectives(status="active")
        
        # Filter out goals that are already being processed by this daemon instance
        pending = [g for g in pending if g["id"] not in self.active_processes]
        active = [g for g in active if g["id"] not in self.active_processes]
        
        if not pending and not active:
            return

        logger.info(f"Found {len(pending)} pending and {len(active)} active objectives not currently processing.")
        
        goals_to_process = sorted(pending + active, key=lambda x: x.get("priority", 1), reverse=True)
        
        for goal in goals_to_process:
            self._evaluate_and_execute_goal(goal)

    def _evaluate_and_execute_goal(self, goal):
        goal_id = goal["id"]
        goal_text = goal["goal"]
        
        logger.info(f"🚀 Evaluating execution strategy for Goal {goal_id}: {goal_text[:50]}...")
        
        requires_gpu = False
        
        # Ask cognitive generator to evaluate resource needs
        if self.cog_gen:
            eval_prompt = f"""
            Evaluate the following goal and determine if it requires a high-end GPU (e.g., training a large model, massive context processing) or if it can be solved locally on CPU (e.g., symbolic logic, web research, scripting).
            
            GOAL: {goal_text}
            
            Output a JSON object: {{"requires_gpu": true/false, "reason": "..."}}
            """
            try:
                res = self.cog_gen.execute("generate_response", {"input": eval_prompt})
                text = res.get("text", "")
                json_match = re.search(r"\{.*\}", text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    requires_gpu = data.get("requires_gpu", False)
                    logger.info(f"Evaluation: Requires GPU? {requires_gpu} ({data.get('reason', '')})")
            except Exception as e:
                logger.warning(f"Failed to evaluate goal resources: {e}. Defaulting to local execution.")
        
        if requires_gpu:
            self._execute_goal_on_remote(goal)
        else:
            self._execute_goal_locally(goal)

    def _execute_goal_locally(self, goal):
        goal_id = goal["id"]
        logger.info(f"💻 Executing Goal {goal_id} locally (Cost: 0 credits).")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        
        python_exe = REPO_ROOT / ".venv/bin/python3"
        if not python_exe.exists():
            python_exe = "python3"

        cmd = [
            str(python_exe),
            str(REPO_ROOT / "scripts/execute_local_goal.py"),
            "--goal-id", goal_id
        ]

        try:
            process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.active_processes[goal_id] = process
            logger.info(f"Local executor launched for Goal {goal_id}. PID: {process.pid}")
        except Exception as e:
            logger.error(f"Failed to launch local goal execution: {e}")

    def _execute_goal_on_remote(self, goal):
        goal_id = goal["id"]
        goal_text = goal["goal"]
        
        estimated_cost = 1.50
        
        if not self.budget_manager.deduct(estimated_cost, reason=f"Remote execution for goal {goal_id}"):
            logger.warning(f"Insufficient budget for remote execution of goal {goal_id}. Falling back to local execution.")
            self._execute_goal_locally(goal)
            return
            
        logger.info(f"☁️ Orchestrating remote execution for Goal {goal_id} (Cost: {estimated_cost} credits).")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        
        python_exe = REPO_ROOT / ".venv/bin/python3"
        if not python_exe.exists():
            python_exe = "python3"

        cmd = [
            str(python_exe),
            str(REPO_ROOT / "scripts/runpod_bridge.py"),
            "--cluster-size", "1",
            "--auto",
            "--min-vram", "24",
            "--max-price", "1.50",
            "--upload-to-s3",
            "--execute-goal", goal_id,
            "--alias", f"oricli_goal_{goal_id}"
        ]

        try:
            process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.active_processes[goal_id] = process
            logger.info(f"Bridge launched for Goal {goal_id}. PID: {process.pid}")
        except Exception as e:
            logger.error(f"Failed to launch remote goal execution: {e}")
            # Refund budget if launch failed
            self.budget_manager.add(estimated_cost, reason=f"Refund: Failed to launch goal {goal_id}")

    def run(self):
        logger.info("OricliAlpha Sovereign Goal Daemon started.")
        while self.running:
            try:
                self.process_pending_goals()
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Goal Daemon loop error: {e}")
                time.sleep(60)

def handle_sigterm(signum, frame):
    logger.info("Received SIGTERM, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    daemon = OricliAlphaGoalDaemon()
    daemon.run()
