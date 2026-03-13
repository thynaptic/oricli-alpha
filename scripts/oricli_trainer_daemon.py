#!/usr/bin/env python3
"""
Oricli-Alpha Trainer Daemon - Background RFAL Alignment Orchestrator.
Monitors rfal_lessons.jsonl and triggers local CPU training passes.
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
LOG_FILE = REPO_ROOT / "trainer_daemon.log"
LESSONS_FILE = REPO_ROOT / "oricli_core/data/rfal_lessons.jsonl"
CHECKPOINT_FILE = REPO_ROOT / "trainer_last_sync.json"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("oricli-trainer")

class Oricli-AlphaTrainerDaemon:
    def __init__(self):
        self.running = True
        self.sync_threshold = 20  # Trigger training every 20 new lessons
        self.cooldown_seconds = 3600  # Wait at least 1 hour between passes
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
                logger.info(f"Loaded daemon state: last sync at {self.last_sync_time} with {self.last_sync_count} lessons")
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
        if not LESSONS_FILE.exists():
            return 0
        try:
            with open(LESSONS_FILE, "r") as f:
                return sum(1 for _ in f)
        except Exception as e:
            logger.error(f"Error counting lessons: {e}")
            return 0

    def trigger_training(self, current_count: int):
        logger.info(f"🚀 Triggering background RFAL alignment (Count: {current_count})")
        
        # Ensure heavy modules are enabled for the training process
        env = os.environ.copy()
        env["MAVAIA_ENABLE_HEAVY_MODULES"] = "true"
        env["PYTHONPATH"] = str(REPO_ROOT)
        
        # Use local venv python
        python_exe = REPO_ROOT / ".venv/bin/python3"
        if not python_exe.exists():
            python_exe = "python3"

        cmd = [
            str(python_exe),
            str(REPO_ROOT / "scripts/train_neural_text_generator.py"),
            "--dpo",
            "--dpo-data", str(LESSONS_FILE),
            "--epochs", "1",
            "--batch-size", "1",
            "--adapter-name", "rfal_alignment_local",
            "--plain-output"
        ]

        try:
            # We run this synchronously here as the daemon's job is to manage this process
            # It's already in the background relative to the user.
            start_time = time.time()
            process = subprocess.run(cmd, env=env, capture_output=True, text=True)
            duration = time.time() - start_time

            if process.returncode == 0:
                logger.info(f"✨ Training complete in {duration:.2f}s.")
                self.last_sync_time = time.time()
                self.last_sync_count = current_count
                self._save_state()
            else:
                logger.error(f"❌ Training failed (code {process.returncode})")
                logger.error(f"STDOUT: {process.stdout[-500:]}")
                logger.error(f"STDERR: {process.stderr[-500:]}")

        except Exception as e:
            logger.error(f"Exception during training trigger: {e}")

    def run(self):
        logger.info("Oricli-Alpha Trainer Daemon started.")
        while self.running:
            try:
                current_count = self.get_lesson_count()
                new_lessons = current_count - self.last_sync_count
                
                if new_lessons >= self.sync_threshold:
                    # Check cooldown
                    if (time.time() - self.last_sync_time) >= self.cooldown_seconds:
                        self.trigger_training(current_count)
                    else:
                        wait_rem = int(self.cooldown_seconds - (time.time() - self.last_sync_time))
                        logger.info(f"Threshold reached ({new_lessons} new), but in cooldown. {wait_rem}s remaining.")
                
                # Check once per minute
                time.sleep(60)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Daemon loop error: {e}")
                time.sleep(30)

def handle_sigterm(signum, frame):
    logger.info("Received SIGTERM, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    daemon = Oricli-AlphaTrainerDaemon()
    daemon.run()
