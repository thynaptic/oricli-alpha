#!/usr/bin/env python3
"""
Oricli-Alpha JIT Knowledge Daemon - Autonomous Learning Orchestrator.
Monitors jit_absorption.jsonl and triggers remote RunPod cluster training.
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
LOG_FILE = REPO_ROOT / "jit_daemon.log"
JIT_FILE = REPO_ROOT / "oricli_core/data/jit_absorption.jsonl"
CHECKPOINT_FILE = REPO_ROOT / "jit_last_sync.json"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("oricli-jit")

class Oricli-AlphaJITDaemon:
    def __init__(self):
        self.running = True
        self.sync_threshold = 5  # Trigger training every 5 new verified facts
        self.cooldown_seconds = 7200  # Wait at least 2 hours between remote passes
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
                logger.info(f"Loaded JIT state: last sync at {self.last_sync_time} with {self.last_sync_count} lessons")
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

    def get_lesson_count(self) -> int:
        if not JIT_FILE.exists():
            return 0
        try:
            with open(JIT_FILE, "r") as f:
                return sum(1 for _ in f)
        except Exception as e:
            logger.error(f"Error counting JIT lessons: {e}")
            return 0

    def trigger_training(self, current_count: int):
        logger.info(f"🚀 Triggering remote JIT knowledge absorption (Count: {current_count})")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        
        # Use local venv python
        python_exe = REPO_ROOT / ".venv/bin/python3"
        if not python_exe.exists():
            python_exe = "python3"

        # Strategy: Use runpod_bridge to spin up a 2-node Blackwell cluster for fast absorption
        cmd = [
            str(python_exe),
            str(REPO_ROOT / "scripts/runpod_bridge.py"),
            "--cluster-size", "2",
            "--auto",
            "--min-vram", "40",
            "--max-price", "2.50",
            "--upload-to-s3",
            "--train-jit", # New flag we'll add to bridge
            "--alias", "oricli_jit_absorption"
        ]

        try:
            start_time = time.time()
            # We use check=True to catch failures, but we wrap in try/except
            process = subprocess.run(cmd, env=env, capture_output=True, text=True)
            duration = time.time() - start_time

            if process.returncode == 0:
                logger.info(f"✨ JIT Absorption complete in {duration:.2f}s.")
                self.last_sync_time = time.time()
                self.last_sync_count = current_count
                self._save_state()
            else:
                logger.error(f"❌ JIT Training failed (code {process.returncode})")
                logger.error(f"STDOUT: {process.stdout[-1000:]}")
                logger.error(f"STDERR: {process.stderr[-1000:]}")

        except Exception as e:
            logger.error(f"Exception during JIT training trigger: {e}")

    def run(self):
        logger.info("Oricli-Alpha JIT Knowledge Daemon started.")
        # Check every 5 minutes
        while self.running:
            try:
                current_count = self.get_lesson_count()
                new_lessons = current_count - self.last_sync_count
                
                if new_lessons >= self.sync_threshold:
                    # Check cooldown or check if it's late night (Off-peak training)
                    now = datetime.now()
                    is_night_window = now.hour >= 23 or now.hour <= 5
                    
                    if (time.time() - self.last_sync_time) >= self.cooldown_seconds or is_night_window:
                        self.trigger_training(current_count)
                    else:
                        wait_rem = int(self.cooldown_seconds - (time.time() - self.last_sync_time))
                        logger.info(f"JIT Threshold reached ({new_lessons} new), waiting for window or cooldown ({wait_rem}s).")
                
                time.sleep(300) 
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"JIT Daemon loop error: {e}")
                time.sleep(60)

def handle_sigterm(signum, frame):
    logger.info("Received SIGTERM, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    daemon = Oricli-AlphaJITDaemon()
    daemon.run()
