#!/usr/bin/env python3
"""
Mavaia Sovereign Goal Daemon - Persistent Proactive Execution.
Monitors global_objectives.jsonl and orchestrates execution across available resources.
"""

import os
import sys
import json
import time
import subprocess
import logging
import signal
from pathlib import Path
from datetime import datetime

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

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
logger = logging.getLogger("mavaia-goals")

class MavaiaGoalDaemon:
    def __init__(self):
        self.running = True
        self.check_interval = 300  # Check every 5 minutes
        self._load_goal_service()

    def _load_goal_service(self):
        try:
            from mavaia_core.services.goal_service import GoalService
            self.service = GoalService()
        except ImportError:
            logger.error("Failed to load GoalService. Daemon cannot run.")
            sys.exit(1)

    def process_pending_goals(self):
        """Find pending goals and initiate execution."""
        pending = self.service.list_objectives(status="pending")
        active = self.service.list_objectives(status="active")
        
        if not pending and not active:
            return

        logger.info(f"Found {len(pending)} pending and {len(active)} active objectives.")
        
        # Strategy: Orchestrate execution via runpod_bridge
        # We start with the highest priority pending goal
        goals_to_process = sorted(pending + active, key=lambda x: x.get("priority", 1), reverse=True)
        
        for goal in goals_to_process:
            self._execute_goal_on_remote(goal)

    def _execute_goal_on_remote(self, goal):
        goal_id = goal["id"]
        goal_text = goal["goal"]
        
        logger.info(f"🚀 Orchestrating execution for Goal {goal_id}: {goal_text[:50]}...")
        
        # Ensure heavy modules are enabled
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        
        python_exe = REPO_ROOT / ".venv/bin/python3"
        if not python_exe.exists():
            python_exe = "python3"

        # Strategy: Use runpod_bridge to spin up a specialized execution node
        # We pass the --execute-goal flag (to be added)
        cmd = [
            str(python_exe),
            str(REPO_ROOT / "scripts/runpod_bridge.py"),
            "--cluster-size", "1",
            "--auto",
            "--min-vram", "24",
            "--max-price", "1.50",
            "--upload-to-s3",
            "--execute-goal", goal_id,
            "--alias", f"mavaia_goal_{goal_id}"
        ]

        try:
            # Note: The daemon triggers the bridge, which handles the remote execution
            # In a real multi-day scenario, the bridge would start the pod, 
            # the pod would pull the goal state, do N steps, then hibernate/terminate.
            process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # We don't want the daemon to block forever on one goal if it's multi-day
            # but we'll monitor the bridge's initial launch
            logger.info(f"Bridge launched for Goal {goal_id}. PID: {process.pid}")
            
            # For now, we wait for the bridge to finish one 'pass'
            # In future, we could handle asynchronous bridge monitoring
            
        except Exception as e:
            logger.error(f"Failed to launch goal execution: {e}")

    def run(self):
        logger.info("Mavaia Sovereign Goal Daemon started.")
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
    daemon = MavaiaGoalDaemon()
    daemon.run()
