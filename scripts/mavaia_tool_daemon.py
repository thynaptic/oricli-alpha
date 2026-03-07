#!/usr/bin/env python3
"""
Mavaia ToolBench Daemon - Autonomous Tool-Efficacy Orchestrator.
Monitors tool_corrections.jsonl and triggers remote RunPod cluster training.
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
LOG_FILE = REPO_ROOT / "tool_daemon.log"
CORRECTIONS_FILE = REPO_ROOT / "mavaia_core/data/tool_corrections.jsonl"
CHECKPOINT_FILE = REPO_ROOT / "tool_last_sync.json"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("mavaia-tool")

class MavaiaToolDaemon:
    def __init__(self):
        self.running = True
        self.sync_threshold = 10  # Trigger training every 10 tool-use corrections
        self.cooldown_seconds = 14400  # Wait at least 4 hours between tool-specific passes
        self.last_sync_time = 0
        self.last_sync_count = 0
        
        # Load state
        self._load_state()

    def _load_state(self):
        if CHECKPOINT_FILE.exists():
            try:
                state = json.loads(CHECKPOINT_FILE.read_text())
                self.last_sync_time = state.get("last_sync_time", 0)
                self.last_sync_count = state.get("last_sync_count", 0)
                logger.info(f"Loaded Tool Daemon state: last sync at {self.last_sync_time} with {self.last_sync_count} corrections")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    def _save_state(self):
        try:
            state = {
                "last_sync_time": self.last_sync_time,
                "last_sync_count": self.last_sync_count,
                "updated_at": str(datetime.now())
            }
            CHECKPOINT_FILE.write_text(json.dumps(state, indent=2))
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def get_correction_count(self) -> int:
        if not CORRECTIONS_FILE.exists():
            return 0
        try:
            with open(CORRECTIONS_FILE, "r") as f:
                return sum(1 for _ in f)
        except Exception as e:
            logger.error(f"Error counting corrections: {e}")
            return 0

    def trigger_training(self, current_count: int):
        logger.info(f"🚀 Triggering remote Tool-Efficacy training (Corrections: {current_count})")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        
        # Use local venv python
        python_exe = REPO_ROOT / ".venv/bin/python3"
        if not python_exe.exists():
            python_exe = "python3"

        # Strategy: Use runpod_bridge to train a 'tool_efficacy' adapter
        cmd = [
            str(python_exe),
            str(REPO_ROOT / "scripts/runpod_bridge.py"),
            "--cluster-size", "2",
            "--auto",
            "--min-vram", "40",
            "--max-price", "2.50",
            "--upload-to-s3",
            "--train-tool-bench", # New flag to be added to bridge
            "--alias", "mavaia_tool_tuning"
        ]

        try:
            start_time = time.time()
            process = subprocess.run(cmd, env=env, capture_output=True, text=True)
            duration = time.time() - start_time

            if process.returncode == 0:
                logger.info(f"✨ Tool-Efficacy training complete in {duration:.2f}s.")
                self.last_sync_time = time.time()
                self.last_sync_count = current_count
                self._save_state()
            else:
                logger.error(f"❌ Tool training failed (code {process.returncode})")
                logger.error(f"STDOUT: {process.stdout[-1000:]}")
                logger.error(f"STDERR: {process.stderr[-1000:]}")

        except Exception as e:
            logger.error(f"Exception during tool training trigger: {e}")

    def run(self):
        logger.info("Mavaia ToolBench Daemon started.")
        while self.running:
            try:
                current_count = self.get_correction_count()
                new_corrections = current_count - self.last_sync_count
                
                if new_corrections >= self.sync_threshold:
                    if (time.time() - self.last_sync_time) >= self.cooldown_seconds:
                        self.trigger_training(current_count)
                    else:
                        wait_rem = int(self.cooldown_seconds - (time.time() - self.last_sync_time))
                        logger.info(f"Threshold reached ({new_corrections} new), in cooldown ({wait_rem}s remaining).")
                
                time.sleep(600) # Check every 10 minutes
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Tool Daemon loop error: {e}")
                time.sleep(60)

def handle_sigterm(signum, frame):
    logger.info("Received SIGTERM, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    daemon = MavaiaToolDaemon()
    daemon.run()
