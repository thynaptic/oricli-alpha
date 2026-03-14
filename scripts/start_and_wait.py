import subprocess
import time
import sys
import httpx

def start_server():
    print("Starting OricliAlpha API server on port 8080...")
    cmd = [
        "python3", "-m", "oricli_core.api.server",
        "--port", "8080",
        "--no-auto-port",
        "--log-level", "info"
    ]
    env = {
        **subprocess.os.environ,
        "PYTHONPATH": ".",
        "NEO4J_PASSWORD": "password",
        "MAVAIA_API_KEY": "test_key"
    }
    
    # Use Popen to run in background
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=open("server_stdout.log", "w"),
        stderr=open("server_stderr.log", "w"),
        preexec_fn=subprocess.os.setpgrp
    )
    
    max_retries = 60
    for i in range(max_retries):
        try:
            print(f"Checking health (attempt {i+1}/{max_retries})...")
            resp = httpx.get("http://localhost:8080/health", timeout=1.0)
            if resp.status_code == 200:
                print("Server is healthy!")
                return True
        except Exception:
            pass
        time.sleep(2)
    
    print("Server failed to start in time.")
    return False

if __name__ == "__main__":
    if start_server():
        sys.exit(0)
    else:
        sys.exit(1)
