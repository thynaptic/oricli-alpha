#!/usr/bin/env python3
"""
OricliAlpha API Daemon - Persistent interface for completions and routing.
"""

import os
import sys
import subprocess
import logging
import signal
from pathlib import Path

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = REPO_ROOT / "api_daemon.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("oricli-api")

class OricliAlphaAPIDaemon:
    def __init__(self):
        self.process = None

    def start(self):
        logger.info("Starting OricliAlpha API server...")
        
        env = os.environ.copy()
        env["MAVAIA_ENABLE_HEAVY_MODULES"] = "true"
        env["PYTHONPATH"] = str(REPO_ROOT)
        
        # Use local venv python
        python_exe = REPO_ROOT / ".venv/bin/python3"
        if not python_exe.exists():
            python_exe = "python3"

        cmd = [
            str(python_exe),
            "-m", "oricli_core.api.server",
            "--host", "0.0.0.0",
            "--port", "8081"
        ]

        try:
            # Run the API server as a subprocess
            self.process = subprocess.Popen(
                cmd, 
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Log output in a separate thread
            import threading
            def log_output():
                for line in self.process.stdout:
                    logger.info(f"[API] {line.strip()}")
            
            threading.Thread(target=log_output, daemon=True).start()
            
            logger.info("OricliAlpha API server process started.")
            self.process.wait()
            
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")

    def stop(self):
        if self.process:
            logger.info("Stopping OricliAlpha API server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            logger.info("API server stopped.")

def handle_sigterm(signum, frame):
    daemon.stop()
    sys.exit(0)

if __name__ == "__main__":
    daemon = OricliAlphaAPIDaemon()
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)
    daemon.start()
