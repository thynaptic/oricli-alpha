import os
import sys
import json
import time
import subprocess
import argparse
import requests
import threading
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Load environment variables (hand-rolled simple loader)
def load_dotenv(path: Path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            key, _, value = line.partition("=")
            os.environ[key.strip()] = value.strip()

load_dotenv(REPO_ROOT / ".env")

# RunPod API configuration
RUNPOD_API_KEY = os.environ.get("Mavaia_Key")
RUNPOD_ENDPOINT = "https://api.runpod.io/graphql"

class RunPodBridge:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else ""
        }

    def _query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        response = requests.post(
            RUNPOD_ENDPOINT,
            json={"query": query, "variables": variables},
            headers=self.headers
        )
        data = response.json()
        if "errors" in data:
            print(f"[!] RunPod GraphQL Error: {json.dumps(data['errors'], indent=2)}")
        
        response.raise_for_status()
        return data

    def get_pods(self) -> List[Dict]:
        query = """
        query MyPods {
          myself {
            pods {
              id
              name
              runtime {
                uptimeInSeconds
                ports {
                  ip
                  isIpPublic
                  privatePort
                  publicPort
                }
              }
            }
          }
        }
        """
        result = self._query(query)
        return result.get("data", {}).get("myself", {}).get("pods", [])

    def create_pod(
        self,
        name: str,
        gpu_type_id: str,
        template_id: Optional[str] = None,
        image: Optional[str] = None,
        volume_mount_path: str = "/workspace",
        ssh_key_value: Optional[str] = None,
        data_center_id: Optional[str] = None,
        volume_id: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        input_fields = [
            f'name: "{name}"',
            f'gpuTypeId: "{gpu_type_id}"',
            f'gpuCount: 1',
            f'volumeInGb: 20',
            f'containerDiskInGb: 10',
            f'volumeMountPath: "{volume_mount_path}"'
        ]
        
        env_vars = []
        if env:
            for k, v in env.items():
                if v:
                    env_vars.append(f'{{key: "{k}", value: "{str(v)}"}}')
        if ssh_key_value:
            env_vars.append(f'{{key: "PUBLIC_KEY", value: "{ssh_key_value}"}}')
            env_vars.append(f'{{key: "SSH_PUBLIC_KEY", value: "{ssh_key_value}"}}')

        if env_vars:
            input_fields.append(f'env: [{", ".join(env_vars)}]')

        if data_center_id:
            input_fields.append(f'dataCenterId: "{data_center_id}"')
        if volume_id:
            input_fields.append(f'volumeId: "{volume_id}"')
        
        if template_id:
            input_fields.append(f'templateId: "{template_id}"')
            input_fields.append('ports: "22/tcp"')
        elif image:
            input_fields.append(f'imageName: "{image}"')
            input_fields.append('ports: "22/tcp"')
            input_fields.append('dockerArgs: ""')
        
        input_str = ", ".join(input_fields)
        
        query = f"""
        mutation {{
          podFindAndDeployOnDemand(input: {{ {input_str} }}) {{
            id
            imageName
            name
          }}
        }}
        """
        result = self._query(query)
        return result.get("data", {}).get("podFindAndDeployOnDemand")

    def stop_pod(self, pod_id: str):
        query = f"""
        mutation {{
          podStop(input: {{ podId: "{pod_id}" }}) {{
            id
          }}
        }}
        """
        return self._query(query)

    def terminate_pod(self, pod_id: str):
        query = f"""
        mutation {{
          podTerminate(input: {{ podId: "{pod_id}" }})
        }}
        """
        return self._query(query)

def setup_pod_env(pod_ip: str, pod_port: int, ssh_key: str, pod_id: str = None, proxy: str = None):
    print(f"[*] Setting up environment on pod {pod_ip}:{pod_port}...")
    
    # Try direct first, then proxy
    connection_methods = []
    if proxy:
        connection_methods.append({"host": proxy, "port": "22"})
    else:
        connection_methods.append({"host": f"root@{pod_ip}", "port": str(pod_port)})
        if pod_id:
            connection_methods.append({"host": f"{pod_id}-22@ssh.runpod.io", "port": "22"})
        
    # Use SSH to install deps with retries
    max_retries = 30
    for i in range(max_retries):
        method = connection_methods[0] if i % 2 == 0 or len(connection_methods) == 1 else connection_methods[1]
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "PasswordAuthentication=no",
            "-i", ssh_key,
            "-p", method["port"],
            method["host"],
            "apt-get update && apt-get install -y rsync python3-venv curl awscli && python3 -m pip install --upgrade pip"
        ]
        
        try:
            subprocess.run(ssh_cmd, check=True)
            return
        except subprocess.CalledProcessError as e:
            if e.returncode == 255 and i < max_retries - 1:
                print(f"[*] SSH method {method['host']} failed. Retrying... ({i+1}/{max_retries})")
                time.sleep(10)
            else:
                raise e

def ensure_mavaia_installed(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    workdir: str,
    pod_id: str = None,
    proxy: str = None,
):
    print("[*] Installing mavaia_core + training deps in pod venv...")

    if proxy:
        host = proxy
        port = "22"
    else:
        host = f"root@{pod_ip}"
        port = str(pod_port)

    install_cmd = (
        "set -e; "
        f"cd {workdir}/mavaia; "
        "if [ -f .mavaia_initialized ]; then "
        "  echo '[*] Mavaia already initialized, skipping install.'; "
        "else "
        "  python3 -m venv .venv; "
        "  . .venv/bin/activate; "
        "  pip install --upgrade pip setuptools wheel; "
        "  pip install -e '.[train_neural]' torch transformers; "
        "  .venv/bin/python -c \"import mavaia_core; print('mavaia_core_ok')\"; "
        "  touch .mavaia_initialized; "
        "fi"
    )

    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "PasswordAuthentication=no",
        "-i", ssh_key,
        "-p", port,
        host,
        install_cmd,
    ]

    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError as e:
        if (not proxy) and pod_id and e.returncode == 255:
            print("[*] Direct SSH failed (255), trying via fallback proxy...")
            ssh_cmd[9] = "22"
            ssh_cmd[10] = f"{pod_id}-22@ssh.runpod.io"
            subprocess.run(ssh_cmd, check=True)
        else:
            raise e


def setup_ollama(pod_ip: str, pod_port: int, ssh_key: str, model_name: str, model_dir: str, pod_id: str = None, proxy: str = None):
    print(f"[*] Setting up Ollama (model: {model_name})...")

    ollama_cmd = (
        "set -e; "
        f"export OLLAMA_MODELS={model_dir}; "
        f"mkdir -p {model_dir}; "
        "if ! command -v ollama >/dev/null 2>&1; then "
        "  curl -fsSL https://ollama.com/install.sh | sh; "
        "fi; "
        "nohup ollama serve > /var/log/ollama.log 2>&1 & "
        "sleep 2; "
        "ollama list >/dev/null 2>&1 || true; "
        f"ollama pull {model_name}; "
        "echo ollama_ready"
    )

    if proxy:
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "PasswordAuthentication=no",
            "-i", ssh_key,
            "-p", "22",
            proxy,
            ollama_cmd,
        ]
        subprocess.run(ssh_cmd, check=True)
        return

    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "PasswordAuthentication=no",
        "-i", ssh_key,
        "-p", str(pod_port),
        f"root@{pod_ip}",
        ollama_cmd,
    ]
    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError as e:
        if pod_id and e.returncode == 255:
            print("[*] Direct SSH failed (255), trying via fallback proxy...")
            ssh_cmd[9] = "22"
            ssh_cmd[10] = f"{pod_id}-22@ssh.runpod.io"
            subprocess.run(ssh_cmd, check=True)
        else:
            raise e


def _aws_env_flags(region: str, endpoint_url: str) -> str:
    flags = []
    if region:
        flags.append(f"--region {region}")
    if endpoint_url:
        flags.append(f"--endpoint-url {endpoint_url}")
    return " ".join(flags)


def s3_sync_local_to_bucket(
    local_path: Path,
    bucket: str,
    prefix: str,
    region: str,
    endpoint_url: str,
):
    print("[*] Syncing local repo to S3...")
    cmd = [
        "aws",
        "s3",
        "sync",
        str(local_path) + "/",
        f"s3://{bucket}/{prefix}",
        "--delete",
        "--exclude", ".git/*",
        "--exclude", ".venv/*",
        "--exclude", "__pycache__/*",
        "--exclude", "*.pyc",
    ]
    if region:
        cmd.extend(["--region", region])
    if endpoint_url:
        cmd.extend(["--endpoint-url", endpoint_url])
    subprocess.run(cmd, check=True)


def s3_sync_pod(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    bucket: str,
    prefix: str,
    region: str,
    endpoint_url: str,
    direction: str,
    pod_id: str = None,
    proxy: str = None,
    src: str = "/workspace/mavaia",
):
    if direction not in ("pull", "push"):
        raise ValueError("direction must be pull or push")

    flags = _aws_env_flags(region, endpoint_url)
    if direction == "pull":
        cmd = f"aws s3 sync s3://{bucket}/{prefix} {src} {flags}"
    else:
        cmd = f"aws s3 sync {src} s3://{bucket}/{prefix} {flags}"

    if proxy:
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "PasswordAuthentication=no",
            "-i", ssh_key,
            "-p", "22",
            proxy,
            cmd,
        ]
        subprocess.run(ssh_cmd, check=True)
        return

    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "PasswordAuthentication=no",
        "-i", ssh_key,
        "-p", str(pod_port),
        f"root@{pod_ip}",
        cmd,
    ]
    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError as e:
        if pod_id and e.returncode == 255:
            ssh_cmd[9] = "22"
            ssh_cmd[10] = f"{pod_id}-22@ssh.runpod.io"
            subprocess.run(ssh_cmd, check=True)
        else:
            raise e

def sync_code(pod_ip: str, pod_port: int, ssh_key: str, local_path: Path, workdir: str, pod_id: str = None, proxy: str = None):
    print(f"[*] Syncing code to pod...")
    
    if proxy:
        rsync_cmd = [
            "rsync", "-avz", "--progress",
            "--no-owner", "--no-group", "--no-perms",
            "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22",
            "--exclude", ".git", "--exclude", "__pycache__", "--exclude", ".venv",
            str(local_path) + "/",
            f"{proxy}:{workdir}/mavaia"
        ]
        subprocess.run(rsync_cmd, check=True)
        return
        
    rsync_cmd = [
        "rsync", "-avz", "--progress",
        "--no-owner", "--no-group", "--no-perms",
        "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p {pod_port}",
        "--exclude", ".git", "--exclude", "__pycache__", "--exclude", ".venv",
        "--exclude", ".cursor", "--exclude", ".vscode", "--exclude", "tmp",
        str(local_path) + "/",
        f"root@{pod_ip}:{workdir}/mavaia"
    ]
    try:
        proc = subprocess.run(rsync_cmd, check=False)
        if proc.returncode != 0 and proc.returncode != 23:
            # 23 means partial transfer (often harmless for locked local files)
            raise subprocess.CalledProcessError(proc.returncode, rsync_cmd)
        elif proc.returncode == 23:
            print("[*] Rsync finished with status 23 (Partial Transfer). This is usually ignoring locked/special files and is safe.")

    except subprocess.CalledProcessError:
        if pod_id:
            print("[*] Direct rsync failed, trying via fallback proxy...")
            rsync_cmd[4] = f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22"
            rsync_cmd[-1] = f"{pod_id}-22@ssh.runpod.io:{workdir}/mavaia"
            proc = subprocess.run(rsync_cmd, check=False)
            if proc.returncode != 0 and proc.returncode != 23:
                raise subprocess.CalledProcessError(proc.returncode, rsync_cmd)
            elif proc.returncode == 23:
                print("[*] Rsync finished with status 23 (Partial Transfer) via proxy. Safe to proceed.")

def remote_train(pod_ip: str, pod_port: int, ssh_key: str, train_args: List[str], workdir: str, pod_id: str = None, proxy: str = None):
    print(f"[*] Starting training on remote pod...")
    if train_args and train_args[0] == "--":
        train_args = train_args[1:]
    args_str = " ".join(train_args)
    
    if proxy:
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "PasswordAuthentication=no",
            "-i", ssh_key,
            "-p", "22",
            proxy,
            f"cd {workdir}/mavaia && {workdir}/mavaia/.venv/bin/python scripts/train_neural_text_generator.py {args_str}"
        ]
        subprocess.run(ssh_cmd, check=True)
        return

    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "PasswordAuthentication=no",
        "-i", ssh_key,
        "-p", str(pod_port),
        f"root@{pod_ip}",
        f"cd {workdir}/mavaia && {workdir}/mavaia/.venv/bin/python scripts/train_neural_text_generator.py {args_str}"
    ]
    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError as e:
        if pod_id and e.returncode == 255:
            print("[*] Direct SSH failed (255), trying via fallback proxy...")
            ssh_cmd[8] = "22"
            ssh_cmd[9] = f"{pod_id}-22@ssh.runpod.io"
            subprocess.run(ssh_cmd, check=True)
        else:
            raise e

def get_artifacts(pod_ip: str, pod_port: int, ssh_key: str, local_path: Path, workdir: str, pod_id: str = None, proxy: str = None):
    print(f"[*] Pulling trained models from pod...")

    dest_dir = local_path / "models" / "neural_text_generator_remote"
    dest_dir.mkdir(parents=True, exist_ok=True)

    if proxy:
        scp_cmd = [
            "rsync", "-avz",
            "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22",
            f"{proxy}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
            str(dest_dir) + "/",
        ]
        subprocess.run(scp_cmd, check=True)
        return

    scp_cmd = [
        "rsync", "-avz",
        "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p {pod_port}",
        f"root@{pod_ip}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
        str(dest_dir) + "/",
    ]
    try:
            proc = subprocess.run(scp_cmd, check=False)
            if proc.returncode != 0 and proc.returncode != 23:
                raise subprocess.CalledProcessError(proc.returncode, scp_cmd)
            elif proc.returncode == 23:
                print("[*] Rsync finished with status 23 (Partial Transfer). Safe to proceed.")
    except subprocess.CalledProcessError:
        if pod_id:
            print("[*] Direct rsync failed, trying via fallback proxy...")
            scp_cmd[3] = f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22"
            scp_cmd[4] = f"{pod_id}-22@ssh.runpod.io:{workdir}/mavaia/mavaia_core/models/neural_text_generator/"
            proc = subprocess.run(scp_cmd, check=False)
            if proc.returncode != 0 and proc.returncode != 23:
                raise subprocess.CalledProcessError(proc.returncode, scp_cmd)
            elif proc.returncode == 23:
                print("[*] Rsync finished with status 23 (Partial Transfer) via proxy. Safe to proceed.")

def sync_training_data(pod_ip: str, pod_port: int, ssh_key: str, local_path: Path, workdir: str, pod_id: str = None, proxy: str = None):
    print("[*] Syncing training data (runs, checkpoints, cache) from pod...")

    dest_dir = local_path / "models" / "neural_text_generator_remote" / "training_data"
    dest_dir.mkdir(parents=True, exist_ok=True)

    if proxy:
        rsync_cmd = [
            "rsync", "-avz",
            "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22",
            f"{proxy}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
            str(dest_dir / "models") + "/",
        ]
        cache_cmd = [
            "rsync", "-avz",
            "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22",
            f"{proxy}:{workdir}/mavaia/mavaia_core/data/",
            str(dest_dir / "data_cache") + "/",
        ]
        for cmd in (rsync_cmd, cache_cmd):
            proc = subprocess.run(cmd, check=False)
            if proc.returncode not in (0, 23):
                raise subprocess.CalledProcessError(proc.returncode, cmd)
            if proc.returncode == 23:
                print("[*] Rsync finished with status 23 (Partial Transfer). Safe to proceed.")
        return

    rsync_cmd = [
        "rsync", "-avz",
        "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p {pod_port}",
        f"root@{pod_ip}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
        str(dest_dir / "models") + "/",
    ]
    cache_cmd = [
        "rsync", "-avz",
        "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p {pod_port}",
        f"root@{pod_ip}:{workdir}/mavaia/mavaia_core/data/",
        str(dest_dir / "data_cache") + "/",
    ]
    try:
        for cmd in (rsync_cmd, cache_cmd):
            proc = subprocess.run(cmd, check=False)
            if proc.returncode not in (0, 23):
                raise subprocess.CalledProcessError(proc.returncode, cmd)
            if proc.returncode == 23:
                print("[*] Rsync finished with status 23 (Partial Transfer). Safe to proceed.")
    except subprocess.CalledProcessError:
        if pod_id:
            print("[*] Direct rsync failed, trying via fallback proxy...")
            rsync_cmd[3] = f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22"
            rsync_cmd[4] = f"{pod_id}-22@ssh.runpod.io:{workdir}/mavaia/mavaia_core/models/neural_text_generator/"
            cache_cmd[3] = f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22"
            cache_cmd[4] = f"{pod_id}-22@ssh.runpod.io:{workdir}/mavaia/mavaia_core/data/"
            for cmd in (rsync_cmd, cache_cmd):
                proc = subprocess.run(cmd, check=False)
                if proc.returncode not in (0, 23):
                    raise subprocess.CalledProcessError(proc.returncode, cmd)
                if proc.returncode == 23:
                    print("[*] Rsync finished with status 23 (Partial Transfer) via proxy. Safe to proceed.")

def remote_snapshot(pod_ip: str, pod_port: int, ssh_key: str, workdir: str, pod_id: str = None, proxy: str = None):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    snapshot_cmd = (
        "set -e; "
        f"cd {workdir}/mavaia; "
        f"SNAP_DIR={workdir}/mavaia/mavaia_core/models/neural_text_generator/snapshots/{{ts}}; "
        "mkdir -p \"$SNAP_DIR\"; "
        "cp -a mavaia_core/models/neural_text_generator/checkpoints \"$SNAP_DIR\" 2>/dev/null || true; "
        "cp -a mavaia_core/models/neural_text_generator/runs \"$SNAP_DIR\" 2>/dev/null || true; "
        "cp -a mavaia_core/models/neural_text_generator/latest_run.txt \"$SNAP_DIR\" 2>/dev/null || true; "
        "cp -a mavaia_core/models/neural_text_generator/*.keras \"$SNAP_DIR\" 2>/dev/null || true; "
        "cp -a mavaia_core/models/neural_text_generator/*.json \"$SNAP_DIR\" 2>/dev/null || true; "
        "echo \"snapshot_saved\""
    ).format(ts=timestamp)

    if proxy:
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "PasswordAuthentication=no",
            "-i", ssh_key,
            "-p", "22",
            proxy,
            snapshot_cmd,
        ]
        subprocess.run(ssh_cmd, check=True)
        return

    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "PasswordAuthentication=no",
        "-i", ssh_key,
        "-p", str(pod_port),
        f"root@{pod_ip}",
        snapshot_cmd,
    ]
    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError:
        if pod_id:
            ssh_cmd[9] = "22"
            ssh_cmd[10] = f"{pod_id}-22@ssh.runpod.io"
            subprocess.run(ssh_cmd, check=True)
        else:
            raise

def main():
    parser = argparse.ArgumentParser(description="Mavaia RunPod Training Bridge")
    parser.add_argument("--pod-id", help="Existing pod ID to use")
    parser.add_argument("--gpu", default="NVIDIA RTX A6000", help="GPU type for new pod")
    parser.add_argument("--image", default="runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04", help="Container image")
    parser.add_argument("--template", default="runpod-torch-v240", help="RunPod Template ID")
    parser.add_argument("--ssh-key", default=str(Path.home() / ".ssh" / "mavaia_key"), help="Path to your local private SSH key")
    parser.add_argument("--ssh-key-value", help="Public SSH key content (or name) to inject into the pod")
    parser.add_argument("--ssh-proxy", help="Full SSH proxy host (e.g. 68aeykzanq67mn-64411855@ssh.runpod.io)")
    parser.add_argument("--auto", action="store_true", help="Auto-manage: terminate active pods, pick best GPU under $0.50/hr, and train")
    parser.add_argument("--max-price", type=float, default=1.00, help="Max hourly price for auto GPU selection")
    parser.add_argument("--min-price", type=float, default=0.50, help="Min hourly price for auto GPU selection")
    parser.add_argument("--auto-price-range", type=str, default="0.50-1.00", help="Auto price range min-max (overrides min/max if set)")
    parser.add_argument("--auto-price-step", type=float, default=0.05, help="Step size for auto price range scan")
    parser.add_argument("--terminate", action="store_true", help="Terminate pod after training")
    parser.add_argument("--dry-run", action="store_true", help="Just print commands")
    parser.add_argument("--watchdog-minutes", type=float, default=10.0, help="Watchdog interval (minutes) to snapshot/sync during training (0 disables)")
    parser.add_argument("--no-watchdog", action="store_true", help="Disable watchdog snapshots during training")
    parser.add_argument("--teacher-model", default="phi4:latest", help="Ollama teacher model to pull (default: phi4:latest)")
    parser.add_argument("--ollama-model-dir", default="/workspace/ollama", help="Ollama model storage dir (default: /workspace/ollama)")
    parser.add_argument("--no-ollama", action="store_true", help="Skip Ollama setup")
    parser.add_argument("--data-center", default="EU-RO-1", help="RunPod data center ID (default: EU-RO-1)")
    parser.add_argument("--s3-bucket", default="sxzm7zw9w9", help="RunPod S3 bucket name")
    parser.add_argument("--s3-region", default="eu-ro-1", help="RunPod S3 region")
    parser.add_argument("--s3-endpoint", default="https://s3api-eu-ro-1.runpod.io", help="RunPod S3 endpoint URL")
    parser.add_argument("--s3-prefix", default="mavaia", help="S3 prefix for repo/workspace sync")
    parser.add_argument("--s3-ollama-prefix", default="ollama", help="S3 prefix for Ollama model storage")
    parser.add_argument("--no-s3", action="store_true", help="Disable S3 sync for workspace/ollama")
    parser.add_argument("--volume-id", help="Attach an existing RunPod network volume by ID")
    parser.add_argument("--volume-mount-path", default="/workspace", help="Mount path for the attached volume")
    parser.add_argument("--auto-distill", action="store_true", help="Auto-inject distillation args for transformer training")
    parser.add_argument("--distill-alpha", type=float, default=0.7, help="Hard loss weight for distillation")
    parser.add_argument("--distill-temp", type=float, default=2.0, help="Distillation temperature")
    parser.add_argument("--distill-topk", type=int, default=20, help="Top-k logprobs for teacher distillation")
    
    # Forwarded args
    parser.add_argument("train_args", nargs=argparse.REMAINDER, help="Args for training script")

    args = parser.parse_args()

    if not RUNPOD_API_KEY:
        print("[!] Error: Mavaia_Key not found in .env")
        sys.exit(1)

    bridge = RunPodBridge(RUNPOD_API_KEY)
    
    if not args.ssh_key_value:
        pub_key_path = Path(args.ssh_key).with_suffix(".pub")
        if pub_key_path.exists():
            args.ssh_key_value = pub_key_path.read_text().strip()
            print(f"[*] Auto-loaded public SSH key from {pub_key_path}")

    if args.volume_id:
        args.no_s3 = True

    if not args.no_s3:
        if not shutil.which("aws"):
            print("[!] aws CLI not found on VPS. Install awscli or use --no-s3.")
            sys.exit(1)

    pod = None
    auto_candidate_gpus = None
    if args.auto:
        print("[*] Auto-manage enabled: Finding existing pods...")
        pods = bridge.get_pods()
        for p in pods:
            print(f"[*] Terminating existing pod {p['id']} ({p.get('name')})...")
            bridge.terminate_pod(p['id'])
        
        # Build price steps from range
        min_price = float(args.min_price)
        max_price = float(args.max_price)
        if args.auto_price_range:
            try:
                min_str, max_str = args.auto_price_range.split("-", 1)
                min_price = float(min_str.strip())
                max_price = float(max_str.strip())
            except Exception:
                pass
        if max_price < min_price:
            min_price, max_price = max_price, min_price
        step = float(args.auto_price_step) if args.auto_price_step else 0.05
        if step <= 0:
            step = 0.05
        price_steps = []
        p = min_price
        # Avoid floating drift
        while p <= max_price + 1e-9:
            price_steps.append(round(p, 2))
            p += step
        if not price_steps:
            price_steps = [max_price]

        gpu_types = bridge._query("query { gpuTypes { id displayName memoryInGb securePrice communityPrice } }").get("data", {}).get("gpuTypes", [])

        filtered_gpus = []
        for step in price_steps:
            print(f"[*] Finding best GPU under ${step}/hr (min {min_price}, max {max_price})...")
            filtered_gpus = [
                g for g in gpu_types 
                if g.get('communityPrice') is not None 
                and g['communityPrice'] >= min_price
                and g['communityPrice'] <= step
                and g.get('memoryInGb') is not None
                and g.get('memoryInGb') >= 45
            ]
            if filtered_gpus:
                break

        if not filtered_gpus:
            print(f"[!] No suitable GPUs found under ${price_steps[-1]}/hr.")
            sys.exit(1)

        # Sort by memory descending, then price ascending (highest memory, lowest price tiebreaker)
        filtered_gpus.sort(key=lambda x: (x['memoryInGb'], -x['communityPrice']), reverse=True)
        best_gpu = filtered_gpus[0]
        gpu_id = best_gpu['id']
        auto_candidate_gpus = filtered_gpus
        
        print(f"[*] Selected optimal GPU: {best_gpu['displayName']} ({best_gpu['memoryInGb']}GB VRAM @ ${best_gpu['communityPrice']}/hr)")
    elif args.pod_id:
        pods = bridge.get_pods()
        pod = next((p for p in pods if p['id'] == args.pod_id), None)
        if not pod:
            print(f"[!] Pod {args.pod_id} not found.")
            sys.exit(1)
    else:
        print(f"[*] No pod specified. Finding GPU ID for {args.gpu}...")
        gpu_types = bridge._query("query { gpuTypes { id } }").get("data", {}).get("gpuTypes", [])
        gpu_ids = [g['id'] for g in gpu_types]
        
        gpu_id = None
        if args.gpu in gpu_ids:
            gpu_id = args.gpu
        else:
            # Fallback mapping
            gpu_id = args.gpu.lower().replace(" ", "_").replace("nvidia_", "")
            if gpu_id not in gpu_ids:
                # Try one more: 'gpu_' prefix
                if f"gpu_{gpu_id}" in gpu_ids:
                    gpu_id = f"gpu_{gpu_id}"
                else:
                    print(f"[!] Warning: GPU '{args.gpu}' (mapped to '{gpu_id}') not found in available IDs: {gpu_ids[:5]}...")

    pod_env = {
        "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
        "AWS_SESSION_TOKEN": os.environ.get("AWS_SESSION_TOKEN"),
        "AWS_DEFAULT_REGION": args.s3_region,
    }

    if not args.no_s3:
        s3_sync_local_to_bucket(
            REPO_ROOT,
            args.s3_bucket,
            args.s3_prefix,
            args.s3_region,
            args.s3_endpoint,
        )

    if not pod and gpu_id:
        # Enforce minimum VRAM requirement for teacher + training
        try:
            gpu_info_list = bridge._query("query { gpuTypes { id displayName memoryInGb } }").get("data", {}).get("gpuTypes", [])
            gpu_info = next((g for g in gpu_info_list if g.get("id") == gpu_id), None)
            if gpu_info and gpu_info.get("memoryInGb") is not None and gpu_info.get("memoryInGb") < 45:
                print(f"[!] GPU {gpu_info.get('displayName', gpu_id)} has {gpu_info.get('memoryInGb')}GB VRAM; minimum is 45GB.")
                sys.exit(1)
        except Exception:
            pass

        candidate_gpus = auto_candidate_gpus if args.auto else [{"id": gpu_id, "displayName": gpu_id}]
        for candidate in candidate_gpus:
            candidate_id = candidate.get("id") if isinstance(candidate, dict) else candidate
            print(f"[*] Launching pod with GPU: {candidate_id}...")
            if args.dry_run:
                print(f"[DRY-RUN] Would launch {candidate_id} pod with template {args.template}")
                pod = {"id": "dry-run-id", "runtime": {"ports": [{"ip": "1.2.3.4", "publicPort": 1234, "isIpPublic": True}]}}
                break
            pod_result = bridge.create_pod(
                name="mavaia-trainer", 
                gpu_type_id=candidate_id, 
                template_id=args.template, 
                image=args.image,
                ssh_key_value=args.ssh_key_value,
                data_center_id=args.data_center,
                volume_id=args.volume_id,
                volume_mount_path=args.volume_mount_path,
                env=pod_env,
            )
            if not pod_result:
                print(f"[!] Failed to create pod with {candidate_id}, trying next candidate...")
                continue
            pod_id = pod_result['id']
            print(f"[*] Pod {pod_id} launched. Waiting for it to be ready...")
            
            # Polling for readiness
            while True:
                pods = bridge.get_pods()
                pod = next((p for p in pods if p['id'] == pod_id), None)
                if pod and pod.get("runtime") and pod["runtime"].get("uptimeInSeconds", 0) > 0:
                    break
                time.sleep(10)
            break

        if not pod:
            print("[!] Failed to create pod with any candidate GPU.")
            sys.exit(1)

    # Get SSH details
    # Look for privatePort 22, then fallback to first available public port
    public_ports = [p for p in pod.get("runtime", {}).get("ports", []) if p.get("isIpPublic")]
    ssh_port_info = next((p for p in public_ports if p.get("privatePort") == 22), None)
    
    if not ssh_port_info and public_ports:
        # Fallback to first available if 22 isn't explicitly found
        ssh_port_info = public_ports[0]
        print(
            f"[*] Warning: Port 22 not found; falling back to port {ssh_port_info.get('publicPort')} "
            f"(mapped from {ssh_port_info.get('privatePort', 'unknown')})"
        )
    
    if not ssh_port_info:
        # Some templates/accounts don't surface runtime public ports; fall back to RunPod's SSH proxy.
        if pod.get("id"):
            args.ssh_proxy = args.ssh_proxy or f"{pod['id']}-22@ssh.runpod.io"
            print(f"[*] No public port info; falling back to SSH proxy: {args.ssh_proxy}")
            pod_ip = "ssh.runpod.io"
            pod_port = 22
        else:
            print("[!] Could not find any public port information for pod.")
            sys.exit(1)
    else:
        pod_ip = ssh_port_info['ip']
        pod_port = ssh_port_info['publicPort']

    if args.dry_run:
        print(f"[DRY-RUN] Would sync to {pod_ip}:{pod_port} and start training.")
        return

    # Wait a bit for SSH service to be ready
    print("[*] Waiting 60s for SSH service to initialize...")
    time.sleep(60)

    interrupted = False
    failed = False
    watchdog_stop = None
    watchdog_thread = None
    try:
        setup_pod_env(pod_ip, pod_port, args.ssh_key, pod['id'], args.ssh_proxy)
        if args.no_s3:
            sync_code(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
        else:
            s3_sync_pod(
                pod_ip,
                pod_port,
                args.ssh_key,
                args.s3_bucket,
                args.s3_prefix,
                args.s3_region,
                args.s3_endpoint,
                "pull",
                pod['id'],
                args.ssh_proxy,
                src=f"{args.volume_mount_path}/mavaia",
            )
            s3_sync_pod(
                pod_ip,
                pod_port,
                args.ssh_key,
                args.s3_bucket,
                args.s3_ollama_prefix,
                args.s3_region,
                args.s3_endpoint,
                "pull",
                pod['id'],
                args.ssh_proxy,
                src=f"{args.volume_mount_path}/ollama",
            )
        ensure_mavaia_installed(pod_ip, pod_port, args.ssh_key, args.volume_mount_path, pod['id'], args.ssh_proxy)
        if not args.no_s3:
            s3_sync_pod(
                pod_ip,
                pod_port,
                args.ssh_key,
                args.s3_bucket,
                args.s3_prefix,
                args.s3_region,
                args.s3_endpoint,
                "push",
                pod['id'],
                args.ssh_proxy,
                src=f"{args.volume_mount_path}/mavaia",
            )
        if not args.no_ollama:
            setup_ollama(
                pod_ip,
                pod_port,
                args.ssh_key,
                args.teacher_model,
                args.ollama_model_dir,
                pod['id'],
                args.ssh_proxy,
            )
            if not args.no_s3:
                s3_sync_pod(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    args.s3_bucket,
                    args.s3_ollama_prefix,
                    args.s3_region,
                    args.s3_endpoint,
                    "push",
                    pod['id'],
                    args.ssh_proxy,
                    src=f"{args.volume_mount_path}/ollama",
                )

        if not args.no_watchdog:
            interval_minutes = float(args.watchdog_minutes or 0.0)
            if interval_minutes > 0:
                watchdog_stop = threading.Event()

                def _watchdog_loop():
                    interval_s = max(60.0, interval_minutes * 60.0)
                    while not watchdog_stop.wait(interval_s):
                        try:
                            print("[*] Watchdog: snapshot + sync")
                            remote_snapshot(pod_ip, pod_port, args.ssh_key, pod['id'], args.ssh_proxy)
                            get_artifacts(pod_ip, pod_port, args.ssh_key, REPO_ROOT, pod['id'], args.ssh_proxy)
                            sync_training_data(pod_ip, pod_port, args.ssh_key, REPO_ROOT, pod['id'], args.ssh_proxy)
                        except Exception as e:
                            print(f"[!] Watchdog failed: {e}")

                watchdog_thread = threading.Thread(target=_watchdog_loop, daemon=True)
                watchdog_thread.start()

        train_args = list(args.train_args)
        if args.auto_distill:
            if "--distill" not in train_args:
                train_args.extend(
                    [
                        "--distill",
                        "--teacher-model", args.teacher_model,
                        "--distill-alpha", str(args.distill_alpha),
                        "--distill-temp", str(args.distill_temp),
                        "--distill-topk", str(args.distill_topk),
                    ]
                )
            if "--model-type" not in train_args and "--model_type" not in train_args:
                train_args.extend(["--model-type", "transformer"])

        remote_train(pod_ip, pod_port, args.ssh_key, train_args, args.volume_mount_path, pod['id'], args.ssh_proxy)
        get_artifacts(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
        sync_training_data(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
        if not args.no_s3:
            s3_sync_pod(
                pod_ip,
                pod_port,
                args.ssh_key,
                args.s3_bucket,
                args.s3_prefix,
                args.s3_region,
                args.s3_endpoint,
                "push",
                pod['id'],
                args.ssh_proxy,
                src=f"{args.volume_mount_path}/mavaia",
            )
            s3_sync_pod(
                pod_ip,
                pod_port,
                args.ssh_key,
                args.s3_bucket,
                args.s3_ollama_prefix,
                args.s3_region,
                args.s3_endpoint,
                "push",
                pod['id'],
                args.ssh_proxy,
                src=f"{args.volume_mount_path}/ollama",
            )

        print("[*] Remote training successful! Artifacts retrieved.")
    except KeyboardInterrupt:
        interrupted = True
        print("[*] CTRL+C detected: saving snapshot and syncing artifacts before exit...")
        try:
            remote_snapshot(pod_ip, pod_port, args.ssh_key, args.volume_mount_path, pod['id'], args.ssh_proxy)
        except Exception as e:
            print(f"[!] Snapshot failed: {e}")
        try:
            get_artifacts(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
            sync_training_data(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
            if not args.no_s3:
                s3_sync_pod(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    args.s3_bucket,
                    args.s3_prefix,
                    args.s3_region,
                    args.s3_endpoint,
                    "push",
                    pod['id'],
                    args.ssh_proxy,
                    src="/workspace/mavaia",
                )
                s3_sync_pod(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    args.s3_bucket,
                    args.s3_ollama_prefix,
                    args.s3_region,
                    args.s3_endpoint,
                    "push",
                    pod['id'],
                    args.ssh_proxy,
                    src="/workspace/ollama",
                )
        except Exception as e:
            print(f"[!] Artifact sync failed: {e}")
    except Exception as e:
        failed = True
        print(f"[!] Error detected: {e}. Saving snapshot and syncing artifacts before exit...")
        try:
            remote_snapshot(pod_ip, pod_port, args.ssh_key, args.volume_mount_path, pod['id'], args.ssh_proxy)
        except Exception as snap_e:
            print(f"[!] Snapshot failed: {snap_e}")
        try:
            get_artifacts(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
            sync_training_data(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
            if not args.no_s3:
                s3_sync_pod(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    args.s3_bucket,
                    args.s3_prefix,
                    args.s3_region,
                    args.s3_endpoint,
                    "push",
                    pod['id'],
                    args.ssh_proxy,
                    src="/workspace/mavaia",
                )
                s3_sync_pod(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    args.s3_bucket,
                    args.s3_ollama_prefix,
                    args.s3_region,
                    args.s3_endpoint,
                    "push",
                    pod['id'],
                    args.ssh_proxy,
                    src="/workspace/ollama",
                )
        except Exception as sync_e:
            print(f"[!] Artifact sync failed: {sync_e}")
    finally:
        if watchdog_stop is not None:
            watchdog_stop.set()
        if args.terminate:
            print(f"[*] Terminating pod {pod['id']}...")
            bridge.terminate_pod(pod['id'])
        else:
            print(f"[*] Stopping pod {pod['id']} (saving costs)...")
            bridge.stop_pod(pod['id'])

    if interrupted:
        return 130
    if failed:
        return 1

if __name__ == "__main__":
    sys.exit(main() or 0)
