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
import math
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add project root to path to allow importing mavaia_core
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# Try to import Mavaia parser
try:
    from mavaia_core.evaluation.livebench_parser import LiveBenchResultParser
except ImportError:
    LiveBenchResultParser = None

# Try to import rich for beautiful output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich import box
    from rich.markup import escape

    console = Console()
    USE_RICH = True
except ImportError:
    USE_RICH = False
    console = None
    escape = lambda x: x

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


def _rich_log(message: str, style: str = "white", icon: str = "", progress=None, task_id=None):
    # Remove old-school prefixes if they exist in the message string
    message = re.sub(r"^\[(\*|INFO|ERROR|WARN|SUCCESS|!|DRY-RUN)\]\s*", "", message)

    if progress and task_id is not None:
        icon_str = f"{icon} " if icon else ""
        safe_msg = escape(message)
        progress.update(task_id, description=f"[{style}]{icon_str}{safe_msg}[/{style}]")
        return

    if USE_RICH:
        icon_str = f"{icon} " if icon else ""
        console.print(f"[{style}]{icon_str}{message}[/{style}]")
    else:
        print(f"{icon} {message}" if icon else message)


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


def calculate_required_vram(
    model_type: str, dataset_size_chars: int = 0, batch_size: int = 4, sequence_length: int = 512
) -> int:
    """
    Estimate minimum VRAM required for a training task.
    Returns value in GB.
    """
    # 1. Base Footprint (Model + Optimizer State)
    # RNNs are very small
    if model_type in ("character", "word"):
        base_gb = 4
    else:
        # Transformer defaults to GPT-2 (124M) or DistilGPT-2 (82M)
        # Training GPT-2 with Adam needs ~10-12GB for stability
        base_gb = 12

    # 2. Dataset Scaling (Data loading buffer, shuffling, caching)
    # Add ~1GB for every 200M characters of data
    data_gb = math.ceil(dataset_size_chars / 200_000_000)

    # 3. Hyperparameter Scaling
    # Batch size: linear scaling
    # Sequence length: quadratic scaling for self-attention
    hp_multiplier = (batch_size / 4) * ((sequence_length / 512) ** 2)

    # Total calculation
    estimated = base_gb + data_gb + (2 * hp_multiplier)

    # Add a safety headroom (20%)
    total_with_headroom = math.ceil(estimated * 1.2)

    # Floor at 8GB for modern torch/transformers stability
    return max(8, total_with_headroom)


def get_task_details(args) -> Dict[str, Any]:
    """
    Extract model type, dataset size (est), batch size, and sequence length from args or curriculum.
    """
    model_type = "transformer"  # default
    dataset_size = 0
    batch_size = 4  # default
    seq_len = 512  # default

    # 1. Check if we're in curriculum mode
    if args.curriculum:
        try:
            # Import stage defs to see what's coming
            sys.path.insert(0, str(REPO_ROOT))
            from scripts.train_curriculum import _stage_defs

            stages = _stage_defs(1, 1.0, False)

            # Determine which stage we're targeting
            target_stage = None
            if args.stage:
                # Use first stage in range
                if "-" in str(args.stage):
                    try:
                        start_idx = int(str(args.stage).split("-")[0])
                        target_stage = stages[start_idx - 1]
                    except (ValueError, IndexError):
                        pass
                else:
                    try:
                        idx = int(str(args.stage))
                        target_stage = stages[idx - 1]
                    except (ValueError, IndexError):
                        target_stage = next(
                            (s for s in stages if str(args.stage) in s["name"]), None
                        )

            if not target_stage:
                # Try to find next pending from progress.json
                prog_path = (
                    REPO_ROOT
                    / "mavaia_core"
                    / "models"
                    / "neural_text_generator"
                    / "curriculum"
                    / "curriculum_progress.json"
                )
                if not prog_path.exists():
                    prog_path = (
                        REPO_ROOT
                        / "models"
                        / "neural_text_generator_remote"
                        / "curriculum"
                        / "curriculum_progress.json"
                    )

                if prog_path.exists():
                    try:
                        prog_data = json.loads(prog_path.read_text())
                        # In real run, the next pending stage would be targeted
                        target_name = prog_data.get("current_stage")
                        if target_name:
                            target_stage = next(
                                (s for s in stages if s["name"] == target_name), None
                            )
                    except Exception:
                        pass

            if not target_stage:
                target_stage = stages[0]  # fallback

            if target_stage:
                # Estimate dataset size (heuristics)
                ds_name = str(target_stage.get("dataset", ""))
                if "fineweb" in ds_name or "wikipedia" in ds_name:
                    dataset_size = 1_000_000_000  # 1GB est
                elif "booksum" in ds_name:
                    dataset_size = 500_000_000
                elif "hotpot" in ds_name or "orca" in ds_name:
                    dataset_size = 200_000_000
                else:
                    dataset_size = 50_000_000
        except Exception:
            pass

    # 2. Extract from train_args if provided
    if args.train_args:
        # Simple parser for forwarded args
        for i, arg in enumerate(args.train_args):
            if arg == "--batch-size" and i + 1 < len(args.train_args):
                try:
                    batch_size = int(args.train_args[i + 1])
                except ValueError:
                    pass
            elif arg == "--model-type" and i + 1 < len(args.train_args):
                model_type = args.train_args[i + 1]

    # 3. Explicit args on bridge take precedence
    if args.batch_size:
        batch_size = args.batch_size

    return {
        "model_type": model_type,
        "dataset_size": dataset_size,
        "batch_size": batch_size,
        "sequence_length": seq_len,
    }


class RunPodBridge:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else "",
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
                    if code == "SUPPLY_CONSTRAINT":
                        continue
                    _rich_log(f"RunPod: {code} - {msg}", "red", "✗")
                else:
                    _rich_log(f"RunPod: {msg}", "red", "✗")
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
            env_vars.append({"key": "RUNPOD_PUBLIC_KEY", "value": ssh_key_value})
            env_vars.append({"key": "TCP_PORT_22", "value": ssh_key_value})
            env_vars.append({"key": "SSH_KEY", "value": ssh_key_value})

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


def setup_pod_env(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    pod_id: str = None,
    proxy: str = None,
    progress=None,
    task_id=None,
    bridge: "RunPodBridge" = None,
):
    # Determine targets
    direct_target = None
    if pod_ip and str(pod_ip) != "ssh.runpod.io":
        direct_target = {"host": f"root@{pod_ip}", "port": str(pod_port)}

    proxy_target = None
    if proxy:
        proxy_target = {"host": proxy, "port": "22"}
    elif pod_id:
        proxy_target = {"host": f"{pod_id}-22@ssh.runpod.io", "port": "22"}

    # Skip install if rsync and aws are already present
    check_cmd = "command -v rsync >/dev/null 2>&1 && command -v aws >/dev/null 2>&1"
    install_cmd = (
        "apt-get update -qq && apt-get install -y rsync python3-venv curl zstd pciutils mbuffer -qq && "
        "python3 -m pip install --upgrade pip -q && "
        "if ! command -v aws >/dev/null 2>&1; then pip install --upgrade awscli -q; fi"
    )
    full_cmd = f"if ! ({check_cmd}); then {install_cmd}; fi"

    max_retries = 40
    for i in range(max_retries):
        # STRATEGY:
        # If we have a direct IP, stick to it for the first 10 attempts (give the service time to start).
        # After that, alternate with proxy in case direct IP is firewalled/unreliable.
        if direct_target:
            if i < 10:
                method = direct_target
            else:
                method = direct_target if i % 2 == 0 else proxy_target
        else:
            method = proxy_target

        if not method:
            raise RuntimeError("No SSH target (Direct or Proxy) available.")

        is_proxy = "ssh.runpod.io" in method["host"]

        # If the pod is already gone, don't spin on SSH retries.
        if bridge and pod_id and i % 3 == 0:
            try:
                pods = bridge.get_pods()
                if not any(p.get("id") == pod_id for p in pods):
                    raise RuntimeError(f"Pod {pod_id} not found; SSH target is stale")
            except Exception as e:
                if "not found" in str(e).lower():
                    raise

        # Single line status with counter
        _rich_log(
            f"Stabilizing SSH connection ({i+1}/{max_retries})...",
            "cyan",
            "⏳",
            progress=progress,
            task_id=task_id,
        )

        # Try a quick handshake check
        try:
            # Force root for direct IP connections (Standard for RunPod)
            target = f"root@{method['host'].split('@')[-1]}" if not is_proxy else method["host"]

            subprocess.run(
                _ssh_base(ssh_key, method["port"], target) + ["true"],
                check=True,
                capture_output=True,
                timeout=15,
                text=True,
            )

            # If handshake succeeded, run the environment setup
            _rich_log(
                "Connection stable! Preparing environment...",
                "cyan",
                "🛠",
                progress=progress,
                task_id=task_id,
            )
            subprocess.run(
                _ssh_base(ssh_key, method["port"], target) + [full_cmd],
                check=True,
                capture_output=bool(progress),
                text=True,
            )
            _rich_log(
                "Pod environment ready!", "bold green", "✓", progress=progress, task_id=task_id
            )
            return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raw = ""
            if isinstance(e, subprocess.CalledProcessError):
                raw = (e.stderr or e.stdout or f"exit {e.returncode}").strip()
            else:
                raw = "Handshake timed out"

            # Clean up the raw message for the UI
            diag_msg = raw.splitlines()[-1] if "\n" in raw else raw
            if "Connection closed" in raw or "exit 255" in raw:
                diag_msg = "Proxy routing not established yet (Normal for new pods)"
            elif "Connection refused" in raw:
                diag_msg = "SSH service starting"
            elif "Permission denied" in raw:
                diag_msg = "Authentication failed (checking key)"

            _rich_log(
                f"SSH not ready ({method['host']}): {diag_msg}",
                "dim",
                "…",
                progress=progress,
                task_id=task_id,
            )

            if i < max_retries - 1:
                # MANDATORY GRACE: If it's the first proxy failure, wait significantly longer
                # Global proxy routing can take up to 60-90s to propagate
                if is_proxy and i == 0:
                    _rich_log(
                        "First proxy attempt failed; waiting 60s for global routing propagation...",
                        "dim",
                        "⏳",
                        progress=progress,
                        task_id=task_id,
                    )
                    time.sleep(60)
                else:
                    # Increasing delay for proxy attempts
                    delay = 20 if is_proxy and i < 10 else 5
                    time.sleep(delay)
                continue

            # Final attempt: run without capture so user can see what's happening
            subprocess.run(_ssh_base(ssh_key, method["port"], target) + [full_cmd], check=True)
            return


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
    progress=None,
    task_id=None,
):
    _rich_log(
        "Ensuring environment is ready (Minimalist Mode)...",
        "cyan",
        "🛠",
        progress=progress,
        task_id=task_id,
    )

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
            f'if [ ! -d {workdir}/mavaia ] || [ "{force_reinstall}" = "True" ] || [ "{force_reinstall}" = "1" ]; then '
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
        'if [ ! -z "$HF_TOKEN" ]; then '
        "  echo '[INFO] Logging into Hugging Face Hub...'; "
        '  huggingface-cli login --token "$HF_TOKEN" --add-to-git-credential >/dev/null 2>&1 || true; '
        "fi; "
        # 1. Determine Python path (Use system if Golden Image, else Venv)
        "if python3 -c 'import torch' >/dev/null 2>&1; then "
        "  echo '[INFO] Golden Image detected (torch found). Using system Python.'; "
        "  if [ -d .venv ]; then echo '[INFO] Removing old isolated .venv...'; rm -rf .venv; fi; "
        '  VENV_PY="python3"; '
        "  echo '[INFO] Purging old mavaia-core installations to ensure fresh code usage...'; "
        '  "$VENV_PY" -m pip uninstall -y mavaia-core 2>/dev/null || true; '
        '  if [ "$force_reinstall" = "True" ] || [ "$force_reinstall" = "1" ]; then '
        "    echo '[INFO] Force refresh: cleaning up potentially broken extras...'; "
        '    "$VENV_PY" -m pip uninstall -y datasets transformers accelerate huggingface_hub pyarrow 2>/dev/null || true; '
        "  fi; "
        "else "
        "  if [ ! -f .venv/bin/activate ]; then "
        "    echo '[INFO] No torch in system. Creating venv...'; "
        "    python3 -m venv --system-site-packages .venv; "
        "  fi; "
        '  VENV_PY="$(pwd)/.venv/bin/python"; '
        "fi; "
        # 2. CLEANUP & SYSTEM INSTALL: Clear the project-root mess and install to system
        "echo '[INFO] Cleaning up project root and ensuring system-level extras...'; "
        "rm -rf datasets transformers accelerate huggingface_hub pyarrow wikipedia regex pandas peft trl numpy PIL torch torchvision torchaudio xxhash multiprocess dill fsspec aiohttp requests tqdm yaml safetensors 2>/dev/null || true; "
        "find . -maxdepth 1 -name '*.so' -delete; "
        "echo '[INFO] Installing core ML libraries (this may take a few minutes)...'; "
        '"$VENV_PY" -m pip install --upgrade datasets transformers accelerate huggingface_hub pyarrow wikipedia regex pandas peft trl numpy Pillow torch torchvision torchaudio xxhash shortuuid libtmux python-dotenv uvicorn fastapi pydantic beautifulsoup4 PyPDF2 PyYAML -q || true; '
        "if [ -d LiveBench ]; then "
        "  echo '[INFO] LiveBench detected. Installing in editable mode...'; "
        '  "$VENV_PY" -m pip install -e LiveBench/ -q || true; '
        "fi; "
        "# 3. Final verification"
        "echo '[INFO] Diagnostic: Listing root files on pod...'; ls -F; "
        "echo '[INFO] Verifying core libraries...'; "
        "if ! \"$VENV_PY\" -c 'import torch; import datasets; import transformers' >/dev/null 2>&1; then "
        "  echo '[ERROR] Core libraries still failing. Traceback details:'; "
        "  \"$VENV_PY\" -c 'import torch' 2>&1 || echo 'Torch failed'; "
        "  \"$VENV_PY\" -c 'import transformers' 2>&1 || echo 'Transformers failed'; "
        "  \"$VENV_PY\" -c 'import datasets' 2>&1 || echo 'Datasets failed'; "
        "  exit 1; "
        "fi; "
        "echo '[SUCCESS] Environment ready. System Python: '$VENV_PY; "
    )

    _run_ssh(ssh_key, pod_ip, pod_port, pod_id, proxy, install_cmd)


def setup_ollama(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    model_name: str,
    model_dir: str,
    pod_id: str = None,
    proxy: str = None,
    progress=None,
    task_id=None,
):
    _rich_log(
        f"Setting up Ollama (model: {model_name})...",
        "cyan",
        "🦙",
        progress=progress,
        task_id=task_id,
    )

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
        ssh_cmd = _ssh_base(ssh_key, "22", proxy) + [ollama_cmd]
        subprocess.run(ssh_cmd, check=True)
        return

    ssh_cmd = _ssh_base(ssh_key, str(pod_port), f"root@{pod_ip}") + [ollama_cmd]
    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError as e:
        if pod_id and e.returncode == 255:
            _rich_log(
                "Direct SSH failed (255); retrying via proxy.",
                "yellow",
                "⚠",
                progress=progress,
                task_id=task_id,
            )
            ssh_cmd = _ssh_base(ssh_key, "22", f"{pod_id}-22@ssh.runpod.io") + [ollama_cmd]
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
            capture_output=True,
            text=True,
            check=False,
        )
        import json as _json

        data = _json.loads(result.stdout or "{}")
        for upload in data.get("Uploads", []):
            key = upload["Key"]
            uid = upload["UploadId"]
            if key.startswith(prefix):
                subprocess.run(
                    [
                        "aws",
                        "s3api",
                        "abort-multipart-upload",
                        "--bucket",
                        bucket,
                        "--key",
                        key,
                        "--upload-id",
                        uid,
                    ]
                    + flags,
                    check=False,
                )
                _rich_log(f"Aborted zombie multipart upload: {key} ({uid[:8]}...)", "dim", "ℹ")
    except Exception as e:
        _rich_log(f"Zombie cleanup skipped: {_redact_secrets(str(e))}", "dim", "ℹ")


def s3_sync_local_to_bucket(
    local_path: Path,
    bucket: str,
    prefix: str,
    region: str,
    endpoint_url: str,
):
    """Stream-archive local repo → S3 as a single tar (fast, no per-file overhead)."""
    _rich_log("Packing and streaming local repo → S3 (tar pipe)...", "cyan", "📦")
    _aws_configure_fast(region, endpoint_url)
    _s3_abort_zombies(bucket, prefix, region, endpoint_url)
    s3_key = f"s3://{bucket}/{prefix}/mavaia.tar"
    tar_cmd = [
        "tar",
        "-cf",
        "-",
        "--exclude=.git",
        "--exclude=__pycache__",
        "--exclude=.venv",
        "--exclude=*.pyc",
        "--exclude=*.tmp",
        "--exclude=.cursor",
        "--exclude=./models",
        "--exclude=./models/*",
        "--exclude=build",
        "--exclude=*.egg-info",
        "--exclude=runs",
        "--exclude=checkpoints",
        "--exclude=snapshots",
        "--exclude=numpy",
        "--exclude=PIL",
        "--exclude=torch",
        "--exclude=transformers",
        "--exclude=datasets",
        "--exclude=accelerate",
        "-C",
        str(local_path),
        ".",
    ]
    # Use mbuffer if available for a smooth 128M in-memory buffer; otherwise pass directly
    use_mbuffer = shutil.which("mbuffer") is not None
    aws_cmd = ["aws", "s3", "cp", "-", s3_key] + _aws_cli_flags(region, endpoint_url)
    _rich_log(
        f"Uploading to {s3_key} {'(mbuffer)' if use_mbuffer else '(direct pipe)'}...", "cyan", "📤"
    )
    tar_proc = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE)
    if use_mbuffer:
        buf_proc = subprocess.Popen(
            ["mbuffer", "-m", "128M", "-q"],
            stdin=tar_proc.stdout,
            stdout=subprocess.PIPE,
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
        raise RuntimeError(
            f"S3 tar upload failed (tar={tar_proc.returncode}, aws={aws_proc.returncode})"
        )
    _rich_log("Repo archive uploaded to S3.", "bold green", "✓")


def _ssh_base(ssh_key: str, port: str, host: str, log_level: str = "ERROR") -> list:
    # Short, reliable SSH defaults for flaky public endpoints.
    return [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        f"LogLevel={log_level}",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "ConnectTimeout=20",
        "-o",
        "TCPKeepAlive=yes",
        "-o",
        "ServerAliveInterval=15",
        "-o",
        "ServerAliveCountMax=3",
        "-i",
        ssh_key,
        "-p",
        port,
        host,
    ]


def _ssh_e(ssh_key: str, port: str) -> str:
    # For rsync/scp -e; mirrors _ssh_base options.
    return (
        "ssh "
        "-o StrictHostKeyChecking=no "
        "-o UserKnownHostsFile=/dev/null "
        "-o LogLevel=ERROR "
        "-o PasswordAuthentication=no "
        "-o IdentitiesOnly=yes "
        "-o ConnectTimeout=20 "
        "-o TCPKeepAlive=yes "
        "-o ServerAliveInterval=15 "
        "-o ServerAliveCountMax=3 "
        f"-i {ssh_key} -p {port}"
    )


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
    progress=None,
    task_id=None,
):
    """Run a remote shell command, with retries and proxy fallback on exit 255."""

    def _try(cmd_list: list) -> None:
        attempt = 0
        while True:
            try:
                subprocess.run(cmd_list, check=check, capture_output=bool(progress))
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
            _rich_log(
                "Direct SSH failed (255); retrying via proxy.",
                "yellow",
                "⚠",
                progress=progress,
                task_id=task_id,
            )
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
    progress=None,
    task_id=None,
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
        "tar -cf - --exclude=.git --exclude=__pycache__ --exclude=.venv "
        "--exclude='*.pyc' --exclude='*.tmp' "
        "--exclude=numpy --exclude=PIL --exclude=torch --exclude=transformers --exclude=datasets --exclude=accelerate "
        "-C {src} . "
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
        _rich_log(
            f"Streaming pod dir {src} -> {s3_key}...",
            "cyan",
            "📤",
            progress=progress,
            task_id=task_id,
        )
    else:  # pull
        cmd = (
            f"{cred_export}{aws_cfg}"
            f"mkdir -p {src} && "
            f"aws s3 cp {s3_key} - {aws_flags} | tar -xf - --no-same-owner -C {src}"
        )
        _rich_log(
            f"Streaming {s3_key} -> pod dir {src}...",
            "cyan",
            "📥",
            progress=progress,
            task_id=task_id,
        )

    _run_ssh(ssh_key, pod_ip, pod_port, pod_id, proxy, cmd, progress=progress, task_id=task_id)


def sync_code(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    local_path: Path,
    workdir: str,
    pod_id: str = None,
    proxy: str = None,
    progress=None,
    task_id=None,
):
    _rich_log("Syncing code to pod...", "cyan", "🔄", progress=progress, task_id=task_id)

    rsync_info = ["--info=stats2,progress2"] if not progress else ["--quiet"]

    # Common excludes for rsync
    common_excludes = [
        "--exclude",
        ".git",
        "--exclude",
        "__pycache__",
        "--exclude",
        ".venv",
        "--exclude",
        ".cursor",
        "--exclude",
        ".vscode",
        "--exclude",
        ".ruff_cache",
        "--exclude",
        "tmp",
        "--exclude",
        "models",
        "--exclude",
        "mavaia_core/models",
        "--exclude",
        "mavaia_core/data",
        "--exclude",
        "data",
        "--exclude",
        "build",
        "--exclude",
        "numpy",
        "--exclude",
        "PIL",
        "--exclude",
        "torch",
        "--exclude",
        "transformers",
        "--exclude",
        "datasets",
        "--exclude",
        "accelerate",
    ]

    if proxy:
        rsync_cmd = (
            [
                "rsync",
                "-az",
                "--human-readable",
                "--no-owner",
                "--no-group",
                "--no-perms",
                "-e",
                _ssh_e(ssh_key, "22"),
                str(local_path) + "/",
                f"{proxy}:{workdir}/mavaia",
            ]
            + common_excludes
            + rsync_info
        )
        subprocess.run(rsync_cmd, check=True)
        return

    rsync_cmd = (
        [
            "rsync",
            "-az",
            "--human-readable",
            "--no-owner",
            "--no-group",
            "--no-perms",
            "-e",
            _ssh_e(ssh_key, str(pod_port)),
            str(local_path) + "/",
            f"root@{pod_ip}:{workdir}/mavaia",
        ]
        + common_excludes
        + rsync_info
    )
    try:
        proc = subprocess.run(rsync_cmd, check=False)
        if proc.returncode != 0 and proc.returncode != 23:
            # 23 means partial transfer (often harmless for locked local files)
            raise subprocess.CalledProcessError(proc.returncode, rsync_cmd)
        elif proc.returncode == 23:
            _rich_log(
                "Rsync completed with status 23 (partial transfer). Safe to proceed.", "dim", "ℹ"
            )

    except subprocess.CalledProcessError:
        if pod_id:
            _rich_log(
                "Direct rsync failed; retrying via proxy.",
                "yellow",
                "⚠",
                progress=progress,
                task_id=task_id,
            )
            # Find the index of the SSH command (-e flag value)
            for idx, item in enumerate(rsync_cmd):
                if item == "-e":
                    rsync_cmd[idx + 1] = _ssh_e(ssh_key, "22")
                    break
            rsync_cmd[-1] = f"{pod_id}-22@ssh.runpod.io:{workdir}/mavaia"
            proc = subprocess.run(rsync_cmd, check=False)
            if proc.returncode != 0 and proc.returncode != 23:
                raise subprocess.CalledProcessError(proc.returncode, rsync_cmd)
            elif proc.returncode == 23:
                _rich_log(
                    "Rsync completed with status 23 (partial transfer) via proxy. Safe to proceed.",
                    "dim",
                    "ℹ",
                    progress=progress,
                    task_id=task_id,
                )


def sync_models_to_pod(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    local_path: Path,
    workdir: str,
    pod_id: str = None,
    proxy: str = None,
    progress=None,
    task_id=None,
):
    _rich_log("Syncing model weights to pod...", "cyan", "📤", progress=progress, task_id=task_id)

    src_dir = local_path / "mavaia_core" / "models" / "neural_text_generator"
    if not src_dir.exists():
        _rich_log(
            "No local models found to sync.", "yellow", "⚠", progress=progress, task_id=task_id
        )
        return

    if proxy:
        rsync_cmd = [
            "rsync",
            "-az",
            "--info=stats2",
            "--no-owner",
            "--no-group",
            "-e",
            _ssh_e(ssh_key, "22"),
            str(src_dir) + "/",
            f"{proxy}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
        ]
        subprocess.run(rsync_cmd, check=True)
        return

    rsync_cmd = [
        "rsync",
        "-az",
        "--info=stats2",
        "--no-owner",
        "--no-group",
        "-e",
        _ssh_e(ssh_key, str(pod_port)),
        str(src_dir) + "/",
        f"root@{pod_ip}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
    ]
    try:
        proc = subprocess.run(rsync_cmd, check=False)
        if proc.returncode not in (0, 23):
            raise subprocess.CalledProcessError(proc.returncode, rsync_cmd)
    except subprocess.CalledProcessError:
        if pod_id:
            _rich_log(
                "Direct rsync failed; retrying via proxy.",
                "yellow",
                "⚠",
                progress=progress,
                task_id=task_id,
            )
            rsync_cmd[4] = _ssh_e(ssh_key, "22")
            rsync_cmd[5] = (
                f"{pod_id}-22@ssh.runpod.io:{workdir}/mavaia/mavaia_core/models/neural_text_generator/"
            )
            proc = subprocess.run(rsync_cmd, check=False)
            if proc.returncode not in (0, 23):
                raise subprocess.CalledProcessError(proc.returncode, rsync_cmd)


def summarize_results(local_path: Path):
    """Improved result parsing using the LiveBenchResultParser."""
    if LiveBenchResultParser:
        _rich_log(f"Analyzing benchmark data in {local_path}...", "cyan", "🔍")
        LiveBenchResultParser.parse_all(local_path)
        return

    # Fallback to legacy lightweight summary if parser not available
    results_path = None

    # Find latest livebench_results_*.json
    candidates = list(local_path.glob("livebench_results_*.json"))
    if not candidates:
        _rich_log("No benchmark results found to summarize.", "yellow", "⚠")
        return

    results_path = max(candidates, key=lambda p: p.stat().st_mtime)
    _rich_log(f"Analyzing results from: {results_path.name}", "cyan", "🔍")

    try:
        data = json.loads(results_path.read_text())
        results = data.get("results", [])

        from collections import defaultdict

        totals = defaultdict(int)
        passed = defaultdict(int)
        for item in results:
            rd = item.get("result_data") or {}
            cat = rd.get("livebench_category") or item.get("category")
            if not cat:
                continue
            totals[cat] += 1
            if item.get("status") == "passed":
                passed[cat] += 1

        category_rates = {cat: passed[cat] / totals[cat] for cat in totals if totals[cat]}

        # Ensure ALL standard categories are shown even if not in results
        all_categories = [
            "reasoning",
            "coding",
            "math",
            "knowledge",
            "language",
            "instruction_following",
        ]
        for cat in all_categories:
            if cat not in category_rates:
                category_rates[cat] = 0.0

        gaps = [cat for cat, rate in category_rates.items() if rate < 0.5]

        # Recommendations mapping
        recs = {
            "reasoning": ("Stage 4: Capability", ["kitsdk/hotpot_qa"]),
            "coding": (
                "Stage 7: Coding",
                [
                    "iamtarun/python_code_instructions_18k_alpaca",
                    "m-a-p/CodeFeedback-Filtered-Instruction",
                ],
            ),
            "math": ("Stage 2: Logic", ["microsoft/orca-math-word-problems-200k"]),
            "knowledge": ("Stage 6: Knowledge", ["kitsdk/wiki_hop"]),
            "context": ("Stage 5: Context", ["kmfoda/booksum"]),
            "alignment": ("Stage 8: Alignment", ["Intel/orca_dpo_pairs"]),
        }

        print("\n" + "=" * 60)
        print("📊 MAVAIA COGNITIVE PERFORMANCE SUMMARY")
        print("=" * 60)

        for cat in sorted(category_rates.keys()):
            rate = category_rates[cat]
            # Use totals if available, otherwise 0
            count = totals.get(cat, 0)
            status = "[PASS]" if rate >= 0.5 else "[GAP]"
            print(f"{cat.capitalize():<25} {rate:>6.1%} {status} ({count} tests)")

        if gaps:
            print("\n💡 RECOMMENDED RETOUCH STAGES:")
            for gap in sorted(gaps):
                gap_lower = gap.lower()
                if gap_lower in recs:
                    stage, datasets = recs[gap_lower]
                    print(f"  • {stage}: Use {', '.join(datasets)}")
        else:
            print("\n✨ No critical gaps detected! Foundation is solid.")
        print("=" * 60 + "\n")

    except Exception as e:
        _rich_log(f"Failed to summarize results: {e}", "red", "✗")


def remote_train(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    train_args: List[str],
    workdir: str,
    pod_id: str = None,
    proxy: str = None,
    script_rel: str = "scripts/train_neural_text_generator.py",
    progress=None,
    task_id=None,
):
    _rich_log(
        "Starting training on remote pod...", "bold green", "🏋", progress=progress, task_id=task_id
    )
    if train_args and train_args[0] == "--":
        train_args = train_args[1:]
    args_str = " ".join(train_args)
    env_prefix = "PYTHONUNBUFFERED=1 "
    if "--plain-output" in train_args:
        env_prefix += "MAVAIA_PLAIN_OUTPUT=1 "
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        env_prefix += f"HF_TOKEN='{hf_token}' "
    
    if "run_tests.py" in script_rel or "train" in script_rel:
        env_prefix += "MAVAIA_ENABLE_HEAVY_MODULES=true "

    if proxy:
        ssh_cmd = _ssh_base(ssh_key, "22", proxy) + [
            f"cd {workdir}/mavaia && PYTHON_EXE=$(if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi); {env_prefix}$PYTHON_EXE {script_rel} {args_str}"
        ]
        subprocess.run(ssh_cmd, check=True)
        return

    ssh_cmd = _ssh_base(ssh_key, str(pod_port), f"root@{pod_ip}") + [
        f"cd {workdir}/mavaia && PYTHON_EXE=$(if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi); {env_prefix}$PYTHON_EXE {script_rel} {args_str}"
    ]
    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError as e:
        if pod_id and e.returncode == 255:
            _rich_log(
                "Direct SSH failed (255); retrying via proxy.",
                "yellow",
                "⚠",
                progress=progress,
                task_id=task_id,
            )
            ssh_cmd = _ssh_base(ssh_key, "22", f"{pod_id}-22@ssh.runpod.io") + [
                f"cd {workdir}/mavaia && PYTHON_EXE=$(if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi); {env_prefix}$PYTHON_EXE {script_rel} {args_str}"
            ]
            subprocess.run(ssh_cmd, check=True)
        else:
            raise e


def check_model_health(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    workdir: str,
    pod_id: str = None,
    proxy: str = None,
    progress=None,
    task_id=None,
):
    """Verifies if the Neural Text Generator can actually load and run on the pod."""
    _rich_log("Performing Model Health Check on pod...", "cyan", "🩺", progress=progress, task_id=task_id)
    
    health_script = f"""
import os
import sys

# Force heavy modules for the health check
os.environ['MAVAIA_ENABLE_HEAVY_MODULES'] = 'true'
os.environ['MAVAIA_STRICT_INIT'] = 'true'

try:
    print("[HEALTH] Checking torch and CUDA...")
    import torch
    print(f"[HEALTH] Torch version: {{torch.__version__}}")
    print(f"[HEALTH] CUDA available: {{torch.cuda.is_available()}}")
    if torch.cuda.is_available():
        print(f"[HEALTH] GPU: {{torch.cuda.get_device_name(0)}}")
    
    print("[HEALTH] Initializing ModuleRegistry...")
    from mavaia_core.brain.registry import ModuleRegistry
    ModuleRegistry.discover_modules(verbose=False)
    
    print("[HEALTH] Retrieving cognitive_generator...")
    cg = ModuleRegistry.get_module("cognitive_generator")
    if not cg:
        print("[HEALTH] ERROR: Could not find 'cognitive_generator' in registry.")
        sys.exit(1)
        
    cg.initialize()
    
    print("[HEALTH] Attempting tiny generation...")
    res = cg.execute(
        operation="generate_response",
        params={{
            "input": "Hello",
            "max_tokens": 5
        }}
    )
    
    print(f"[HEALTH] Result text: '{{res.get('text', '')}}'")
    
    # Check if we got the 'analyzing' placeholder
    if "analyzing your request" in res.get('text', '').lower():
        print("[HEALTH] WARNING: Received placeholder response instead of model inference.")
        sys.exit(2)
        
    print("[HEALTH] SUCCESS: Model is active and responding.")
    sys.exit(0)
except Exception as e:
    print(f"[HEALTH] ERROR: {{str(e)}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
    
    remote_cmd = (
        f"cd {workdir}/mavaia && "
        f"PYTHON_EXE=$(if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi); "
        f"cat << 'EOF' > model_health_check.py\n{health_script}\nEOF\n"
        f"PYTHONPATH=. $PYTHON_EXE model_health_check.py"
    )

    try:
        if proxy:
            ssh_cmd = _ssh_base(ssh_key, "22", proxy) + [remote_cmd]
        else:
            ssh_cmd = _ssh_base(ssh_key, str(pod_port), f"root@{pod_ip}") + [remote_cmd]
            
        result = subprocess.run(ssh_cmd, check=True, capture_output=True, text=True)
        _rich_log("Model Health Check passed!", "bold green", "✓", progress=progress, task_id=task_id)
        return True
    except subprocess.CalledProcessError as e:
        _rich_log("Model Health Check FAILED!", "bold red", "✗", progress=progress, task_id=task_id)
        print(e.stdout)
        print(e.stderr)
        
        if e.returncode == 2:
            _rich_log("Detailed Diagnosis: Model loaded but returned a placeholder. This usually means weights are missing or incompatible.", "yellow", "🔍")
        return False


def remote_benchmark(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    bench_args: List[str],
    workdir: str,
    pod_id: str = None,
    proxy: str = None,
    script_rel: str = "LiveBench/livebench/run_livebench.py",
    progress=None,
    task_id=None,
):
    _rich_log(
        "Starting benchmark on remote pod...",
        "bold green",
        "📊",
        progress=progress,
        task_id=task_id,
    )
    if bench_args and bench_args[0] == "--":
        bench_args = bench_args[1:]

    # Extract model path to pass to API server
    model_path = None
    for i, arg in enumerate(bench_args):
        if arg == "--model":
            model_path = bench_args[i + 1]
            break

    args_str = " ".join(f"'{a}'" if " " in a else a for a in bench_args)
    env_prefix = "PYTHONUNBUFFERED=1 MAVAIA_ENABLE_HEAVY_MODULES=true "
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        env_prefix += f"HF_TOKEN='{hf_token}' "

    if model_path:
        env_prefix += f"MAVAIA_MODEL_PATH='{model_path}' "

    log_path = f"{workdir}/mavaia/server.log"

    # Build a robust single script to run on the pod
    remote_script = f"""
set -e
PYTHON_EXE=$(if [ -f {workdir}/mavaia/.venv/bin/python ]; then echo {workdir}/mavaia/.venv/bin/python; else echo python3; fi)
echo "[DEBUG] Using Python: $PYTHON_EXE"

cd {workdir}/mavaia
echo "[DEBUG] Starting API server..."
{env_prefix} PYTHONPATH=. nohup $PYTHON_EXE -m mavaia_core.api.server --host 127.0.0.1 --port 8000 --no-auto-port > {log_path} 2>&1 &
SERVER_PID=$!

echo "Waiting for API server to start on 127.0.0.1:8000..."
READY=0
for i in $(seq 1 60); do
    if curl -s http://127.0.0.1:8000/v1/models > /dev/null; then
        echo "Server ready and models loaded!"
        READY=1
        break
    fi
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "Server died! Tail of {log_path}:"
        tail -n 20 {log_path}
        exit 1
    fi
    sleep 2
done

if [ $READY -eq 0 ]; then
    echo "Timeout waiting for server. Tail of {log_path}:"
    tail -n 20 {log_path}
    kill $SERVER_PID || true
    exit 1
fi

cd {workdir}/mavaia/LiveBench/livebench
echo "[DEBUG] Cleaning old benchmark data..."
# Archive existing results instead of deleting them to avoid data loss on partial runs
rm -rf data_old/
if [ -d data/ ]; then mv data/ data_old/; fi
rm -f mavaia_result.json livebench_results_*.json

if [ ! -f run_livebench.py ]; then
    echo "ERROR: run_livebench.py not found in $(pwd)"
    ls -F
    kill $SERVER_PID || true
    exit 1
fi

echo "[DEBUG] Starting LiveBench evaluation..."
echo "Executing: $PYTHON_EXE run_livebench.py {args_str}"
{env_prefix} $PYTHON_EXE run_livebench.py {args_str}

echo "Benchmark complete. Cleaning up..."
kill $SERVER_PID || true
"""

    if proxy:
        ssh_cmd = _ssh_base(ssh_key, "22", proxy) + [remote_script]
        subprocess.run(ssh_cmd, check=True)
        return

    ssh_cmd = _ssh_base(ssh_key, str(pod_port), f"root@{pod_ip}") + [remote_script]
    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError as e:
        if pod_id and e.returncode == 255:
            _rich_log(
                "Direct SSH failed (255); retrying via proxy.",
                "yellow",
                "⚠",
                progress=progress,
                task_id=task_id,
            )
            ssh_cmd = _ssh_base(ssh_key, "22", f"{pod_id}-22@ssh.runpod.io") + [remote_script]
            subprocess.run(ssh_cmd, check=True)
        else:
            raise e


def get_artifacts(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    local_path: Path,
    workdir: str,
    pod_id: str = None,
    proxy: str = None,
    progress=None,
    task_id=None,
):
    _rich_log(
        "Pulling trained models from pod...", "cyan", "📥", progress=progress, task_id=task_id
    )

    dest_dir = local_path / "models" / "neural_text_generator_remote"
    dest_dir.mkdir(parents=True, exist_ok=True)

    if proxy:
        scp_cmd = [
            "rsync",
            "-az",
            "--info=stats2",
            "--no-owner",
            "--no-group",
            "-e",
            _ssh_e(ssh_key, "22"),
            f"{proxy}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
            str(dest_dir) + "/",
        ]
        subprocess.run(scp_cmd, check=True)
        return

    scp_cmd = [
        "rsync",
        "-az",
        "--info=stats2",
        "--no-owner",
        "--no-group",
        "-e",
        _ssh_e(ssh_key, str(pod_port)),
        f"root@{pod_ip}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
        str(dest_dir) + "/",
    ]
    try:
        proc = subprocess.run(scp_cmd, check=False)
        if proc.returncode != 0 and proc.returncode != 23:
            raise subprocess.CalledProcessError(proc.returncode, scp_cmd)
        elif proc.returncode == 23:
            _rich_log(
                "Rsync completed with status 23 (partial transfer). Safe to proceed.", "dim", "ℹ"
            )
    except subprocess.CalledProcessError:
        if pod_id:
            _rich_log(
                "Direct rsync failed; retrying via proxy.",
                "yellow",
                "⚠",
                progress=progress,
                task_id=task_id,
            )
            scp_cmd[4] = _ssh_e(ssh_key, "22")
            scp_cmd[5] = (
                f"{pod_id}-22@ssh.runpod.io:{workdir}/mavaia/mavaia_core/models/neural_text_generator/"
            )
            proc = subprocess.run(scp_cmd, check=False)
            if proc.returncode != 0 and proc.returncode != 23:
                raise subprocess.CalledProcessError(proc.returncode, scp_cmd)
            elif proc.returncode == 23:
                _rich_log(
                    "Rsync completed with status 23 (partial transfer) via proxy. Safe to proceed.",
                    "dim",
                    "ℹ",
                    progress=progress,
                    task_id=task_id,
                )


def get_bench_results(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    local_path: Path,
    workdir: str,
    pod_id: str = None,
    proxy: str = None,
    progress=None,
    task_id=None,
):
    _rich_log(
        "Pulling benchmark results from pod...", "cyan", "📥", progress=progress, task_id=task_id
    )

    remote_base = f"{workdir}/mavaia/LiveBench/livebench"
    
    def run_sync(host_str, port_str):
        ssh_cmd = _ssh_e(ssh_key, port_str)
        # 1. Pull root level JSON results
        sync_root_cmd = [
            "rsync", "-az", "--info=stats2", "--no-owner", "--no-group",
            "-e", ssh_cmd,
            "--include=livebench_results_*.json",
            "--include=mavaia_result.json",
            "--exclude=*",
            f"{host_str}:{remote_base}/",
            str(local_path) + "/",
        ]
        # 2. Pull the entire data directory
        sync_data_cmd = [
            "rsync", "-az", "--info=stats2", "--no-owner", "--no-group",
            "-e", ssh_cmd,
            f"{host_str}:{remote_base}/data/",
            str(local_path / "data") + "/",
        ]
        subprocess.run(sync_root_cmd, check=True)
        subprocess.run(sync_data_cmd, check=True)

    try:
        remote_host = proxy if proxy else f"root@{pod_ip}"
        remote_port = "22" if proxy else str(pod_port)
        run_sync(remote_host, remote_port)
    except Exception as e:
        if pod_id and not proxy:
            _rich_log("Direct rsync failed; retrying via proxy.", "yellow", "⚠", progress=progress, task_id=task_id)
            try:
                run_sync(f"{pod_id}-22@ssh.runpod.io", "22")
            except Exception as retry_e:
                _rich_log(f"Proxy rsync also failed: {retry_e}", "red", "✗", progress=progress, task_id=task_id)
        else:
            _rich_log(f"Result sync failed: {e}", "red", "✗", progress=progress, task_id=task_id)


def get_internal_bench_results(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    local_path: Path,
    workdir: str,
    pod_id: str = None,
    proxy: str = None,
    progress=None,
    task_id=None,
):
    _rich_log(
        "Pulling internal benchmark results from pod...",
        "cyan",
        "📥",
        progress=progress,
        task_id=task_id,
    )

    dest_dir = local_path / "mavaia_core" / "evaluation" / "results"
    dest_dir.mkdir(parents=True, exist_ok=True)

    def run_sync(host_str, port_str):
        ssh_cmd = _ssh_e(ssh_key, port_str)
        sync_cmd = [
            "rsync",
            "-az",
            "--info=stats2",
            "--no-owner",
            "--no-group",
            "-e",
            ssh_cmd,
            # Pull the entire results directory content accurately
            f"{host_str}:{workdir}/mavaia/mavaia_core/evaluation/results/",
            str(dest_dir) + "/",
        ]
        # Also specifically ensure any root level report HTMLs are caught if they are outside
        sync_html_cmd = [
            "rsync",
            "-az",
            "--include=report_*.html",
            "--exclude=*",
            "-e",
            ssh_cmd,
            f"{host_str}:{workdir}/mavaia/mavaia_core/evaluation/results/",
            str(dest_dir) + "/",
        ]
        subprocess.run(sync_cmd, check=True)
        subprocess.run(sync_html_cmd, check=False) # Fallback, don't crash if no extra HTMLs

    try:
        remote_host = proxy if proxy else f"root@{pod_ip}"
        remote_port = "22" if proxy else str(pod_port)
        run_sync(remote_host, remote_port)
    except Exception as e:
        if pod_id and not proxy:
            _rich_log(
                "Direct rsync failed; retrying via proxy.",
                "yellow",
                "⚠",
                progress=progress,
                task_id=task_id,
            )
            try:
                run_sync(f"{pod_id}-22@ssh.runpod.io", "22")
            except Exception as retry_e:
                _rich_log(
                    f"Proxy rsync also failed: {retry_e}",
                    "red",
                    "✗",
                    progress=progress,
                    task_id=task_id,
                )
        else:
            _rich_log(f"Result sync failed: {e}", "red", "✗", progress=progress, task_id=task_id)


def sync_training_data(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    local_path: Path,
    workdir: str,
    pod_id: str = None,
    proxy: str = None,
    progress=None,
    task_id=None,
):
    _rich_log(
        "Syncing training data (runs, checkpoints, cache) from pod...",
        "cyan",
        "📥",
        progress=progress,
        task_id=task_id,
    )

    dest_dir = local_path / "models" / "neural_text_generator_remote" / "training_data"
    dest_dir.mkdir(parents=True, exist_ok=True)

    if proxy:
        rsync_cmd = [
            "rsync",
            "-az",
            "--info=stats2",
            "--no-owner",
            "--no-group",
            "-e",
            _ssh_e(ssh_key, "22"),
            f"{proxy}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
            str(dest_dir / "models") + "/",
        ]
        cache_cmd = [
            "rsync",
            "-az",
            "--info=stats2",
            "--no-owner",
            "--no-group",
            "-e",
            _ssh_e(ssh_key, "22"),
            f"{proxy}:{workdir}/mavaia/mavaia_core/data/",
            str(dest_dir / "data_cache") + "/",
        ]
        for cmd in (rsync_cmd, cache_cmd):
            proc = subprocess.run(cmd, check=False)
            if proc.returncode not in (0, 23):
                raise subprocess.CalledProcessError(proc.returncode, cmd)
            if proc.returncode == 23:
                _rich_log(
                    "Rsync completed with status 23 (partial transfer). Safe to proceed.",
                    "dim",
                    "ℹ",
                )
        return

    rsync_cmd = [
        "rsync",
        "-az",
        "--info=stats2",
        "--no-owner",
        "--no-group",
        "-e",
        _ssh_e(ssh_key, str(pod_port)),
        f"root@{pod_ip}:{workdir}/mavaia/mavaia_core/models/neural_text_generator/",
        str(dest_dir / "models") + "/",
    ]
    cache_cmd = [
        "rsync",
        "-az",
        "--info=stats2",
        "--no-owner",
        "--no-group",
        "-e",
        _ssh_e(ssh_key, str(pod_port)),
        f"root@{pod_ip}:{workdir}/mavaia/mavaia_core/data/",
        str(dest_dir / "data_cache") + "/",
    ]
    try:
        for cmd in (rsync_cmd, cache_cmd):
            proc = subprocess.run(cmd, check=False)
            if proc.returncode not in (0, 23):
                raise subprocess.CalledProcessError(proc.returncode, cmd)
            if proc.returncode == 23:
                _rich_log(
                    "Rsync completed with status 23 (partial transfer). Safe to proceed.",
                    "dim",
                    "ℹ",
                )
    except subprocess.CalledProcessError:
        if pod_id:
            _rich_log(
                "Direct rsync failed; retrying via proxy.",
                "yellow",
                "⚠",
                progress=progress,
                task_id=task_id,
            )
            rsync_cmd[4] = _ssh_e(ssh_key, "22")
            rsync_cmd[5] = (
                f"{pod_id}-22@ssh.runpod.io:{workdir}/mavaia/mavaia_core/models/neural_text_generator/"
            )
            cache_cmd[4] = _ssh_e(ssh_key, "22")
            cache_cmd[5] = f"{pod_id}-22@ssh.runpod.io:{workdir}/mavaia/mavaia_core/data/"
            for cmd in (rsync_cmd, cache_cmd):
                proc = subprocess.run(cmd, check=False)
                if proc.returncode not in (0, 23):
                    raise subprocess.CalledProcessError(proc.returncode, cmd)
                if proc.returncode == 23:
                    _rich_log(
                        "Rsync completed with status 23 (partial transfer) via proxy. Safe to proceed.",
                        "dim",
                        "ℹ",
                    )


def _select_candidate_gpus(
    bridge: RunPodBridge, min_price: float, max_price: float, min_vram: int
) -> List[Dict]:
    gpu_types = bridge.get_gpu_types_with_availability()
    if not gpu_types:
        return []
    # Estimate storage cost (~$0.01 per 10GB per hour as a rough safe buffer)
    storage_overhead = 0.20  # 200GB vol + 200GB disk

    # BLACKWELL EXCLUSION: These cards require sm_120 kernels not present in our stable image
    incompatible_keywords = ["Blackwell", "PRO 4500", "PRO 5000"]

    filtered_gpus = [
        g
        for g in gpu_types
        if bridge.gpu_is_available(g)
        if g.get("securePrice") is not None
        and (g["securePrice"] + storage_overhead) >= min_price
        and (g["securePrice"] + storage_overhead) <= max_price
        and g.get("memoryInGb") is not None
        and g.get("memoryInGb") >= min_vram
        and not any(kw in g.get("displayName", "") for kw in incompatible_keywords)
    ]

    # BALANCED HEADROOM SCORING: Prioritize high-VRAM low-cost options
    def _score(gpu):
        price = gpu["securePrice"] + storage_overhead
        vram = gpu["memoryInGb"]
        # VRAM per dollar - simple but effective for balancing headroom and cost
        return vram / price

    filtered_gpus.sort(key=_score, reverse=True)
    return filtered_gpus


def _fleet_role_specs(args) -> List[Dict[str, Any]]:
    base_mount = "/workspace"

    # Base args shared by all fleet roles
    extra_train_args = []
    if args.batch_size:
        extra_train_args.extend(["--batch-size", str(args.batch_size)])
    if args.gradient_checkpointing:
        extra_train_args.append("--gradient-checkpointing")

    # Modern curriculum-aligned fleet specs
    return [
        {
            "name": "mavaia_distill",
            "role": "distill",
            "workdir": f"{base_mount}/distill",
            "script": "scripts/train_neural_text_generator.py",
            "train_args": [
                "--epochs",
                "10",
                "--model-type",
                "transformer",
                "--distill",
                "--teacher-model",
                args.teacher_model,
                "--distill-alpha",
                str(args.distill_alpha),
                "--distill-temp",
                str(args.distill_temp),
                "--distill-topk",
                str(args.distill_topk),
                "--stop-at-loss",
                str(args.stop_at_loss or 0.05),
                "--min-improvement",
                str(args.min_improvement or 0.01),
            ]
            + extra_train_args,
        },
        {
            "name": "mavaia_logic",
            "role": "logic",
            "workdir": f"{base_mount}/logic",
            "script": "scripts/train_neural_text_generator.py",
            "train_args": [
                "--source",
                "huggingface",
                "--book-ids",
                "microsoft/orca-math-word-problems-200k",
                "--epochs",
                "1",
                "--data-percentage",
                "0.1",
                "--model-type",
                "transformer",
                "--stop-at-loss",
                str(args.stop_at_loss or 0.05),
                "--min-improvement",
                str(args.min_improvement or 0.01),
            ]
            + extra_train_args,
        },
        {
            "name": "mavaia_tone",
            "role": "tone",
            "workdir": f"{base_mount}/tone",
            "script": "scripts/train_neural_text_generator.py",
            "train_args": [
                "--source",
                "huggingface",
                "--book-ids",
                "mlfoundations-dev/oh-dcft-v3.1-gemini-1.5-pro",
                "--epochs",
                "1",
                "--data-percentage",
                "0.2",
                "--model-type",
                "transformer",
                "--stop-at-loss",
                str(args.stop_at_loss or 0.05),
                "--min-improvement",
                str(args.min_improvement or 0.01),
            ]
            + extra_train_args,
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
_FLEET_PROGRESS = None


def _fleet_worker(bridge: RunPodBridge, args, role: Dict[str, Any], stop_event: threading.Event):
    global _FLEET_PROGRESS
    pod_id = None
    retry_sleep = 30
    min_price = float(args.min_price)
    max_price = float(args.max_price)

    # Add a progress task for this worker if fleet progress is active
    task_id = None
    if _FLEET_PROGRESS:
        task_id = _FLEET_PROGRESS.add_task(
            description=f"[{role['role']}] Initializing...", total=None
        )

    # Stagger workers slightly to reduce contention.
    time.sleep({"distill": 0, "normal": 5, "auditor": 10}.get(role["role"], 0))
    while not stop_event.is_set():
        if _BALANCE_LOW.is_set():
            _rich_log(
                f"Balance below ${args.min_balance:.2f}. Fleet paused.",
                "yellow",
                "⚠",
                progress=_FLEET_PROGRESS,
                task_id=task_id,
            )
            time.sleep(min(60, retry_sleep))
            retry_sleep = min(retry_sleep * 2, 300)
            continue
        # Check existing pod
        if pod_id:
            pods = bridge.get_pods()
            pod = next((p for p in pods if p["id"] == pod_id), None)
            if not pod or not pod.get("runtime"):
                _rich_log(
                    f"Pod {pod_id} for role {role['role']} missing; restarting.",
                    "yellow",
                    "⚠",
                    progress=_FLEET_PROGRESS,
                    task_id=task_id,
                )
                pod_id = None
            else:
                time.sleep(30)
                continue

        candidates = _select_candidate_gpus(bridge, min_price, max_price, args.min_vram)
        if not candidates:
            _rich_log(
                f"No available GPUs for role {role['role']}. Retrying in {retry_sleep}s...",
                "dim",
                "ℹ",
                progress=_FLEET_PROGRESS,
                task_id=task_id,
            )
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
            _rich_log(
                f"All candidate GPUs are in-flight. Retrying in {retry_sleep}s...",
                "dim",
                "ℹ",
                progress=_FLEET_PROGRESS,
                task_id=task_id,
            )
            time.sleep(retry_sleep)
            retry_sleep = min(retry_sleep * 2, 300)
            continue

        candidate_id = candidate.get("id")
        candidate_display = candidate.get("displayName", candidate_id)
        current_image = args.image
        if "AMD" in candidate_display or "MI" in candidate_display:
            current_image = "runpod/pytorch:2.1.0-py3.10-rocm5.7-devel-ubuntu22.04"
        pod_name = role["name"]
        _rich_log(
            f"[{role['role']}] Looking for GPU with {candidate_display}...",
            "cyan",
            "🔍",
            progress=_FLEET_PROGRESS,
            task_id=task_id,
        )
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
            _rich_log(
                f"Failed to create pod for role {role['role']}.",
                "red",
                "✗",
                progress=_FLEET_PROGRESS,
                task_id=task_id,
            )
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
        _rich_log(
            f"Pod {pod_id} launched for role {role['role']}! Waiting for runtime...",
            "cyan",
            "🚀",
            progress=_FLEET_PROGRESS,
            task_id=task_id,
        )
        while True:
            pods = bridge.get_pods()
            pod = next((p for p in pods if p["id"] == pod_id), None)
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
        setup_pod_env(
            pod_ip,
            pod_port,
            args.ssh_key,
            pod_id,
            proxy,
            progress=_FLEET_PROGRESS,
            task_id=task_id,
            bridge=bridge,
        )
        sync_code(
            pod_ip,
            pod_port,
            args.ssh_key,
            REPO_ROOT,
            role["workdir"],
            pod_id,
            proxy,
            progress=_FLEET_PROGRESS,
            task_id=task_id,
        )
        ensure_mavaia_installed(
            pod_ip,
            pod_port,
            args.ssh_key,
            role["workdir"],
            pod_id,
            proxy,
            s3_bucket=args.s3_bucket if args.use_s3 else None,
            s3_prefix=args.s3_prefix if args.use_s3 else None,
            s3_region=args.s3_region if args.use_s3 else None,
            s3_endpoint=args.s3_endpoint if args.use_s3 else None,
            force_reinstall=args.force_refresh,
            pip_debug=args.pip_debug,
            pip_stream=args.pip_stream,
            editable_install=args.editable_install,
            progress=_FLEET_PROGRESS,
            task_id=task_id,
        )

        if role["role"] == "distill" and not args.no_ollama:
            setup_ollama(
                pod_ip,
                pod_port,
                args.ssh_key,
                args.teacher_model,
                args.ollama_model_dir,
                pod_id,
                proxy,
                progress=_FLEET_PROGRESS,
                task_id=task_id,
            )

        if role["role"] == "auditor":
            _run_ssh(
                args.ssh_key,
                pod_ip,
                pod_port,
                pod_id,
                proxy,
                _fleet_auditor_cmd(role["workdir"]),
                progress=_FLEET_PROGRESS,
                task_id=task_id,
            )
        else:
            train_args = list(role["train_args"])
            script_rel = role.get("script", "scripts/train_neural_text_generator.py")
            if (
                script_rel.endswith("train_neural_text_generator.py")
                and "--plain-output" not in train_args
            ):
                train_args.append("--plain-output")

            # NOTE: For training, we might want to exit progress display to see logs,
            # but for now we'll stay in it until training starts.
            _rich_log(
                f"Role {role['role']} training starting...",
                "bold green",
                "🏋",
                progress=_FLEET_PROGRESS,
                task_id=task_id,
            )
            remote_train(
                pod_ip,
                pod_port,
                args.ssh_key,
                train_args,
                role["workdir"],
                pod_id,
                proxy,
                script_rel=script_rel,
            )

        # Best-effort termination to avoid leaks; restart loop will acquire a new pod if needed.
        try:
            bridge.terminate_pod(pod_id)
        except Exception:
            pass

        # If training ends, loop to restart
        _rich_log(
            f"Role {role['role']} completed or failed; restarting search.",
            "yellow",
            "🔄",
            progress=_FLEET_PROGRESS,
            task_id=task_id,
        )
        pod_id = None


def remote_snapshot(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    workdir: str,
    pod_id: str = None,
    proxy: str = None,
    progress=None,
    task_id=None,
):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    snapshot_cmd = (
        "set -e; "
        f"cd {workdir}/mavaia; "
        f"SNAP_DIR={workdir}/mavaia/mavaia_core/models/neural_text_generator/snapshots/{{ts}}; "
        'mkdir -p "$SNAP_DIR"; '
        'cp -a mavaia_core/models/neural_text_generator/checkpoints "$SNAP_DIR" 2>/dev/null || true; '
        'cp -a mavaia_core/models/neural_text_generator/runs "$SNAP_DIR" 2>/dev/null || true; '
        'cp -a mavaia_core/models/neural_text_generator/latest_run.txt "$SNAP_DIR" 2>/dev/null || true; '
        'cp -a mavaia_core/models/neural_text_generator/*.keras "$SNAP_DIR" 2>/dev/null || true; '
        'cp -a mavaia_core/models/neural_text_generator/*.json "$SNAP_DIR" 2>/dev/null || true; '
        'echo "snapshot_saved"'
    ).format(ts=timestamp)

    if proxy:
        ssh_cmd = _ssh_base(ssh_key, "22", proxy) + [snapshot_cmd]
        subprocess.run(ssh_cmd, check=True)
        return

    ssh_cmd = _ssh_base(ssh_key, str(pod_port), f"root@{pod_ip}") + [snapshot_cmd]
    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError:
        if pod_id:
            _rich_log(
                "Direct SSH failed (255); retrying via proxy.",
                "yellow",
                "⚠",
                progress=progress,
                task_id=task_id,
            )
            # Swap to RunPod SSH proxy (update port + host entries)
            ssh_cmd = _ssh_base(ssh_key, "22", f"{pod_id}-22@ssh.runpod.io") + [snapshot_cmd]
            subprocess.run(ssh_cmd, check=True)
        else:
            raise


def main():
    parser = argparse.ArgumentParser(description="Mavaia RunPod Training Bridge")
    parser.add_argument("--pod-id", help="Existing pod ID to use")
    parser.add_argument("--gpu", default="NVIDIA RTX A6000", help="GPU type for new pod")
    parser.add_argument(
        "--image",
        default="runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04",
        help="Container image",
    )
    parser.add_argument("--template", help="RunPod Template ID (overrides --image if provided)")
    parser.add_argument(
        "--ssh-key",
        default=str(Path.home() / ".ssh" / "mavaia_key"),
        help="Path to your local private SSH key",
    )
    parser.add_argument(
        "--ssh-key-value", help="Public SSH key content (or name) to inject into the pod"
    )
    parser.add_argument(
        "--ssh-proxy", help="Full SSH proxy host (e.g. 68aeykzanq67mn-64411855@ssh.runpod.io)"
    )
    parser.add_argument(
        "--fleet", action="store_true", help="Enable parallel fleet mode (3 pods max)"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-manage: terminate active pods, pick best GPU under $0.50/hr, and train",
    )
    parser.add_argument(
        "--max-price", type=float, default=1.50, help="Max hourly price for auto GPU selection"
    )
    parser.add_argument(
        "--min-price", type=float, default=0.50, help="Min hourly price for auto GPU selection"
    )
    parser.add_argument(
        "--auto-price-range",
        type=str,
        default="0.50-1.50",
        help="Auto price range min-max (overrides min/max if set)",
    )
    parser.add_argument(
        "--auto-price-step", type=float, default=0.05, help="Step size for auto price range scan"
    )
    parser.add_argument(
        "--min-vram", type=int, default=24, help="Minimum VRAM (GB) for GPU selection"
    )
    parser.add_argument(
        "--min-balance", type=float, default=5.0, help="Minimum balance required to run (USD)"
    )
    parser.add_argument(
        "--balance-watchdog-seconds", type=int, default=60, help="Balance check interval (seconds)"
    )
    parser.add_argument("--terminate", action="store_true", help="Terminate pod after training")
    parser.add_argument(
        "--no-auto-report", action="store_true", help="Disable the post-benchmark summary report"
    )
    parser.add_argument("--dry-run", action="store_true", help="Just print commands")
    parser.add_argument(
        "--watchdog-minutes",
        type=float,
        default=10.0,
        help="Watchdog interval (minutes) to snapshot/sync during training (0 disables)",
    )
    parser.add_argument(
        "--no-watchdog", action="store_true", help="Disable watchdog snapshots during training"
    )
    parser.add_argument(
        "--rich-output", action="store_true", help="Enable rich (non-ASCII) output in training logs"
    )
    parser.add_argument(
        "--teacher-model",
        default="phi4:latest",
        help="Ollama teacher model to pull (default: phi4:latest)",
    )
    parser.add_argument(
        "--ollama-model-dir",
        default="/workspace/ollama",
        help="Ollama model storage dir (default: /workspace/ollama)",
    )
    parser.add_argument("--no-ollama", action="store_true", help="Skip Ollama setup")
    parser.add_argument(
        "--distill-precompute-minutes",
        type=float,
        default=15.0,
        help="Max minutes to precompute distill cache before training (0 disables limit)",
    )
    parser.add_argument(
        "--data-center", default="EU-RO-1", help="RunPod data center ID (default: EU-RO-1)"
    )
    parser.add_argument("--s3-bucket", default="sxzm7zw9w9", help="RunPod S3 bucket name")
    parser.add_argument("--s3-region", default="eu-ro-1", help="RunPod S3 region")
    parser.add_argument(
        "--s3-endpoint", default="https://s3api-eu-ro-1.runpod.io", help="RunPod S3 endpoint URL"
    )
    parser.add_argument("--s3-prefix", default="mavaia", help="S3 prefix for repo/workspace sync")
    parser.add_argument(
        "--s3-ollama-prefix", default="ollama", help="S3 prefix for Ollama model storage"
    )
    parser.add_argument(
        "--use-s3",
        action="store_false",
        dest="use_s3",
        default=True,
        help="Disable S3 sync (enabled by default)",
    )
    parser.add_argument(
        "--no-refresh-code",
        action="store_false",
        dest="force_refresh",
        default=True,
        help="Skip forcing pod code refresh (faster, but may use stale code)",
    )
    parser.add_argument(
        "--hf-token", default=None, help="Hugging Face token (overrides env HF_TOKEN)"
    )
    parser.add_argument(
        "--volume-id",
        default=os.environ.get("RUNPOD_VOLUME_ID", ""),
        help="Attach an existing RunPod network volume by ID (default: RUNPOD_VOLUME_ID or empty)",
    )
    parser.add_argument(
        "--alias", default="mavaia_train", help="Alias for pod name (default: mavaia_train)"
    )
    parser.add_argument(
        "--volume-mount-path", default="/workspace", help="Mount path for the attached volume"
    )
    parser.add_argument(
        "--auto-distill",
        action="store_true",
        help="Auto-inject distillation args for transformer training",
    )
    parser.add_argument(
        "--distill-alpha", type=float, default=0.7, help="Hard loss weight for distillation"
    )
    parser.add_argument("--distill-temp", type=float, default=2.0, help="Distillation temperature")
    parser.add_argument(
        "--distill-topk", type=int, default=20, help="Top-k logprobs for teacher distillation"
    )
    parser.add_argument(
        "--gradient-checkpointing",
        action="store_true",
        help="Enable gradient checkpointing for transformer training",
    )
    parser.add_argument("--batch-size", type=int, help="Batch size for training")
    parser.add_argument(
        "--no-editable-install",
        action="store_false",
        dest="editable_install",
        default=True,
        help="Disable editable install for mavaia.",
    )
    parser.add_argument(
        "--force-editable",
        action="store_true",
        dest="editable_install_forced",
        help="Force editable install.",
    )

    # Forwarded args
    parser.add_argument(
        "--benchmark", action="store_true", help="Run benchmark mode instead of training"
    )
    parser.add_argument(
        "--bench-script",
        default="LiveBench/livebench/run_livebench.py",
        help="Path to evaluation script on the pod",
    )
    parser.add_argument(
        "--internal-bench",
        action="store_true",
        help="Run Mavaia's internal knowledge benchmark (run_tests.py --internal-bench) on the pod.",
    )
    parser.add_argument(
        "--curriculum",
        action="store_true",
        help="Run curriculum training (scripts/train_curriculum.py) instead of standard training.",
    )
    parser.add_argument(
        "--stage",
        help="Specific curriculum stage indices or names to run (e.g. 1,5,7 or logic,prose). Only works with --curriculum.",
    )
    parser.add_argument(
        "--list-stages",
        action="store_true",
        help="List all available curriculum stages and exit",
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
    parser.add_argument(
        "--script",
        help="Custom script to run on the pod (relative to repo root).",
    )
    
    # We use parse_known_args() instead of REMAINDER to prevent greedy swallowing of flags.
    # Everything runpod_bridge doesn't know will be passed to the remote task.
    args, extra_args = parser.parse_known_args()
    
    # Store extras in the appropriate field for downward compatibility
    if args.internal_bench or args.benchmark:
        args.bench_args = extra_args
        args.train_args = []
    else:
        args.train_args = extra_args
        args.bench_args = []

    if args.editable_install_forced:
        args.editable_install = True
    if not args.no_pip_stream:
        args.pip_stream = True

    if args.list_stages:
        subprocess.run([sys.executable, "scripts/train_curriculum.py", "--list-stages"])
        return 0

    if not RUNPOD_API_KEY:
        _rich_log("Error: Mavaia_Key not found in .env", "red", "✗")
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
                    _rich_log(
                        f"Balance ${bal:.2f} below ${args.min_balance:.2f}. Stopping pods.",
                        "yellow",
                        "⚠",
                    )
                    try:
                        for p in bridge.get_pods():
                            if str(p.get("name", "")).startswith("mavaia_"):
                                bridge.terminate_pod(p["id"])
                    except Exception:
                        pass
            else:
                if _BALANCE_LOW.is_set():
                    _BALANCE_LOW.clear()
                    _rich_log(
                        f"Balance ${bal:.2f} >= ${args.min_balance:.2f}. Resuming.",
                        "bold green",
                        "✓",
                    )
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
        _rich_log(f"Loaded S3 credentials from {s3_env_path}", "dim", "🔑")

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
            _rich_log(f"Auto-loaded public SSH key from {pub_key_path}", "dim", "🔑")

    if args.volume_id:
        args.use_s3 = False
    else:
        # If no volume ID, we can search globally for better inventory
        if args.use_s3:
            _rich_log(
                "S3 persistence enabled with no volume lock: searching all data centers for optimal GPUs...",
                "cyan",
                "🌐",
            )
            args.data_center = None

    if args.use_s3:
        if not shutil.which("aws"):
            _rich_log("aws CLI not found on VPS. Install awscli or use --no-s3.", "red", "✗")
            sys.exit(1)

    auto_timeout_s = None
    if args.stage:
        args.curriculum = True

    if args.curriculum and not args.auto and not args.fleet and not args.pod_id:
        _rich_log(
            "Curriculum mode enabled; auto pod search activated (5 minute limit).", "cyan", "ℹ"
        )
        args.auto = True
        auto_timeout_s = 300

    # DYNAMIC VRAM ESTIMATION
    details = get_task_details(args)
    vram_floor = calculate_required_vram(
        model_type=details["model_type"],
        dataset_size_chars=details["dataset_size"],
        batch_size=details["batch_size"],
        sequence_length=details["sequence_length"],
    )
    if vram_floor > args.min_vram:
        _rich_log(
            f"Dynamic Sizing: Task requires ~{vram_floor}GB VRAM (est). Increasing floor from {args.min_vram}GB.",
            "cyan",
            "⚖",
        )
        args.min_vram = vram_floor
    else:
        _rich_log(
            f"Dynamic Sizing: Task requires ~{vram_floor}GB VRAM (est). Using floor {args.min_vram}GB.",
            "dim",
            "⚖",
        )

    pod = None
    auto_candidate_gpus = None
    if args.fleet:
        threading.Thread(target=_balance_watchdog, daemon=True).start()
        if not args.volume_id:
            _rich_log("Fleet mode requires --volume-id (200GB network volume).", "red", "✗")
            sys.exit(1)
        if args.volume_mount_path != "/workspace":
            _rich_log("Fleet mode expects volume mounted at /workspace. Overriding.", "yellow", "⚠")
            args.volume_mount_path = "/workspace"
        roles = _fleet_role_specs(args)
        stop_event = threading.Event()
        workers = []

        global _FLEET_PROGRESS
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as fleet_progress:
            _FLEET_PROGRESS = fleet_progress
            for role in roles:
                t = threading.Thread(
                    target=_fleet_worker, args=(bridge, args, role, stop_event), daemon=True
                )
                t.start()
                workers.append(t)

            _rich_log("Fleet mode active. Press CTRL+C to stop.", "bold green", "🚀")
            try:
                while True:
                    time.sleep(5)
            except KeyboardInterrupt:
                _rich_log("Stopping fleet...", "yellow", "🛑")
                stop_event.set()
        return 0

    if args.auto:
        threading.Thread(target=_balance_watchdog, daemon=True).start()

        if USE_RICH:
            console.print(
                Panel(
                    Text.from_markup(
                        "[bold magenta]MAVAIA RUNPOD BRIDGE[/bold magenta]\n[cyan]Auto-Selection Mode Active[/cyan]"
                    ),
                    box=box.DOUBLE,
                    border_style="magenta",
                )
            )

        _rich_log("Finding existing pods...", "dim", "🔍")
        pods = bridge.get_pods()
        for p in pods:
            if str(p.get("name", "")).startswith("mavaia_"):
                _rich_log(f"Terminating existing pod {p['id']} ({p.get('name')})", "yellow", "💥")
                bridge.terminate_pod(p["id"])

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

        # Use the central selection logic to find valid GPUs
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            progress.add_task(
                description=f"Scanning RunPod Inventory (Min VRAM: {args.min_vram}GB)...",
                total=None,
            )
            filtered_gpus = _select_candidate_gpus(bridge, min_price, max_price, args.min_vram)

        if not filtered_gpus:
            _rich_log(
                f"No suitable GPUs currently available under ${max_price}/hr with {args.min_vram}GB VRAM.",
                "yellow",
                "⚠",
            )
            _rich_log("Will enter Wait & Retry loop...", "dim")
            best_gpu = None
            gpu_id = None
            auto_candidate_gpus = []
        else:
            if USE_RICH:
                gpu_table = Table(
                    title=f"Top Matches (Min VRAM: {args.min_vram}GB)", box=box.SIMPLE
                )
                gpu_table.add_column("Display Name", style="green")
                gpu_table.add_column("VRAM", style="cyan")
                gpu_table.add_column("Price/hr", style="yellow")
                gpu_table.add_column("Score (VRAM/$)", style="magenta")

                storage_overhead = 0.20
                for g in filtered_gpus[:5]:  # Show top 5
                    price = g["securePrice"] + storage_overhead
                    vram = g["memoryInGb"]
                    score = vram / price
                    gpu_table.add_row(
                        g["displayName"], f"{vram}GB", f"${g['securePrice']:.2f}", f"{score:.2f}"
                    )
                console.print(gpu_table)

            best_gpu = filtered_gpus[0]
            gpu_id = best_gpu["id"]
            auto_candidate_gpus = filtered_gpus

            storage_overhead = 0.20
            total_estimated = round(best_gpu["securePrice"] + storage_overhead, 2)
            _rich_log(
                f"Best current option: {best_gpu['displayName']} (${total_estimated}/hr total)",
                "bold green",
                "✓",
            )
    elif args.pod_id:
        # Resume existing pod flow
        pods = bridge.get_pods()
        pod = next((p for p in pods if p["id"] == args.pod_id), None)
        if not pod:
            _rich_log(f"Pod {args.pod_id} not found.", "red", "✗")
            sys.exit(1)

        # Check if pod needs starting
        if not pod.get("runtime"):
            _rich_log(f"Pod {args.pod_id} is stopped. Starting it...", "cyan", "⚡")
            # mutation PodResume($input: PodResumeInput!) { podResume(input: $input) { id } }
            bridge._query(
                """
                mutation ResumePod($input: PodResumeInput!) {
                    podResume(input: $input) {
                        id
                    }
                }
            """,
                variables={"input": {"podId": args.pod_id, "gpuCount": 1}},
            )

            _rich_log(f"Waiting for pod {args.pod_id} to initialize runtime...", "cyan", "⏳")
            while True:
                pods = bridge.get_pods()
                pod = next((p for p in pods if p["id"] == args.pod_id), None)
                if pod and pod.get("runtime") and pod["runtime"].get("uptimeInSeconds", 0) > 0:
                    break
                time.sleep(10)

        gpu_id = None  # Signal that no new pod creation is needed
    else:
        _rich_log(f"No pod specified. Finding GPU ID for {args.gpu}...", "dim", "🔍")
        gpu_types = bridge.get_gpu_types_with_availability()

        # Safety Check for manual GPU selection
        incompatible_keywords = ["Blackwell", "PRO 4500", "PRO 5000"]
        if any(kw in args.gpu for kw in incompatible_keywords):
            _rich_log(
                f"GPU '{args.gpu}' is known to be incompatible with our current software stack.",
                "red",
                "✗",
            )
            sys.exit(1)

        gpu_ids = [g["id"] for g in gpu_types]

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
                    _rich_log(
                        f"Warning: GPU '{args.gpu}' (mapped to '{gpu_id}') not found in available IDs: {gpu_ids[:5]}...",
                        "yellow",
                        "⚠",
                    )

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
            if (
                gpu_info
                and gpu_info.get("memoryInGb") is not None
                and gpu_info.get("memoryInGb") < args.min_vram
            ):
                _rich_log(
                    f"GPU {gpu_info.get('displayName', gpu_id)} has {gpu_info.get('memoryInGb')}GB VRAM; minimum is {args.min_vram}GB.",
                    "red",
                    "✗",
                )
                sys.exit(1)
        except Exception:
            pass

        candidate_gpus = (
            auto_candidate_gpus if args.auto else [{"id": gpu_id, "displayName": gpu_id}]
        )
        retry_sleep = 20
        auto_start = time.time()

        # Use a unified progress manager for the landing phase
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[dim]{task.completed}/{task.total}s[/dim]"),
            console=console,
        ) as progress:
            wait_limit = auto_timeout_s or 3600  # 1 hour default wait
            pod_task = progress.add_task(description="Looking for GPU...", total=wait_limit)

            while True:
                elapsed_wait = time.time() - auto_start
                if auto_timeout_s and elapsed_wait >= auto_timeout_s:
                    _rich_log(
                        f"Auto search timed out after {auto_timeout_s}s. Exiting.",
                        "red",
                        "✗",
                        progress=progress,
                        task_id=pod_task,
                    )
                    sys.exit(1)

                if args.auto:
                    progress.update(
                        pod_task, description=f"Scanning inventory (Min VRAM: {args.min_vram}GB)..."
                    )
                    candidate_gpus = _select_candidate_gpus(
                        bridge, min_price, max_price, args.min_vram
                    )

                if not candidate_gpus:
                    progress.update(
                        pod_task,
                        completed=min(wait_limit - 1, int(elapsed_wait)),
                        description=f"Waiting for {args.min_vram}GB GPU match...",
                    )
                    time.sleep(retry_sleep)
                    continue

                for candidate in candidate_gpus:
                    if _BALANCE_LOW.is_set():
                        _rich_log(
                            f"Balance below ${args.min_balance:.2f}. Auto mode paused.",
                            "yellow",
                            "⚠",
                            progress=progress,
                            task_id=pod_task,
                        )
                        time.sleep(min(60, retry_sleep))
                        continue
                    candidate_id = candidate.get("id") if isinstance(candidate, dict) else candidate
                    candidate_display = (
                        candidate.get("displayName")
                        if isinstance(candidate, dict)
                        else candidate_id
                    )

                    # Rationale for selection
                    vram_val = (
                        candidate.get("memoryInGb", "??") if isinstance(candidate, dict) else "??"
                    )
                    price_val = (
                        candidate.get("securePrice", "??") if isinstance(candidate, dict) else "??"
                    )
                    rationale = f"{vram_val}GB / ${price_val}/hr"

                    progress.update(
                        pod_task, description=f"Attempting {candidate_display} ({rationale})..."
                    )

                    # Re-verify availability one last time before mutation
                    availability_snapshot = bridge.get_gpu_types_with_availability()
                    candidate_info = next(
                        (g for g in availability_snapshot if g.get("id") == candidate_id), None
                    )
                    if candidate_info is not None and not bridge.gpu_is_available(candidate_info):
                        continue

                    # Auto-switch image for AMD ROCm
                    current_image = args.image
                    if "AMD" in candidate_display or "MI" in candidate_display:
                        _rich_log(
                            f"Detected AMD GPU ({candidate_display}). Switching to ROCm image.",
                            "cyan",
                            "🔧",
                            progress=progress,
                            task_id=pod_task,
                        )
                        current_image = "runpod/pytorch:2.1.0-py3.10-rocm5.7-devel-ubuntu22.04"
                        pod_env["HSA_OVERRIDE_GFX_VERSION"] = "11.0.0"
                    else:
                        pod_env.pop("HSA_OVERRIDE_GFX_VERSION", None)

                    pod_name = args.alias or "mavaia_train"
                    if args.dry_run:
                        _rich_log(
                            f"[DRY-RUN] Would launch {candidate_display} pod",
                            "dim",
                            progress=progress,
                            task_id=pod_task,
                        )
                        pod = {
                            "id": "dry-run-id",
                            "runtime": {
                                "ports": [{"ip": "1.2.3.4", "publicPort": 1234, "isIpPublic": True}]
                            },
                        }
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
                        continue

                    pod_id = pod_result["id"]
                    progress.update(pod_task, description=f"Found pod {pod_id}! Launching...")

                    poll_start = time.time()
                    while True:
                        pods = bridge.get_pods()
                        pod = next((p for p in pods if p["id"] == pod_id), None)
                        runtime = pod.get("runtime") if pod else None
                        uptime = runtime.get("uptimeInSeconds", 0) if runtime else 0
                        ports = runtime.get("ports", []) if runtime else []

                        # Wait for both uptime AND ports to be assigned
                        if uptime > 0 and len(ports) > 0:
                            progress.update(pod_task, completed=wait_limit)
                            break

                        elapsed = time.time() - poll_start
                        status = (
                            "Waiting for runtime..."
                            if uptime == 0
                            else "Waiting for network assignment..."
                        )
                        progress.update(
                            pod_task,
                            completed=min(wait_limit - 1, int(elapsed_wait + elapsed)),
                            description=f"Launching pod {pod_id}: {status}",
                        )

                        if elapsed > 300:
                            _rich_log(
                                "Safety timeout reached. Attempting to proceed...",
                                "yellow",
                                "⚠",
                                progress=progress,
                                task_id=pod_task,
                            )
                            break
                        time.sleep(5)

                    _rich_log(
                        f"Pod {pod_id} landed on {candidate_display}!",
                        "bold green",
                        "✓",
                        progress=progress,
                        task_id=pod_task,
                    )
                    break

                if pod:
                    break

                # If no candidate in the current filtered list worked, wait and retry the whole scan
                progress.update(
                    pod_task,
                    completed=min(wait_limit - 1, int(time.time() - auto_start)),
                    description="No matches found. Retrying scan...",
                )
                time.sleep(retry_sleep)
                retry_sleep = min(retry_sleep * 1.5, 300)

    # NOW pod is either found (args.pod_id) or created above.
    if not pod:
        _rich_log("Failed to acquire a pod.", "red", "✗")
        sys.exit(1)

    # Get SSH details
    runtime_info = pod.get("runtime") or {}
    ports_info = runtime_info.get("ports") or []

    # Try to find a public port that maps to 22 (SSH)
    # Check explicitly for isIpPublic OR if the IP looks like a real public IP (not 10.x, 172.x, 192.x)
    ssh_port_info = next(
        (
            p
            for p in ports_info
            if (
                p.get("isIpPublic")
                or not any(p.get("ip", "").startswith(pref) for pref in ["10.", "172.", "192."])
            )
            and p.get("privatePort") == 22
        ),
        None,
    )

    # Fallback: find ANY public port (often the only one)
    if not ssh_port_info:
        public_ports = [p for p in ports_info if p.get("isIpPublic") and p.get("publicPort")]
        if public_ports:
            ssh_port_info = public_ports[0]

    if not ssh_port_info:
        # No direct IP available; use proxy
        args.ssh_proxy = args.ssh_proxy or f"{pod['id']}-22@ssh.runpod.io"
        pod_ip = "ssh.runpod.io"
        pod_port = 22

        # Log why we failed to find a direct IP
        port_summary = [
            f"{p.get('privatePort')}->{p.get('publicPort')} (Public: {p.get('isIpPublic')})"
            for p in ports_info
        ]
        _rich_log(
            f"No direct public IP found in ports: {', '.join(port_summary) or 'None'}", "dim", "ℹ"
        )
        _rich_log(f"Using RunPod Proxy: {args.ssh_proxy}", "cyan", "🌐")
    else:
        pod_ip = ssh_port_info["ip"]
        pod_port = ssh_port_info["publicPort"]
        _rich_log(f"Direct IP detected: {pod_ip}:{pod_port}", "cyan", "🔗")

    # Initialize and Train
    interrupted = False
    failed = False
    watchdog_stop = None
    watchdog_thread = None

    try:
        # Initialization phase (single line progress)
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            pod_task = progress.add_task(description="Initializing pod...", total=None)

            if args.dry_run:
                _rich_log(
                    f"[DRY-RUN] Would sync to {pod_ip}:{pod_port} and start training.",
                    "dim",
                    progress=progress,
                    task_id=pod_task,
                )
                return

            # Instead of a hard 60s sleep, we let setup_pod_env's loop handle the service startup patience
            setup_pod_env(
                pod_ip,
                pod_port,
                args.ssh_key,
                pod["id"],
                args.ssh_proxy,
                progress=progress,
                task_id=pod_task,
                bridge=bridge,
            )
            sync_code(
                pod_ip,
                pod_port,
                args.ssh_key,
                REPO_ROOT,
                args.volume_mount_path,
                pod["id"],
                args.ssh_proxy,
                progress=progress,
                task_id=pod_task,
            )

            # For benchmarking/internal testing, we must push the weights if they are not already there
            if args.benchmark or args.internal_bench:
                sync_models_to_pod(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    REPO_ROOT,
                    args.volume_mount_path,
                    pod["id"],
                    args.ssh_proxy,
                    progress=progress,
                    task_id=pod_task,
                )

            ensure_mavaia_installed(
                pod_ip,
                pod_port,
                args.ssh_key,
                args.volume_mount_path,
                pod["id"],
                args.ssh_proxy,
                s3_bucket=args.s3_bucket if args.use_s3 else None,
                s3_prefix=args.s3_prefix if args.use_s3 else None,
                s3_region=args.s3_region if args.use_s3 else None,
                s3_endpoint=args.s3_endpoint if args.use_s3 else None,
                force_reinstall=args.force_refresh,
                pip_debug=args.pip_debug,
                pip_stream=args.pip_stream,
                editable_install=args.editable_install,
                progress=progress,
                task_id=pod_task,
            )

            ollama_cache_pull_failed = False
            if args.use_s3:
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
                        pod["id"],
                        args.ssh_proxy,
                        src=f"{args.volume_mount_path}/ollama",
                        progress=progress,
                        task_id=pod_task,
                    )
                except Exception as e:
                    ollama_cache_pull_failed = True
                    _rich_log(
                        f"Ollama S3 cache pull failed fresh. ({_redact_secrets(str(e))})",
                        "yellow",
                        "⚠",
                        progress=progress,
                        task_id=pod_task,
                    )

            if not args.no_ollama:
                setup_ollama(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    args.teacher_model,
                    args.ollama_model_dir,
                    pod["id"],
                    args.ssh_proxy,
                    progress=progress,
                    task_id=pod_task,
                )
                if args.use_s3 and ollama_cache_pull_failed:
                    _rich_log(
                        "Uploading Ollama cache for future runs...",
                        "cyan",
                        "📤",
                        progress=progress,
                        task_id=pod_task,
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
                        pod["id"],
                        args.ssh_proxy,
                        src=f"{args.volume_mount_path}/ollama",
                        progress=progress,
                        task_id=pod_task,
                    )

            progress.update(pod_task, description=f"Pod {pod['id']} ready!")
            time.sleep(1)

        # After initialization, we exit the Progress block and resume normal scrolling logs for training
        if not args.no_watchdog:
            interval_minutes = float(args.watchdog_minutes or 0.0)
            if interval_minutes > 0:
                watchdog_stop = threading.Event()

                def _watchdog_loop():
                    interval_s = max(60.0, interval_minutes * 60.0)
                    while not watchdog_stop.wait(interval_s):
                        try:
                            _rich_log("Watchdog: snapshot + sync", "cyan", "🐕")
                            remote_snapshot(
                                pod_ip,
                                pod_port,
                                args.ssh_key,
                                args.volume_mount_path,
                                pod["id"],
                                args.ssh_proxy,
                            )
                            get_artifacts(
                                pod_ip,
                                pod_port,
                                args.ssh_key,
                                REPO_ROOT,
                                args.volume_mount_path,
                                pod["id"],
                                args.ssh_proxy,
                            )
                            sync_training_data(
                                pod_ip,
                                pod_port,
                                args.ssh_key,
                                REPO_ROOT,
                                args.volume_mount_path,
                                pod["id"],
                                args.ssh_proxy,
                            )
                        except Exception as e:
                            _rich_log(f"Watchdog failed: {e}", "yellow", "⚠")

                watchdog_thread = threading.Thread(target=_watchdog_loop, daemon=True)
                watchdog_thread.start()

        if args.benchmark:
            bench_args = list(args.bench_args) if args.bench_args else []

            # Ensure --bench-name is present to test ALL subjects
            has_bench = any(arg == "--bench-name" for arg in bench_args)
            if not has_bench:
                # Use the top-level 'live_bench' name, which the script expands correctly
                _rich_log("No benchmark categories specified. Testing all subjects.", "cyan", "📚")
                bench_args.extend(["--bench-name", "live_bench"])

            # Ensure --model is present
            has_model = False
            for i, arg in enumerate(bench_args):
                if arg == "--model":
                    has_model = True
                    break

            if not has_model:
                # Try to find the latest run from latest_run.txt
                default_model = "mavaia_core/models/neural_text_generator"
                latest_run_ptr = (
                    REPO_ROOT
                    / "mavaia_core"
                    / "models"
                    / "neural_text_generator"
                    / "latest_run.txt"
                )
                if latest_run_ptr.exists():
                    try:
                        latest_path = Path(latest_run_ptr.read_text().strip())
                        if latest_path.is_absolute():
                            path_str = str(latest_path)
                            # MAP LOCAL REMOTE-SYNC PATHS TO POD PATHS
                            # Local: .../models/neural_text_generator_remote/curriculum/stage_x
                            # Pod: /workspace/mavaia/mavaia_core/models/neural_text_generator/curriculum/stage_x
                            if "models/neural_text_generator_remote" in path_str:
                                rel = path_str.split("models/neural_text_generator_remote")[
                                    -1
                                ].lstrip("/")
                                default_model = f"mavaia_core/models/neural_text_generator/{rel}"
                            else:
                                try:
                                    default_model = str(latest_path.relative_to(REPO_ROOT))
                                except ValueError:
                                    if "mavaia_core/models" in path_str:
                                        default_model = (
                                            "mavaia_core/models"
                                            + path_str.split("mavaia_core/models")[-1]
                                        )
                    except Exception:
                        pass

                # Make path absolute for pod context since we cd into LiveBench/livebench
                if not default_model.startswith("/"):
                    default_model = f"{args.volume_mount_path}/mavaia/{default_model}"

                _rich_log(
                    f"No model specified for benchmark. Defaulting to: {default_model}",
                    "cyan",
                    "🤖",
                )
                bench_args.extend(["--model", default_model])

            # Ensure --api-base is present if using a local model path
            has_api_base = any(arg == "--api-base" for arg in bench_args)
            if not has_api_base:
                _rich_log("Providing dummy api-base for local model evaluation.", "dim", "ℹ")
                bench_args.extend(["--api-base", "http://127.0.0.1:8000/v1", "--api-key", "dummy"])

            # Ensure --parallel-requests is 1 to avoid overwhelming the local uvicorn
            has_parallel = any(arg == "--parallel-requests" for arg in bench_args)
            if not has_parallel:
                bench_args.extend(["--parallel-requests", "1"])

            # Always force fresh results to ensure we don't skip anything
            if "--remove-existing-judgment-file" not in bench_args:
                bench_args.append("--remove-existing-judgment-file")

            # Use a clean display name so LiveBench doesn't use the full path as an identifier
            if "--model-display-name" not in bench_args:
                bench_args.extend(["--model-display-name", "mavaia"])

            # FORCE FOREGROUND MODE: Otherwise it spawns a tmux session and exits instantly
            if "--mode" not in bench_args:
                bench_args.extend(["--mode", "single"])

            # Remove any resume flags to force fresh start
            bench_args = [
                arg
                for arg in bench_args
                if arg not in ("--resume", "--resume-inference", "--resume-grading")
            ]

            remote_benchmark(
                pod_ip,
                pod_port,
                args.ssh_key,
                bench_args,
                args.volume_mount_path,
                pod["id"],
                args.ssh_proxy,
                script_rel=args.bench_script,
            )
            get_bench_results(
                pod_ip,
                pod_port,
                args.ssh_key,
                REPO_ROOT,
                args.volume_mount_path,
                pod["id"],
                args.ssh_proxy,
            )

            _rich_log("Remote benchmark successful! Results retrieved.", "bold green", "✓")

            if not args.no_auto_report:
                # LIGHTWEIGHT GAP ANALYSIS
                summarize_results(REPO_ROOT)

            if args.use_s3:
                # We also push the results to S3 for persistence
                s3_sync_pod(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    args.s3_bucket,
                    args.s3_prefix,
                    args.s3_region,
                    args.s3_endpoint,
                    "push",
                    pod["id"],
                    args.ssh_proxy,
                    src=f"{args.volume_mount_path}/mavaia",
                )
        elif args.internal_bench:
            _rich_log("Starting Mavaia Internal Knowledge Benchmark...", "bold green", "🚀")
            
            # Internal bench uses run_tests.py with --internal-bench
            script_rel = "run_tests.py"
            bench_args = ["--internal-bench", "--quiet"]
            
            try:
                # 1. Health check first
                health_ok = check_model_health(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    args.volume_mount_path,
                    pod["id"],
                    args.ssh_proxy,
                )
                
                if not health_ok:
                    _rich_log("Proceeding with benchmark despite health check failure, but results may be degraded.", "yellow", "⚠")

                # 2. Run the actual benchmark
                remote_train(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    bench_args,
                    args.volume_mount_path,
                    pod["id"],
                    args.ssh_proxy,
                    script_rel=script_rel,
                )
            except subprocess.CalledProcessError as e:
                _rich_log(f"Benchmark script finished with non-zero exit code (some tests may have failed).", "yellow", "⚠")
            except Exception as e:
                _rich_log(f"Benchmark execution error: {e}", "red", "✗")
            finally:
                # ALWAYS attempt to pull results, even on failure
                get_internal_bench_results(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    REPO_ROOT,
                    args.volume_mount_path,
                    pod["id"],
                    args.ssh_proxy,
                )
                _rich_log("Internal benchmark process complete. Results retrieved.", "bold green", "✓")
        else:
            train_args = list(args.train_args)
            if args.batch_size:
                train_args.extend(["--batch-size", str(args.batch_size)])
            if args.gradient_checkpointing:
                train_args.append("--gradient-checkpointing")

            script_rel = args.script or "scripts/train_neural_text_generator.py"
            if args.curriculum:
                script_rel = "scripts/train_curriculum.py"
                if args.stage:
                    _rich_log(f"Targeting curriculum stages: {args.stage}", "cyan", "🎯")
                    if "--stages" not in train_args:
                        train_args.extend(["--stages", args.stage])
                else:
                    _rich_log("Running full curriculum sequence", "cyan", "📚")
            else:
                if (
                    not args.rich_output
                    and "--plain-output" not in train_args
                    and script_rel.endswith("train_neural_text_generator.py")
                ):
                    train_args.append("--plain-output")
                if args.auto_distill:
                    if "--distill" not in train_args:
                        train_args.extend(
                            [
                                "--distill",
                                "--teacher-model",
                                args.teacher_model,
                                "--distill-alpha",
                                str(args.distill_alpha),
                                "--distill-temp",
                                str(args.distill_temp),
                                "--distill-topk",
                                str(args.distill_topk),
                                "--distill-precompute-minutes",
                                str(args.distill_precompute_minutes),
                            ]
                        )
                    if "--model-type" not in train_args and "--model_type" not in train_args:
                        train_args.extend(["--model-type", "transformer"])
                else:
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
                    i = 0
                    while i < len(train_args):
                        arg = train_args[i]
                        if arg in distill_flags:
                            if i + 1 < len(train_args) and not train_args[i + 1].startswith("--"):
                                i += 2
                            else:
                                i += 1
                            continue
                        cleaned.append(arg)
                        i += 1
                    if cleaned != train_args:
                        _rich_log(
                            "Distillation disabled (use --auto-distill to enable).", "yellow", "⚠"
                        )
                    train_args = cleaned

            remote_train(
                pod_ip,
                pod_port,
                args.ssh_key,
                train_args,
                args.volume_mount_path,
                pod["id"],
                args.ssh_proxy,
                script_rel=script_rel,
            )
            get_artifacts(
                pod_ip,
                pod_port,
                args.ssh_key,
                REPO_ROOT,
                args.volume_mount_path,
                pod["id"],
                args.ssh_proxy,
            )
            sync_training_data(
                pod_ip,
                pod_port,
                args.ssh_key,
                REPO_ROOT,
                args.volume_mount_path,
                pod["id"],
                args.ssh_proxy,
            )

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
                    pod["id"],
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
                    pod["id"],
                    args.ssh_proxy,
                    src=f"{args.volume_mount_path}/ollama",
                )

            _rich_log("Remote training successful! Artifacts retrieved.", "bold green", "✓")

    except KeyboardInterrupt:
        interrupted = True
        _rich_log("CTRL+C detected: giving pod SSH 5s to stabilize...", "yellow", "⚠")
        time.sleep(5)
        _rich_log("Attempting to save snapshot and sync artifacts before exit...", "cyan", "💾")
        try:
            remote_snapshot(
                pod_ip, pod_port, args.ssh_key, args.volume_mount_path, pod["id"], args.ssh_proxy
            )
        except Exception as e:
            _rich_log(f"Snapshot failed: {_redact_secrets(str(e))}", "red", "✗")

        for attempt in range(3):
            try:
                _rich_log(f"Syncing artifacts (attempt {attempt+1}/3)...", "cyan", "🔄")
                get_artifacts(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    REPO_ROOT,
                    args.volume_mount_path,
                    pod["id"],
                    args.ssh_proxy,
                )
                sync_training_data(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    REPO_ROOT,
                    args.volume_mount_path,
                    pod["id"],
                    args.ssh_proxy,
                )
                _rich_log("Sync successful!", "bold green", "✓")
                break
            except Exception as e:
                _rich_log(f"Sync attempt {attempt+1} failed: {_redact_secrets(str(e))}", "red", "✗")
                if attempt < 2:
                    time.sleep(5)

    except Exception as e:
        failed = True
        _rich_log(f"Error detected: {_redact_secrets(str(e))}. Saving snapshot...", "red", "✗")
        try:
            remote_snapshot(
                pod_ip, pod_port, args.ssh_key, args.volume_mount_path, pod["id"], args.ssh_proxy
            )
        except Exception as snap_e:
            _rich_log(f"Snapshot failed: {snap_e}", "red", "✗")
        try:
            get_artifacts(
                pod_ip,
                pod_port,
                args.ssh_key,
                REPO_ROOT,
                args.volume_mount_path,
                pod["id"],
                args.ssh_proxy,
            )
            sync_training_data(
                pod_ip,
                pod_port,
                args.ssh_key,
                REPO_ROOT,
                args.volume_mount_path,
                pod["id"],
                args.ssh_proxy,
            )
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
                    pod["id"],
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
                        pod["id"],
                        args.ssh_proxy,
                        src="/workspace/ollama",
                    )
                except Exception as ollama_e:
                    _rich_log(f"Ollama S3 push skipped: {ollama_e}", "yellow", "⚠")
        except Exception as sync_e:
            _rich_log(f"Artifact sync failed: {sync_e}", "red", "✗")

    finally:
        if watchdog_stop is not None:
            watchdog_stop.set()
        if pod and pod.get("id") and pod["id"] != "dry-run-id":
            if args.terminate:
                _rich_log(f"Terminating pod {pod['id']}...", "red", "💥")
                bridge.terminate_pod(pod["id"])
            else:
                _rich_log(f"Stopping pod {pod['id']} (saving costs)...", "yellow", "🛑")
                bridge.stop_pod(pod["id"])

    if interrupted:
        return 130
    if failed:
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
