import os
import sys
import json
import time
import subprocess
import argparse
import requests
import threading
import shutil
import re
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


def _redact_secrets(text: str) -> str:
    if not text:
        return text
    # Avoid leaking AWS creds if a failed subprocess/ssh command is included in exceptions.
    patterns = [
        (r"(AWS_ACCESS_KEY_ID=)'[^']*'", r"\1'***'"),
        (r'(AWS_ACCESS_KEY_ID=)"[^"]*"', r'\1"***"'),
        (r"(AWS_SECRET_ACCESS_KEY=)'[^']*'", r"\1'***'"),
        (r'(AWS_SECRET_ACCESS_KEY=)"[^"]*"', r'\1"***"'),
        (r"(AWS_SESSION_TOKEN=)'[^']*'", r"\1'***'"),
        (r'(AWS_SESSION_TOKEN=)"[^"]*"', r'\1"***"'),
        (r"(HF_TOKEN=)'[^']*'", r"\1'***'"),
        (r'(HF_TOKEN=)"[^"]*"', r'\1"***"'),
    ]
    for pat, repl in patterns:
        text = re.sub(pat, repl, text)
    return text

class RunPodBridge:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else ""
        }

    def _query(
        self,
        query: str,
        variables: Optional[Dict] = None,
        log_errors: bool = True,
        allow_http_error: bool = False,
    ) -> Dict:
        response = requests.post(
            RUNPOD_ENDPOINT,
            json={"query": query, "variables": variables},
            headers=self.headers,
        )
        try:
            data = response.json()
        except Exception:
            response.raise_for_status()
            return {}
        if "errors" in data and log_errors:
            for err in data["errors"]:
                msg = str(err.get("message", "Unknown error"))
                code = None
                ext = err.get("extensions")
                if isinstance(ext, dict):
                    code = ext.get("code")
                if code:
                    print(f"[ERROR] RunPod: {code} - {msg}")
                else:
                    print(f"[ERROR] RunPod: {msg}")
        if response.status_code >= 400 and not allow_http_error:
            response.raise_for_status()
        return data

    def get_gpu_types_with_availability(self) -> List[Dict]:
        field_sets = [
            "id displayName memoryInGb securePrice communityPrice stockStatus",
            "id displayName memoryInGb securePrice communityPrice availability",
            "id displayName memoryInGb securePrice communityPrice",
        ]
        for fields in field_sets:
            query = f"query {{ gpuTypes {{ {fields} }} }}"
            data = self._query(query, log_errors=False, allow_http_error=True)
            if "errors" in data:
                continue
            return data.get("data", {}).get("gpuTypes", [])
        return []

    @staticmethod
    def gpu_is_available(gpu: Dict) -> bool:
        if "stockStatus" in gpu and gpu.get("stockStatus") is not None:
            status = str(gpu.get("stockStatus")).lower()
            return status in ("available", "in_stock", "ok", "true", "ready")
        if "availability" in gpu and gpu.get("availability") is not None:
            avail = gpu.get("availability")
            if isinstance(avail, bool):
                return avail
            if isinstance(avail, (int, float)):
                return avail > 0
            status = str(avail).lower()
            return status in ("available", "in_stock", "ok", "true", "ready")
        # Unknown; assume available to avoid false negatives.
        return True

    def get_pods(self) -> List[Dict]:
        query = """
        query MyPods {
          myself {
            pods {
              id
              name
              desiredStatus
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

    def get_balance(self) -> Optional[float]:
        queries = [
            "query { myself { balance } }",
            "query { myself { creditBalance } }",
            "query { myself { credits } }",
        ]
        for q in queries:
            data = self._query(q, log_errors=False, allow_http_error=True)
            myself = data.get("data", {}).get("myself", {}) if isinstance(data, dict) else {}
            for key in ("balance", "creditBalance", "credits"):
                val = myself.get(key)
                if val is not None:
                    try:
                        return float(val)
                    except Exception:
                        return None
        return None

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
        input_data = {
            "name": name,
            "gpuTypeId": gpu_type_id,
            "gpuCount": 1,
            "volumeInGb": 200,
            "containerDiskInGb": 200,
            "volumeMountPath": volume_mount_path,
        }
        
        env_vars = []
        if env:
            for k, v in env.items():
                if v:
                    env_vars.append({"key": k, "value": str(v)})
        if ssh_key_value:
            env_vars.append({"key": "PUBLIC_KEY", "value": ssh_key_value})
            env_vars.append({"key": "SSH_PUBLIC_KEY", "value": ssh_key_value})

        if env_vars:
            input_data["env"] = env_vars

        if data_center_id:
            input_data["dataCenterId"] = data_center_id
        if volume_id:
            input_data["networkVolumeId"] = volume_id
        
        if template_id:
            input_data["templateId"] = template_id
            input_data["ports"] = "22/tcp"
        elif image:
            input_data["imageName"] = image
            input_data["ports"] = "22/tcp"
            input_data["dockerArgs"] = ""
        
        query = """
        mutation CreatePod($input: PodFindAndDeployOnDemandInput!) {
          podFindAndDeployOnDemand(input: $input) {
            id
            imageName
            name
          }
        }
        """
        result = self._query(query, variables={"input": input_data})
        return result.get("data", {}).get("podFindAndDeployOnDemand")

    def stop_pod(self, pod_id: str):
        query = """
        mutation StopPod($input: PodStopInput!) {
          podStop(input: $input) {
            id
          }
        }
        """
        return self._query(query, variables={"input": {"podId": pod_id}})

    def terminate_pod(self, pod_id: str):
        query = """
        mutation TerminatePod($input: PodTerminateInput!) {
          podTerminate(input: $input)
        }
        """
        return self._query(query, variables={"input": {"podId": pod_id}})

def setup_pod_env(pod_ip: str, pod_port: int, ssh_key: str, pod_id: str = None, proxy: str = None):
    print(f"[*] Checking environment on pod {pod_ip}:{pod_port}...")
    
    # Try direct first, then proxy
    connection_methods = []
    if proxy:
        connection_methods.append({"host": proxy, "port": "22"})
    else:
        connection_methods.append({"host": f"root@{pod_ip}", "port": str(pod_port)})
        if pod_id:
            connection_methods.append({"host": f"{pod_id}-22@ssh.runpod.io", "port": "22"})
        
    # Skip install if rsync and aws are already present
    check_cmd = "command -v rsync >/dev/null 2>&1 && command -v aws >/dev/null 2>&1"
    install_cmd = (
        "apt-get update -qq && apt-get install -y rsync python3-venv curl zstd pciutils mbuffer -qq && "
        "python3 -m pip install --upgrade pip -q && "
        "if ! command -v aws >/dev/null 2>&1; then pip install --upgrade awscli -q; fi"
    )
    
    full_cmd = f"if ! ({check_cmd}); then {install_cmd}; else echo '[INFO] Tools already present, skipping setup.'; fi"

    max_retries = 30
    for i in range(max_retries):
        method = connection_methods[0] if i % 2 == 0 or len(connection_methods) == 1 else connection_methods[1]
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "PasswordAuthentication=no",
            "-o", "ConnectTimeout=10",
            "-i", ssh_key,
            "-p", method["port"],
            method["host"],
            full_cmd
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
    s3_bucket: str = None,
    s3_prefix: str = None,
    s3_region: str = None,
    s3_endpoint: str = None,
    force_reinstall: bool = False,
    pip_debug: bool = False,
    pip_stream: bool = False,
    editable_install: bool = False,
):
    print("[*] Ensuring environment is ready (Minimalist Mode)...")

    # Build S3 vars for injection into remote script
    s3_key = f"s3://{s3_bucket}/{s3_prefix}/mavaia.tar" if s3_bucket else ""
    region_flag = f"--region {s3_region}" if s3_region else ""
    endpoint_flag = f"--endpoint-url {s3_endpoint}" if s3_endpoint else ""
    aws_flags = f"{region_flag} {endpoint_flag}".strip()
    
    cred_export = ""
    aws_key_id = os.environ.get("AWS_ACCESS_KEY_ID", "")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    hf_token = os.environ.get("HF_TOKEN")
    if aws_key_id and aws_secret:
        cred_export = f"export AWS_ACCESS_KEY_ID='{aws_key_id}'; export AWS_SECRET_ACCESS_KEY='{aws_secret}'; "
    if hf_token:
        cred_export += f"export HF_TOKEN='{hf_token}'; "

    # S3 restore logic: pull if forced or directory missing
    s3_restore = ""
    if s3_key:
        s3_restore = (
            f"if [ ! -d {workdir}/mavaia ] || [ \"{force_reinstall}\" = \"True\" ] || [ \"{force_reinstall}\" = \"1\" ]; then "
            f"  echo '[*] Syncing latest code from S3...'; "
            f"  mkdir -p {workdir}/mavaia; "
            f"  {cred_export} aws s3 cp {s3_key} - {aws_flags} | tar -xf - --no-same-owner -C {workdir}/mavaia; "
            f"fi; "
        )

    install_cmd = (
        "set -e; "
        f"{cred_export}"
        f"{s3_restore}"
        f"cd {workdir}/mavaia; "
        
        # LOGIN: Ensure HF_TOKEN is active for the CLI and library
        "if [ ! -z \"$HF_TOKEN\" ]; then "
        "  echo '[INFO] Logging into Hugging Face Hub...'; "
        "  huggingface-cli login --token \"$HF_TOKEN\" --add-to-git-credential >/dev/null 2>&1 || true; "
        "fi; "

        # 1. Determine Python path (Use system if Golden Image, else Venv)
        "if python3 -c 'import torch' >/dev/null 2>&1; then "
        "  echo '[INFO] Golden Image detected (torch found). Using system Python.'; "
        "  if [ -d .venv ]; then echo '[INFO] Removing old isolated .venv...'; rm -rf .venv; fi; "
        "  VENV_PY=\"python3\"; "
        "  echo '[INFO] Purging old mavaia-core installations to ensure fresh code usage...'; "
        "  \"$VENV_PY\" -m pip uninstall -y mavaia-core 2>/dev/null || true; "
        "  if [ \"$force_reinstall\" = \"True\" ] || [ \"$force_reinstall\" = \"1\" ]; then "
        "    echo '[INFO] Force refresh: cleaning up potentially broken extras...'; "
        "    \"$VENV_PY\" -m pip uninstall -y datasets transformers accelerate huggingface_hub pyarrow 2>/dev/null || true; "
        "  fi; "
        "else "
        "  if [ ! -f .venv/bin/activate ]; then "
        "    echo '[INFO] No torch in system. Creating venv...'; "
        "    python3 -m venv --system-site-packages .venv; "
        "  fi; "
        "  VENV_PY=\"$(pwd)/.venv/bin/python\"; "
        "fi; "

        # 2. CLEANUP & SYSTEM INSTALL: Clear the project-root mess and install to system
        "echo '[INFO] Cleaning up project root and ensuring system-level extras...'; "
        "rm -rf datasets transformers accelerate huggingface_hub pyarrow wikipedia regex pandas peft trl 2>/dev/null || true; "
        "\"$VENV_PY\" -m pip install datasets transformers accelerate huggingface_hub pyarrow wikipedia regex pandas peft trl --break-system-packages -q || true; "


        # 3. Final verification
        "if ! \"$VENV_PY\" -c 'import datasets; import transformers' >/dev/null 2>&1; then "
        "  echo '[ERROR] Core libraries still failing. Traceback:'; "
        "  \"$VENV_PY\" -c 'import transformers' 2>&1; "
        "  \"$VENV_PY\" -c 'import datasets' 2>&1; "
        "  exit 1; "
        "fi; "
        
        "echo '[INFO] Running HF Dataset Quality Check...'; "
        "\"$VENV_PY\" scripts/test_hf_load.py || exit 1; "
        
        "echo '[SUCCESS] Environment ready. System Python: '$VENV_PY; "
    )

    _run_ssh(ssh_key, pod_ip, pod_port, pod_id, proxy, install_cmd)


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
            print("[WARN] Direct SSH failed (255); retrying via proxy.")
            # Swap to RunPod SSH proxy (update port + host entries)
            ssh_cmd[8] = "22"
            ssh_cmd[9] = f"{pod_id}-22@ssh.runpod.io"
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


def _aws_cli_flags(region: str, endpoint_url: str) -> list:
    """Return aws CLI flag list for region + endpoint."""
    flags = []
    if region:
        flags += ["--region", region]
    if endpoint_url:
        flags += ["--endpoint-url", endpoint_url]
    return flags


def _aws_configure_fast(region: str, endpoint_url: str):
    """Tune AWS CLI for high-throughput multipart uploads."""
    for key, val in [
        ("default.s3.max_concurrent_requests", "100"),
        ("default.s3.multipart_chunksize", "50MB"),
        ("default.s3.multipart_threshold", "50MB"),
    ]:
        subprocess.run(["aws", "configure", "set", key, val], check=False)


def _s3_abort_zombies(bucket: str, prefix: str, region: str, endpoint_url: str):
    """Abort any stalled multipart uploads that may block new uploads."""
    flags = _aws_cli_flags(region, endpoint_url)
    try:
        result = subprocess.run(
            ["aws", "s3api", "list-multipart-uploads", "--bucket", bucket] + flags,
            capture_output=True, text=True, check=False,
        )
        import json as _json
        data = _json.loads(result.stdout or "{}")
        for upload in data.get("Uploads", []):
            key = upload["Key"]
            uid = upload["UploadId"]
            if key.startswith(prefix):
                subprocess.run(
                    ["aws", "s3api", "abort-multipart-upload",
                     "--bucket", bucket, "--key", key, "--upload-id", uid] + flags,
                    check=False,
                )
                print(f"[*] Aborted zombie multipart upload: {key} ({uid[:8]}...)")
    except Exception as e:
        print(f"[*] Zombie cleanup skipped: {_redact_secrets(str(e))}")


def s3_sync_local_to_bucket(
    local_path: Path,
    bucket: str,
    prefix: str,
    region: str,
    endpoint_url: str,
):
    """Stream-archive local repo → S3 as a single tar (fast, no per-file overhead)."""
    print("[*] Packing and streaming local repo → S3 (tar pipe)...")
    _aws_configure_fast(region, endpoint_url)
    _s3_abort_zombies(bucket, prefix, region, endpoint_url)
    s3_key = f"s3://{bucket}/{prefix}/mavaia.tar"
    tar_cmd = [
        "tar", "-cf", "-",
        "--exclude=.git",
        "--exclude=__pycache__",
        "--exclude=.venv",
        "--exclude=*.pyc",
        "--exclude=*.tmp",
        "--exclude=.cursor",
        "--exclude=./models",
        "--exclude=./models/*",
        "--exclude=build",
        "--exclude=LiveBench",
        "--exclude=*.egg-info",
        "--exclude=runs",
        "--exclude=checkpoints",
        "--exclude=snapshots",
        "-C", str(local_path), ".",
    ]
    # Use mbuffer if available for a smooth 128M in-memory buffer; otherwise pass directly
    use_mbuffer = shutil.which("mbuffer") is not None
    aws_cmd = ["aws", "s3", "cp", "-", s3_key] + _aws_cli_flags(region, endpoint_url)
    print(f"[*] Uploading to {s3_key} {'(mbuffer)' if use_mbuffer else '(direct pipe)'}...")
    tar_proc = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE)
    if use_mbuffer:
        buf_proc = subprocess.Popen(
            ["mbuffer", "-m", "128M", "-q"],
            stdin=tar_proc.stdout, stdout=subprocess.PIPE,
        )
        tar_proc.stdout.close()
        aws_proc = subprocess.Popen(aws_cmd, stdin=buf_proc.stdout)
        buf_proc.stdout.close()
        aws_proc.communicate()
        buf_proc.wait()
    else:
        aws_proc = subprocess.Popen(aws_cmd, stdin=tar_proc.stdout)
        tar_proc.stdout.close()
        aws_proc.communicate()
    tar_proc.wait()
    if tar_proc.returncode not in (0, None) or aws_proc.returncode != 0:
        raise RuntimeError(f"S3 tar upload failed (tar={tar_proc.returncode}, aws={aws_proc.returncode})")
    print("[*] Repo archive uploaded to S3.")


def _ssh_base(ssh_key: str, port: str, host: str) -> list:
    # Short, reliable SSH defaults for flaky public endpoints.
    return [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "PasswordAuthentication=no",
        "-o", "ConnectTimeout=15",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=3",
        "-i", ssh_key,
        "-p", port,
        host,
    ]


def _run_ssh(
    ssh_key: str,
    pod_ip: str,
    pod_port: int,
    pod_id: str,
    proxy: str,
    cmd: str,
    check: bool = True,
    retries: int = 2,
    retry_delay_s: float = 3.0,
):
    """Run a remote shell command, with retries and proxy fallback on exit 255."""
    def _try(cmd_list: list) -> None:
        attempt = 0
        while True:
            try:
                subprocess.run(cmd_list, check=check)
                return
            except subprocess.CalledProcessError as e:
                attempt += 1
                if attempt > retries:
                    raise e
                time.sleep(retry_delay_s)

    if proxy:
        _try(_ssh_base(ssh_key, "22", proxy) + [cmd])
        return

    try:
        _try(_ssh_base(ssh_key, str(pod_port), f"root@{pod_ip}") + [cmd])
    except subprocess.CalledProcessError as e:
        if pod_id and e.returncode == 255:
            _try(_ssh_base(ssh_key, "22", f"{pod_id}-22@ssh.runpod.io") + [cmd])
        else:
            raise


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
    """Push/pull a directory between a pod and S3 using a streamed tar pipe."""
    if direction not in ("pull", "push"):
        raise ValueError("direction must be 'pull' or 'push'")

    region_flag = f"--region {region}" if region else ""
    endpoint_flag = f"--endpoint-url {endpoint_url}" if endpoint_url else ""
    aws_flags = f"{region_flag} {endpoint_flag}".strip()
    aws_cfg = (
        "aws configure set default.s3.max_concurrent_requests 50; "
        "aws configure set default.s3.multipart_chunksize 64MB; "
        "aws configure set default.s3.multipart_threshold 64MB; "
    )
    # Always inject credentials from env (SSH sessions don't forward env vars)
    aws_key_id = os.environ.get("AWS_ACCESS_KEY_ID", "")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    cred_export = ""
    if aws_key_id and aws_secret:
        cred_export = (
            f"export AWS_ACCESS_KEY_ID='{aws_key_id}'; "
            f"export AWS_SECRET_ACCESS_KEY='{aws_secret}'; "
        )
    # Abort any zombie multipart uploads for this key before starting
    abort_zombies = (
        f"aws s3api list-multipart-uploads --bucket {bucket} {region_flag} {endpoint_flag} 2>/dev/null | "
        f"python3 -c \"import sys,json; [print(u['Key'],u['UploadId']) for u in json.load(sys.stdin).get('Uploads',[]) if u['Key'].startswith('{prefix}')]\" | "
        f"while read key uid; do aws s3api abort-multipart-upload --bucket {bucket} --key $key --upload-id $uid {region_flag} {endpoint_flag} 2>/dev/null; done; "
    )
    # Use mbuffer on pod if available for steady streaming
    tar_pipe_push = (
        f"tar -cf - --exclude=.git --exclude=__pycache__ --exclude=.venv "
        f"--exclude='*.pyc' --exclude='*.tmp' -C {{src}} . "
    )
    s3_key = f"s3://{bucket}/{prefix}/mavaia.tar"

    if direction == "push":
        cmd = (
            f"{cred_export}{aws_cfg}{abort_zombies}"
            f"if command -v mbuffer > /dev/null 2>&1; then "
            f"  {tar_pipe_push.format(src=src)} | mbuffer -m 128M -q | aws s3 cp - {s3_key} {aws_flags}; "
            f"else "
            f"  {tar_pipe_push.format(src=src)} | aws s3 cp - {s3_key} {aws_flags}; "
            f"fi"
        )
        print(f"[*] Streaming pod dir {src} -> {s3_key}...")
    else:  # pull
        cmd = (
            f"{cred_export}{aws_cfg}"
            f"mkdir -p {src} && "
            f"aws s3 cp {s3_key} - {aws_flags} | tar -xf - --no-same-owner -C {src}"
        )
        print(f"[*] Streaming {s3_key} -> pod dir {src}...")

    _run_ssh(ssh_key, pod_ip, pod_port, pod_id, proxy, cmd)

def sync_code(pod_ip: str, pod_port: int, ssh_key: str, local_path: Path, workdir: str, pod_id: str = None, proxy: str = None):
    print(f"[*] Syncing code to pod...")
    
    if proxy:
        rsync_cmd = [
            "rsync", "-az", "--info=stats2,progress2", "--human-readable",
            "--no-owner", "--no-group", "--no-perms",
            "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22",
            "--exclude", ".git", "--exclude", "__pycache__", "--exclude", ".venv",
            "--exclude", "models", "--exclude", "mavaia_core/models",
            "--exclude", "mavaia_core/data", "--exclude", "data",
            "--exclude", "LiveBench", "--exclude", "build", "--exclude", "tmp",
            str(local_path) + "/",
            f"{proxy}:{workdir}/mavaia"
        ]
        subprocess.run(rsync_cmd, check=True)
        return
        
    rsync_cmd = [
        "rsync", "-az", "--info=stats2,progress2", "--human-readable",
        "--no-owner", "--no-group", "--no-perms",
        "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p {pod_port}",
        "--exclude", ".git", "--exclude", "__pycache__", "--exclude", ".venv",
        "--exclude", ".cursor", "--exclude", ".vscode", "--exclude", "tmp",
        "--exclude", "models", "--exclude", "mavaia_core/models",
        "--exclude", "mavaia_core/data", "--exclude", "data",
        "--exclude", "LiveBench", "--exclude", "build",
        str(local_path) + "/",
        f"root@{pod_ip}:{workdir}/mavaia"
    ]
    try:
        proc = subprocess.run(rsync_cmd, check=False)
        if proc.returncode != 0 and proc.returncode != 23:
            # 23 means partial transfer (often harmless for locked local files)
            raise subprocess.CalledProcessError(proc.returncode, rsync_cmd)
        elif proc.returncode == 23:
            print("[INFO] Rsync completed with status 23 (partial transfer). Safe to proceed.")

    except subprocess.CalledProcessError:
        if pod_id:
            print("[WARN] Direct rsync failed; retrying via proxy.")
            rsync_cmd[4] = f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22"
            rsync_cmd[-1] = f"{pod_id}-22@ssh.runpod.io:{workdir}/mavaia"
            proc = subprocess.run(rsync_cmd, check=False)
            if proc.returncode != 0 and proc.returncode != 23:
                raise subprocess.CalledProcessError(proc.returncode, rsync_cmd)
            elif proc.returncode == 23:
                print("[INFO] Rsync completed with status 23 (partial transfer) via proxy. Safe to proceed.")

def remote_train(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    train_args: List[str],
    workdir: str,
    pod_id: str = None,
    proxy: str = None,
    script_rel: str = "scripts/train_neural_text_generator.py",
):
    print(f"[*] Starting training on remote pod...")
    if train_args and train_args[0] == "--":
        train_args = train_args[1:]
    args_str = " ".join(train_args)
    env_prefix = "PYTHONUNBUFFERED=1 "
    if "--plain-output" in train_args:
        env_prefix += "MAVAIA_PLAIN_OUTPUT=1 "
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        env_prefix += f"HF_TOKEN='{hf_token}' "
    
    if proxy:
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "PasswordAuthentication=no",
            "-i", ssh_key,
            "-p", "22",
            proxy,
            f"cd {workdir}/mavaia && PYTHON_EXE=$(if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi); {env_prefix}$PYTHON_EXE {script_rel} {args_str}"
        ]
        subprocess.run(ssh_cmd, check=True)
        return

    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "PasswordAuthentication=no",
        "-i", ssh_key,
        "-p", str(pod_port),
        f"root@{pod_ip}",
        f"cd {workdir}/mavaia && PYTHON_EXE=$(if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi); {env_prefix}$PYTHON_EXE {script_rel} {args_str}"
    ]
    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError as e:
        if pod_id and e.returncode == 255:
            print("[WARN] Direct SSH failed (255); retrying via proxy.")
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
            "rsync", "-az", "--info=stats2",
            "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22",
            f"{proxy}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
            str(dest_dir) + "/",
        ]
        subprocess.run(scp_cmd, check=True)
        return

    scp_cmd = [
        "rsync", "-az", "--info=stats2",
        "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p {pod_port}",
        f"root@{pod_ip}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
        str(dest_dir) + "/",
    ]
    try:
            proc = subprocess.run(scp_cmd, check=False)
            if proc.returncode != 0 and proc.returncode != 23:
                raise subprocess.CalledProcessError(proc.returncode, scp_cmd)
            elif proc.returncode == 23:
                print("[INFO] Rsync completed with status 23 (partial transfer). Safe to proceed.")
    except subprocess.CalledProcessError:
        if pod_id:
            print("[WARN] Direct rsync failed; retrying via proxy.")
            scp_cmd[3] = f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22"
            scp_cmd[4] = f"{pod_id}-22@ssh.runpod.io:{workdir}/mavaia/mavaia_core/models/neural_text_generator/"
            proc = subprocess.run(scp_cmd, check=False)
            if proc.returncode != 0 and proc.returncode != 23:
                raise subprocess.CalledProcessError(proc.returncode, scp_cmd)
            elif proc.returncode == 23:
                print("[INFO] Rsync completed with status 23 (partial transfer) via proxy. Safe to proceed.")

def sync_training_data(pod_ip: str, pod_port: int, ssh_key: str, local_path: Path, workdir: str, pod_id: str = None, proxy: str = None):
    print("[*] Syncing training data (runs, checkpoints, cache) from pod...")

    dest_dir = local_path / "models" / "neural_text_generator_remote" / "training_data"
    dest_dir.mkdir(parents=True, exist_ok=True)

    if proxy:
        rsync_cmd = [
            "rsync", "-az", "--info=stats2",
            "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22",
            f"{proxy}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
            str(dest_dir / "models") + "/",
        ]
        cache_cmd = [
            "rsync", "-az", "--info=stats2",
            "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22",
            f"{proxy}:{workdir}/mavaia/mavaia_core/data/",
            str(dest_dir / "data_cache") + "/",
        ]
        for cmd in (rsync_cmd, cache_cmd):
            proc = subprocess.run(cmd, check=False)
            if proc.returncode not in (0, 23):
                raise subprocess.CalledProcessError(proc.returncode, cmd)
            if proc.returncode == 23:
                print("[INFO] Rsync completed with status 23 (partial transfer). Safe to proceed.")
        return

    rsync_cmd = [
        "rsync", "-az", "--info=stats2",
        "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p {pod_port}",
        f"root@{pod_ip}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
        str(dest_dir / "models") + "/",
    ]
    cache_cmd = [
        "rsync", "-az", "--info=stats2",
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
                print("[INFO] Rsync completed with status 23 (partial transfer). Safe to proceed.")
    except subprocess.CalledProcessError:
        if pod_id:
            print("[WARN] Direct rsync failed; retrying via proxy.")
            rsync_cmd[3] = f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22"
            rsync_cmd[4] = f"{pod_id}-22@ssh.runpod.io:{workdir}/mavaia/mavaia_core/models/neural_text_generator/"
            cache_cmd[3] = f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22"
            cache_cmd[4] = f"{pod_id}-22@ssh.runpod.io:{workdir}/mavaia/mavaia_core/data/"
            for cmd in (rsync_cmd, cache_cmd):
                proc = subprocess.run(cmd, check=False)
                if proc.returncode not in (0, 23):
                    raise subprocess.CalledProcessError(proc.returncode, cmd)
                if proc.returncode == 23:
                    print("[INFO] Rsync completed with status 23 (partial transfer) via proxy. Safe to proceed.")


def _select_candidate_gpus(bridge: RunPodBridge, min_price: float, max_price: float, min_vram: int) -> List[Dict]:
    gpu_types = bridge.get_gpu_types_with_availability()
    if not gpu_types:
        return []
    # Estimate storage cost (~$0.01 per 10GB per hour as a rough safe buffer)
    storage_overhead = 0.20  # 200GB vol + 200GB disk
    
    # BLACKWELL EXCLUSION: These cards require sm_120 kernels not present in our stable image
    incompatible_keywords = ["Blackwell", "PRO 4500", "PRO 5000"]
    
    filtered_gpus = [
        g for g in gpu_types
        if bridge.gpu_is_available(g)
        if g.get('securePrice') is not None
        and (g['securePrice'] + storage_overhead) >= min_price
        and (g['securePrice'] + storage_overhead) <= max_price
        and g.get('memoryInGb') is not None
        and g.get('memoryInGb') >= min_vram
        and not any(kw in g.get('displayName', '') for kw in incompatible_keywords)
    ]
    filtered_gpus.sort(key=lambda x: (x['securePrice'], -x['memoryInGb']))
    return filtered_gpus


def _fleet_role_specs(args) -> List[Dict[str, Any]]:
    base_mount = "/workspace"
    
    # Modern curriculum-aligned fleet specs
    return [
        {
            "name": "mavaia_distill",
            "role": "distill",
            "workdir": f"{base_mount}/distill",
            "script": "scripts/train_neural_text_generator.py",
            "train_args": [
                "--epochs", "10",
                "--model-type", "transformer",
                "--distill",
                "--teacher-model", args.teacher_model,
                "--distill-alpha", str(args.distill_alpha),
                "--distill-temp", str(args.distill_temp),
                "--distill-topk", str(args.distill_topk),
                "--stop-at-loss", str(args.stop_at_loss or 0.05),
                "--min-improvement", str(args.min_improvement or 0.01),
            ],
        },
        {
            "name": "mavaia_logic",
            "role": "logic",
            "workdir": f"{base_mount}/logic",
            "script": "scripts/train_neural_text_generator.py",
            "train_args": [
                "--source", "huggingface",
                "--book-ids", "microsoft/orca-math-word-problems-200k",
                "--epochs", "1",
                "--data-percentage", "0.1",
                "--model-type", "transformer",
                "--stop-at-loss", str(args.stop_at_loss or 0.05),
                "--min-improvement", str(args.min_improvement or 0.01),
            ],
        },
        {
            "name": "mavaia_tone",
            "role": "tone",
            "workdir": f"{base_mount}/tone",
            "script": "scripts/train_neural_text_generator.py",
            "train_args": [
                "--source", "huggingface",
                "--book-ids", "mlfoundations-dev/oh-dcft-v3.1-gemini-1.5-pro",
                "--epochs", "1",
                "--data-percentage", "0.2",
                "--model-type", "transformer",
                "--stop-at-loss", str(args.stop_at_loss or 0.05),
                "--min-improvement", str(args.min_improvement or 0.01),
            ],
        },
    ]


def _fleet_auditor_cmd(workdir: str) -> str:
    return (
        f"cd {workdir}/mavaia && "
        "while true; do "
        "  echo '[INFO] Fleet auditor heartbeat'; "
        "  date -u; "
        "  df -h /workspace | sed -n '1,2p'; "
        "  ls -la /workspace | head -n 50; "
        "  sleep 60; "
        "done"
    )


_FLEET_LOCK = threading.Lock()
_FLEET_IN_FLIGHT = set()
_BALANCE_LOW = threading.Event()


def _fleet_worker(bridge: RunPodBridge, args, role: Dict[str, Any], stop_event: threading.Event):
    pod_id = None
    retry_sleep = 30
    min_price = float(args.min_price)
    max_price = float(args.max_price)
    # Stagger workers slightly to reduce contention.
    time.sleep({"distill": 0, "normal": 5, "auditor": 10}.get(role["role"], 0))
    while not stop_event.is_set():
        if _BALANCE_LOW.is_set():
            print(f"[WARN] Balance below ${args.min_balance:.2f}. Fleet paused.")
            time.sleep(min(60, retry_sleep))
            retry_sleep = min(retry_sleep * 2, 300)
            continue
        # Check existing pod
        if pod_id:
            pods = bridge.get_pods()
            pod = next((p for p in pods if p['id'] == pod_id), None)
            if not pod or not pod.get("runtime"):
                print(f"[WARN] Pod {pod_id} for role {role['role']} missing; restarting.")
                pod_id = None
            else:
                time.sleep(30)
                continue

        candidates = _select_candidate_gpus(bridge, min_price, max_price, args.min_vram)
        if not candidates:
            print(f"[INFO] No available GPUs for role {role['role']}. Retrying in {retry_sleep}s...")
            time.sleep(retry_sleep)
            retry_sleep = min(retry_sleep * 2, 300)
            continue

        candidate = None
        with _FLEET_LOCK:
            for c in candidates:
                cid = c.get("id")
                if cid and cid not in _FLEET_IN_FLIGHT:
                    _FLEET_IN_FLIGHT.add(cid)
                    candidate = c
                    break
        if not candidate:
            print(f"[INFO] All candidate GPUs are in-flight. Retrying in {retry_sleep}s...")
            time.sleep(retry_sleep)
            retry_sleep = min(retry_sleep * 2, 300)
            continue

        candidate_id = candidate.get("id")
        candidate_display = candidate.get("displayName", candidate_id)
        current_image = args.image
        if "AMD" in candidate_display or "MI" in candidate_display:
            current_image = "runpod/pytorch:2.1.0-py3.10-rocm5.7-devel-ubuntu22.04"
        pod_name = role["name"]
        print(f"[INFO] Launching pod '{pod_name}' with GPU: {candidate_display}...")
        pod_result = bridge.create_pod(
            name=pod_name,
            gpu_type_id=candidate_id,
            template_id=args.template,
            image=current_image,
            ssh_key_value=args.ssh_key_value,
            data_center_id=args.data_center,
            volume_id=args.volume_id,
            volume_mount_path=args.volume_mount_path,
            env={
                "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
                "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
                "AWS_SESSION_TOKEN": os.environ.get("AWS_SESSION_TOKEN"),
                "AWS_DEFAULT_REGION": args.s3_region,
                "HF_TOKEN": os.environ.get("HF_TOKEN"),
            },
        )
        if not pod_result:
            print(f"[WARN] Failed to create pod for role {role['role']}.")
            with _FLEET_LOCK:
                if candidate_id in _FLEET_IN_FLIGHT:
                    _FLEET_IN_FLIGHT.remove(candidate_id)
            time.sleep(retry_sleep)
            retry_sleep = min(retry_sleep * 2, 300)
            continue

        pod_id = pod_result["id"]
        with _FLEET_LOCK:
            if candidate_id in _FLEET_IN_FLIGHT:
                _FLEET_IN_FLIGHT.remove(candidate_id)
        print(f"[INFO] Pod {pod_id} launched for role {role['role']}. Waiting for runtime...")
        while True:
            pods = bridge.get_pods()
            pod = next((p for p in pods if p['id'] == pod_id), None)
            if pod and pod.get("runtime") and pod["runtime"].get("uptimeInSeconds", 0) > 0:
                break
            time.sleep(10)

        # SSH details
        public_ports = [p for p in pod.get("runtime", {}).get("ports", []) if p.get("isIpPublic")]
        ssh_port_info = next((p for p in public_ports if p.get("privatePort") == 22), None)
        if not ssh_port_info and public_ports:
            ssh_port_info = public_ports[0]
        if not ssh_port_info:
            pod_ip = "ssh.runpod.io"
            pod_port = 22
            proxy = f"{pod_id}-22@ssh.runpod.io"
        else:
            pod_ip = ssh_port_info["ip"]
            pod_port = ssh_port_info["publicPort"]
            proxy = None

        # Setup + sync
        setup_pod_env(pod_ip, pod_port, args.ssh_key, pod_id, proxy)
        sync_code(pod_ip, pod_port, args.ssh_key, REPO_ROOT, role["workdir"], pod_id, proxy)
        ensure_mavaia_installed(
            pod_ip, pod_port, args.ssh_key, role["workdir"], pod_id, proxy,
            s3_bucket=args.s3_bucket if args.use_s3 else None,
            s3_prefix=args.s3_prefix if args.use_s3 else None,
            s3_region=args.s3_region if args.use_s3 else None,
            s3_endpoint=args.s3_endpoint if args.use_s3 else None,
            force_reinstall=args.force_refresh,
            pip_debug=args.pip_debug,
            pip_stream=args.pip_stream,
            editable_install=args.editable_install,
        )

        if role["role"] == "distill" and not args.no_ollama:
            setup_ollama(pod_ip, pod_port, args.ssh_key, args.teacher_model, args.ollama_model_dir, pod_id, proxy)

        if role["role"] == "auditor":
            _run_ssh(args.ssh_key, pod_ip, pod_port, pod_id, proxy, _fleet_auditor_cmd(role["workdir"]))
        else:
            train_args = list(role["train_args"])
            script_rel = role.get("script", "scripts/train_neural_text_generator.py")
            if script_rel.endswith("train_neural_text_generator.py") and "--plain-output" not in train_args:
                train_args.append("--plain-output")
            remote_train(pod_ip, pod_port, args.ssh_key, train_args, role["workdir"], pod_id, proxy, script_rel=script_rel)

        # Best-effort termination to avoid leaks; restart loop will acquire a new pod if needed.
        try:
            bridge.terminate_pod(pod_id)
        except Exception:
            pass

        # If training ends, loop to restart
        print(f"[WARN] Role {role['role']} completed or failed; restarting search.")
        pod_id = None

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
            # Swap to RunPod SSH proxy (update port + host entries)
            ssh_cmd[8] = "22"
            ssh_cmd[9] = f"{pod_id}-22@ssh.runpod.io"
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
    parser.add_argument("--fleet", action="store_true", help="Enable parallel fleet mode (3 pods max)")
    parser.add_argument("--auto", action="store_true", help="Auto-manage: terminate active pods, pick best GPU under $0.50/hr, and train")
    parser.add_argument("--max-price", type=float, default=1.50, help="Max hourly price for auto GPU selection")
    parser.add_argument("--min-price", type=float, default=0.50, help="Min hourly price for auto GPU selection")
    parser.add_argument("--auto-price-range", type=str, default="0.50-1.50", help="Auto price range min-max (overrides min/max if set)")
    parser.add_argument("--auto-price-step", type=float, default=0.05, help="Step size for auto price range scan")
    parser.add_argument("--min-vram", type=int, default=24, help="Minimum VRAM (GB) for GPU selection")
    parser.add_argument("--min-balance", type=float, default=5.0, help="Minimum balance required to run (USD)")
    parser.add_argument("--balance-watchdog-seconds", type=int, default=60, help="Balance check interval (seconds)")
    parser.add_argument("--terminate", action="store_true", help="Terminate pod after training")
    parser.add_argument("--dry-run", action="store_true", help="Just print commands")
    parser.add_argument("--watchdog-minutes", type=float, default=10.0, help="Watchdog interval (minutes) to snapshot/sync during training (0 disables)")
    parser.add_argument("--no-watchdog", action="store_true", help="Disable watchdog snapshots during training")
    parser.add_argument("--rich-output", action="store_true", help="Enable rich (non-ASCII) output in training logs")
    parser.add_argument("--teacher-model", default="phi4:latest", help="Ollama teacher model to pull (default: phi4:latest)")
    parser.add_argument("--ollama-model-dir", default="/workspace/ollama", help="Ollama model storage dir (default: /workspace/ollama)")
    parser.add_argument("--no-ollama", action="store_true", help="Skip Ollama setup")
    parser.add_argument("--distill-precompute-minutes", type=float, default=15.0, help="Max minutes to precompute distill cache before training (0 disables limit)")
    parser.add_argument("--data-center", default="EU-RO-1", help="RunPod data center ID (default: EU-RO-1)")
    parser.add_argument("--s3-bucket", default="sxzm7zw9w9", help="RunPod S3 bucket name")
    parser.add_argument("--s3-region", default="eu-ro-1", help="RunPod S3 region")
    parser.add_argument("--s3-endpoint", default="https://s3api-eu-ro-1.runpod.io", help="RunPod S3 endpoint URL")
    parser.add_argument("--s3-prefix", default="mavaia", help="S3 prefix for repo/workspace sync")
    parser.add_argument("--s3-ollama-prefix", default="ollama", help="S3 prefix for Ollama model storage")
    parser.add_argument("--use-s3", action="store_false", dest="use_s3", default=True, help="Disable S3 sync (enabled by default)")
    parser.add_argument("--no-refresh-code", action="store_false", dest="force_refresh", default=True, help="Skip forcing pod code refresh (faster, but may use stale code)")
    parser.add_argument("--hf-token", default=None, help="Hugging Face token (overrides env HF_TOKEN)")
    parser.add_argument("--volume-id", default=os.environ.get("RUNPOD_VOLUME_ID", ""), help="Attach an existing RunPod network volume by ID (default: RUNPOD_VOLUME_ID or empty)")
    parser.add_argument("--alias", default="mavaia_train", help="Alias for pod name (default: mavaia_train)")
    parser.add_argument("--volume-mount-path", default="/workspace", help="Mount path for the attached volume")
    parser.add_argument("--auto-distill", action="store_true", help="Auto-inject distillation args for transformer training")
    parser.add_argument("--distill-alpha", type=float, default=0.7, help="Hard loss weight for distillation")
    parser.add_argument("--distill-temp", type=float, default=2.0, help="Distillation temperature")
    parser.add_argument("--distill-topk", type=int, default=20, help="Top-k logprobs for teacher distillation")
    parser.add_argument("--no-editable-install", action="store_false", dest="editable_install", default=True, help="Disable editable install for mavaia.")
    parser.add_argument("--force-editable", action="store_true", dest="editable_install_forced", help="Force editable install.")
    
    # Forwarded args
    parser.add_argument("train_args", nargs=argparse.REMAINDER, help="Args for training script")
    parser.add_argument(
        "--curriculum",
        action="store_true",
        help="Run curriculum training (scripts/train_curriculum.py) instead of standard training.",
    )
    parser.add_argument(
        "--fleet-curriculum",
        action="store_true",
        help="In fleet mode, run curriculum training for the normal role instead of standard training.",
    )
    parser.add_argument(
        "--pip-debug",
        action="store_true",
        help="Show full pip install logs while setting up the pod venv.",
    )
    parser.add_argument(
        "--pip-stream",
        action="store_true",
        help="Stream pip install output live instead of periodic status logs.",
    )
    parser.add_argument(
        "--no-pip-stream",
        action="store_true",
        help="Disable live pip output streaming (use periodic status logs).",
    )

    args = parser.parse_args()
    if args.editable_install_forced:
        args.editable_install = True
    if not args.no_pip_stream:
        args.pip_stream = True


    if not RUNPOD_API_KEY:
        print("[!] Error: Mavaia_Key not found in .env")
        sys.exit(1)

    bridge = RunPodBridge(RUNPOD_API_KEY)
    def _balance_watchdog():
        while True:
            bal = bridge.get_balance()
            if bal is None:
                time.sleep(max(30, args.balance_watchdog_seconds))
                continue
            if bal < args.min_balance:
                if not _BALANCE_LOW.is_set():
                    _BALANCE_LOW.set()
                    print(f"[WARN] Balance ${bal:.2f} below ${args.min_balance:.2f}. Stopping pods.")
                    try:
                        for p in bridge.get_pods():
                            if str(p.get("name", "")).startswith("mavaia_"):
                                bridge.terminate_pod(p["id"])
                    except Exception:
                        pass
            else:
                if _BALANCE_LOW.is_set():
                    _BALANCE_LOW.clear()
                    print(f"[INFO] Balance ${bal:.2f} >= ${args.min_balance:.2f}. Resuming.")
            time.sleep(max(30, args.balance_watchdog_seconds))
    
    # Load s3.env if available
    s3_env_path = REPO_ROOT / "s3.env"
    if s3_env_path.exists():
        for line in s3_env_path.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                name = k.strip().upper()
                # RunPod S3 uses these env var names
                if name == "AWS_ACCESS_KEY_ID" or name == "AWS_SECRET_ACCESS_KEY":
                    os.environ[name] = v.strip().strip('"').strip("'")
        print(f"[*] Loaded S3 credentials from {s3_env_path}")

    if args.hf_token:
        os.environ["HF_TOKEN"] = args.hf_token

    pod_env = {
        "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
        "AWS_SESSION_TOKEN": os.environ.get("AWS_SESSION_TOKEN"),
        "AWS_DEFAULT_REGION": args.s3_region,
        "HF_TOKEN": os.environ.get("HF_TOKEN"),
    }
    
    if not args.ssh_key_value:
        pub_key_path = Path(args.ssh_key).with_suffix(".pub")
        if pub_key_path.exists():
            args.ssh_key_value = pub_key_path.read_text().strip()
            print(f"[*] Auto-loaded public SSH key from {pub_key_path}")

    if args.volume_id:
        args.use_s3 = False
    else:
        # If no volume ID, we can search globally for better inventory
        if args.use_s3:
            print("[*] S3 persistence enabled with no volume lock: searching all data centers for optimal GPUs...")
            args.data_center = None

    if args.use_s3:
        if not shutil.which("aws"):
            print("[!] aws CLI not found on VPS. Install awscli or use --no-s3.")
            sys.exit(1)

    auto_timeout_s = None
    if args.curriculum and not args.auto and not args.fleet and not args.pod_id:
        print("[INFO] Curriculum mode enabled; auto pod search activated (5 minute limit).")
        args.auto = True
        auto_timeout_s = 300

    pod = None
    auto_candidate_gpus = None
    if args.fleet:
        threading.Thread(target=_balance_watchdog, daemon=True).start()
        if not args.volume_id:
            print("[ERROR] Fleet mode requires --volume-id (200GB network volume).")
            sys.exit(1)
        if args.volume_mount_path != "/workspace":
            print("[WARN] Fleet mode expects volume mounted at /workspace. Overriding.")
            args.volume_mount_path = "/workspace"
        roles = _fleet_role_specs(args)
        stop_event = threading.Event()
        workers = []
        for role in roles:
            t = threading.Thread(target=_fleet_worker, args=(bridge, args, role, stop_event), daemon=True)
            t.start()
            workers.append(t)
        print("[INFO] Fleet mode active. Press CTRL+C to stop.")
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            print("[INFO] Stopping fleet...")
            stop_event.set()
        return 0

    if args.auto:
        threading.Thread(target=_balance_watchdog, daemon=True).start()
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

        gpu_types = bridge.get_gpu_types_with_availability()
        if not gpu_types:
            print("[WARN] Unable to fetch GPU availability right now. Retrying shortly...")
            time.sleep(10)
            gpu_types = bridge.get_gpu_types_with_availability()
        if not gpu_types:
            print("[ERROR] Unable to fetch GPU availability. Aborting.")
            sys.exit(1)
        
        # Estimate storage cost (~$0.01 per 10GB per hour as a rough safe buffer)
        storage_overhead = 0.20 # 200GB vol + 200GB disk

        filtered_gpus = [
            g for g in gpu_types
            if bridge.gpu_is_available(g)
            if g.get('securePrice') is not None 
            and (g['securePrice'] + storage_overhead) >= min_price
            and (g['securePrice'] + storage_overhead) <= max_price
            and g.get('memoryInGb') is not None
            and g.get('memoryInGb') >= args.min_vram
        ]

        if not filtered_gpus:
            print(f"[!] No suitable GPUs found under your max price of ${max_price}/hr (min required VRAM: {args.min_vram}GB).")
            sys.exit(1)

        # Sort by total cost ascending, then memory descending
        filtered_gpus.sort(key=lambda x: (x['securePrice'], -x['memoryInGb']))
        
        best_gpu = filtered_gpus[0]
        gpu_id = best_gpu['id']
        auto_candidate_gpus = filtered_gpus
        
        total_estimated = round(best_gpu['securePrice'] + storage_overhead, 2)
        print(f"[*] Best value candidate: {best_gpu['displayName']} ({best_gpu['memoryInGb']}GB VRAM @ ${best_gpu['securePrice']}/hr + ${storage_overhead} storage = ${total_estimated}/hr)")
        print(f"[*] Total valid candidates in range: {len(filtered_gpus)}")
    elif args.pod_id:
        # Resume existing pod flow
        pods = bridge.get_pods()
        pod = next((p for p in pods if p['id'] == args.pod_id), None)
        if not pod:
            print(f"[!] Pod {args.pod_id} not found.")
            sys.exit(1)
        
        # Check if pod needs starting
        if not pod.get("runtime"):
            print(f"[*] Pod {args.pod_id} is stopped. Starting it...")
            # mutation PodResume($input: PodResumeInput!) { podResume(input: $input) { id } }
            bridge._query("""
                mutation ResumePod($input: PodResumeInput!) {
                    podResume(input: $input) {
                        id
                    }
                }
            """, variables={"input": {"podId": args.pod_id, "gpuCount": 1}})
            
            print(f"[*] Waiting for pod {args.pod_id} to initialize runtime...")
            while True:
                pods = bridge.get_pods()
                pod = next((p for p in pods if p['id'] == args.pod_id), None)
                if pod and pod.get("runtime") and pod["runtime"].get("uptimeInSeconds", 0) > 0:
                    break
                time.sleep(10)

        gpu_id = None # Signal that no new pod creation is needed
    else:
        print(f"[*] No pod specified. Finding GPU ID for {args.gpu}...")
        gpu_types = bridge.get_gpu_types_with_availability()
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


    if args.use_s3:
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
            gpu_info_list = bridge.get_gpu_types_with_availability()
            gpu_info = next((g for g in gpu_info_list if g.get("id") == gpu_id), None)
            if gpu_info and gpu_info.get("memoryInGb") is not None and gpu_info.get("memoryInGb") < args.min_vram:
                print(f"[!] GPU {gpu_info.get('displayName', gpu_id)} has {gpu_info.get('memoryInGb')}GB VRAM; minimum is {args.min_vram}GB.")
                sys.exit(1)
        except Exception:
            pass

        candidate_gpus = auto_candidate_gpus if args.auto else [{"id": gpu_id, "displayName": gpu_id}]
        retry_sleep = 30
        auto_start = time.time() if auto_timeout_s else None
        while True:
            if auto_start and (time.time() - auto_start) >= auto_timeout_s:
                print("[INFO] Auto search timed out after 5 minutes. Exiting.")
                sys.exit(1)
            if args.auto:
                print("[INFO] Refreshing GPU availability...")
                gpu_types = bridge.get_gpu_types_with_availability()
                filtered_gpus = [
                    g for g in gpu_types
                    if bridge.gpu_is_available(g)
                    if g.get('securePrice') is not None
                    and (g['securePrice'] + storage_overhead) >= min_price
                    and (g['securePrice'] + storage_overhead) <= max_price
                    and g.get('memoryInGb') is not None
                    and g.get('memoryInGb') >= args.min_vram
                ]
                if filtered_gpus:
                    filtered_gpus.sort(key=lambda x: (x['securePrice'], -x['memoryInGb']))
                    candidate_gpus = filtered_gpus
                else:
                    candidate_gpus = []
            for candidate in candidate_gpus:
                if _BALANCE_LOW.is_set():
                    print(f"[WARN] Balance below ${args.min_balance:.2f}. Auto mode paused.")
                    time.sleep(min(60, retry_sleep))
                    continue
                candidate_id = candidate.get("id") if isinstance(candidate, dict) else candidate
                candidate_display = candidate.get("displayName") if isinstance(candidate, dict) else candidate_id
                availability_snapshot = bridge.get_gpu_types_with_availability()
                candidate_info = next((g for g in availability_snapshot if g.get("id") == candidate_id), None)
                if candidate_info is not None and not bridge.gpu_is_available(candidate_info):
                    print(f"[WARN] GPU {candidate_display} is not available right now. Skipping.")
                    continue

                # Auto-switch image for AMD ROCm
                current_image = args.image
                if "AMD" in candidate_display or "MI" in candidate_display:
                    print(f"[*] Detected AMD GPU ({candidate_display}). Switching to ROCm image.")
                    current_image = "runpod/pytorch:2.1.0-py3.10-rocm5.7-devel-ubuntu22.04"
                    pod_env["HSA_OVERRIDE_GFX_VERSION"] = "11.0.0"
                else:
                    # Reset for NVIDIA if it was changed by a previous candidate in the loop
                    pod_env.pop("HSA_OVERRIDE_GFX_VERSION", None)

                pod_name = args.alias or "mavaia_train"
                print(f"[*] Launching pod '{pod_name}' with GPU: {candidate_display}...")
                if args.dry_run:
                    print(f"[DRY-RUN] Would launch {candidate_display} pod with template {args.template}")
                    pod = {"id": "dry-run-id", "runtime": {"ports": [{"ip": "1.2.3.4", "publicPort": 1234, "isIpPublic": True}]}}
                    break
                pod_result = bridge.create_pod(
                    name=pod_name,
                    gpu_type_id=candidate_id,
                    template_id=args.template,
                    image=current_image,
                    ssh_key_value=args.ssh_key_value,
                    data_center_id=args.data_center,
                    volume_id=args.volume_id,
                    volume_mount_path=args.volume_mount_path,
                    env=pod_env,
                )
                if not pod_result:
                    print(f"[!] Failed to create pod with {candidate_display}, trying next candidate...")
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

            if pod:
                break

            print("[WARN] Failed to create pod with any candidate GPU.")
            if args.auto and not args.dry_run:
                print(f"[INFO] Capacity constrained. Retrying in {retry_sleep}s...")
                print("[INFO] Refreshing availability before retry.")
                time.sleep(retry_sleep)
                retry_sleep = min(retry_sleep * 2, 300)
                continue

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
        if pod and pod.get("id"):
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
        
        # ALWAYS sync code via rsync as well to ensure latest diagnostic fixes are present
        sync_code(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
        
        # ensure_mavaia_installed handles S3 archive restore internally when use_s3 is set
        ensure_mavaia_installed(
            pod_ip, pod_port, args.ssh_key, args.volume_mount_path, pod['id'], args.ssh_proxy,
            s3_bucket=args.s3_bucket if args.use_s3 else None,
            s3_prefix=args.s3_prefix if args.use_s3 else None,
            s3_region=args.s3_region if args.use_s3 else None,
            s3_endpoint=args.s3_endpoint if args.use_s3 else None,
            force_reinstall=args.force_refresh,
            pip_debug=args.pip_debug,
            pip_stream=args.pip_stream,
            editable_install=args.editable_install,
        )
        ollama_cache_pull_failed = False
        if args.use_s3:
            # Pull Ollama models from S3 if they were cached there (soft fail on first run)
            try:
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
            except Exception as e:
                ollama_cache_pull_failed = True
                # If a cache object exists but we can't extract it on the pod, it's likely corrupt; invalidate it.
                ollama_s3_key = f"s3://{args.s3_bucket}/{args.s3_ollama_prefix}/mavaia.tar"
                aws_flags = []
                if args.s3_region:
                    aws_flags += ["--region", args.s3_region]
                if args.s3_endpoint:
                    aws_flags += ["--endpoint-url", args.s3_endpoint]
                try:
                    if subprocess.run(["aws", "s3", "ls", ollama_s3_key] + aws_flags, capture_output=True, check=False).returncode == 0:
                        subprocess.run(["aws", "s3", "rm", ollama_s3_key] + aws_flags, capture_output=True, check=False)
                        print(f"[*] Invalidated Ollama S3 cache at {ollama_s3_key} (will re-upload after fresh pull).")
                except Exception:
                    pass
                print(f"[*] Ollama S3 cache pull failed; Ollama will download models fresh. ({_redact_secrets(str(e))})")
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
            if args.use_s3:
                # Only push Ollama cache to S3 if it doesn't exist yet — skip re-uploading 9GB every run
                ollama_s3_key = f"s3://{args.s3_bucket}/{args.s3_ollama_prefix}/mavaia.tar"
                aws_check_flags = []
                if args.s3_region:
                    aws_check_flags += ["--region", args.s3_region]
                if args.s3_endpoint:
                    aws_check_flags += ["--endpoint-url", args.s3_endpoint]
                cache_exists = subprocess.run(
                    ["aws", "s3", "ls", ollama_s3_key] + aws_check_flags,
                    capture_output=True, check=False,
                ).returncode == 0
                if cache_exists and not ollama_cache_pull_failed:
                    print(f"[*] Ollama S3 cache already exists at {ollama_s3_key}, skipping re-upload.")
                else:
                    print(f"[*] Ollama S3 cache not found (or invalidated) — uploading for future runs...")
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
                            print("[INFO] Watchdog: snapshot + sync")
                            remote_snapshot(pod_ip, pod_port, args.ssh_key, args.volume_mount_path, pod['id'], args.ssh_proxy)
                            get_artifacts(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
                            sync_training_data(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
                        except Exception as e:
                            print(f"[WARN] Watchdog failed: {e}")

                watchdog_thread = threading.Thread(target=_watchdog_loop, daemon=True)
                watchdog_thread.start()

        train_args = list(args.train_args)
        script_rel = "scripts/train_neural_text_generator.py"
        if args.curriculum:
            script_rel = "scripts/train_curriculum.py"
        else:
            if not args.rich_output and "--plain-output" not in train_args:
                train_args.append("--plain-output")
            if args.auto_distill:
                if "--distill" not in train_args:
                    train_args.extend(
                        [
                            "--distill",
                            "--teacher-model", args.teacher_model,
                            "--distill-alpha", str(args.distill_alpha),
                            "--distill-temp", str(args.distill_temp),
                            "--distill-topk", str(args.distill_topk),
                            "--distill-precompute-minutes", str(args.distill_precompute_minutes),
                        ]
                    )
                if "--model-type" not in train_args and "--model_type" not in train_args:
                    train_args.extend(["--model-type", "transformer"])
            else:
                # Enforce distillation off unless explicitly enabled.
                distill_flags = {
                    "--distill",
                    "--teacher-model",
                    "--distill-alpha",
                    "--distill-temp",
                    "--distill-topk",
                    "--distill-precompute-minutes",
                    "--ollama-url",
                    "--teacher-cache-dir",
                }
                cleaned = []
                it = iter(range(len(train_args)))
                i = 0
                while i < len(train_args):
                    arg = train_args[i]
                    if arg in distill_flags:
                        # Skip flag and its value if present.
                        if i + 1 < len(train_args) and not train_args[i + 1].startswith("--"):
                            i += 2
                        else:
                            i += 1
                        continue
                    cleaned.append(arg)
                    i += 1
                if cleaned != train_args:
                    print("[INFO] Distillation disabled (use --auto-distill to enable).")
                train_args = cleaned

        remote_train(
            pod_ip,
            pod_port,
            args.ssh_key,
            train_args,
            args.volume_mount_path,
            pod['id'],
            args.ssh_proxy,
            script_rel=script_rel,
        )
        get_artifacts(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
        sync_training_data(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
        if args.use_s3:
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
        print("[*] CTRL+C detected: giving pod SSH 5s to stabilize...")
        time.sleep(5)
        print("[*] Attempting to save snapshot and sync artifacts before exit...")
        try:
            remote_snapshot(pod_ip, pod_port, args.ssh_key, args.volume_mount_path, pod['id'], args.ssh_proxy)
        except Exception as e:
            print(f"[!] Snapshot failed (likely process already dead): {_redact_secrets(str(e))}")
        
        # Retry artifact pull up to 3 times
        for attempt in range(3):
            try:
                print(f"[*] Syncing artifacts (attempt {attempt+1}/3)...")
                get_artifacts(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
                sync_training_data(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
                print("[✓] Sync successful!")
                break
            except Exception as e:
                print(f"[!] Sync attempt {attempt+1} failed: {_redact_secrets(str(e))}")
                if attempt < 2:
                    time.sleep(5)
    except Exception as e:
        failed = True
        print(f"[!] Error detected: {_redact_secrets(str(e))}. Saving snapshot and syncing artifacts before exit...")
        try:
            remote_snapshot(pod_ip, pod_port, args.ssh_key, args.volume_mount_path, pod['id'], args.ssh_proxy)
        except Exception as snap_e:
            print(f"[!] Snapshot failed: {snap_e}")
        try:
            get_artifacts(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
            sync_training_data(pod_ip, pod_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, pod['id'], args.ssh_proxy)
            if args.use_s3:
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
                try:
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
                except Exception as ollama_e:
                    print(f"[*] Ollama S3 push skipped: {ollama_e}")
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
