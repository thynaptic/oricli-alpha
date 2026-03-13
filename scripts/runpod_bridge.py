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

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent

# BOOTSTRAP: Ensure we are running in the virtual environment
VENV_DIR = REPO_ROOT / ".venv"
if VENV_DIR.exists() and sys.prefix != str(VENV_DIR.resolve()):
    VENV_PYTHON = VENV_DIR / "bin" / "python3"
    if VENV_PYTHON.exists():
        # Re-run the script using the venv python
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve())] + sys.argv[1:])

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Try to import OricliAlpha parser
try:
    from oricli_core.evaluation.livebench_parser import LiveBenchResultParser
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

    # Minimal no-op stubs so rich-dependent calls don't raise NameError
    class _NoOpCtx:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def update(self, *a, **kw): pass
        def add_task(self, *a, **kw): return self
        def __call__(self, *a, **kw): return ""
        def __str__(self): return ""

    class Progress(_NoOpCtx):
        def __init__(self, *a, **kw): pass

    class Live(_NoOpCtx):
        def __init__(self, *a, **kw): pass
        def update(self, *a, **kw): pass

    class SpinnerColumn:
        def __init__(self, *a, **kw): pass

    class BarColumn:
        def __init__(self, *a, **kw): pass

    class TextColumn:
        def __init__(self, *a, **kw): pass

    class Table:
        def __init__(self, *a, **kw): pass
        def add_column(self, *a, **kw): pass
        def add_row(self, *a, **kw): pass

    class Panel:
        def __init__(self, *a, **kw): pass

    class Text:
        def __init__(self, *a, **kw): pass

    class box:
        ROUNDED = None
        SIMPLE = None

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


# Load environment variables (hand-rolled simple loader)
def load_dotenv(path: Path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Handle 'export ' prefix
        if line.startswith("export "):
            line = line[len("export "):].strip()
        
        if "=" in line:
            key, _, value = line.partition("=")
            # Handle trailing comments
            if "#" in value:
                value, _, _ = value.partition("#")
            if "|" in value:
                value, _, _ = value.partition("|")
                
            # Strip quotes if present
            value = value.strip().strip("'").strip('"')
            k = key.strip()
            os.environ[k] = value


def check_s3_credentials():
    """Verify S3 credentials exist and are valid before starting."""
    id_val = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_val = os.environ.get("AWS_SECRET_ACCESS_KEY")
    
    if not id_val or not secret_val:
        _rich_log("ERROR: AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY not found in environment.", "red", "✗")
        return False
        
    _rich_log(f"AWS Credentials found (ID: {id_val[:5]}...)", "dim", "ℹ")
    
    # Optional: Quick check with s3 ls
    try:
        bucket = os.environ.get("AWS_BUCKET_NAME", "")
        endpoint_url = os.environ.get("MAVAIA_S3_ENDPOINT", "")
        cmd = ["aws", "s3", "ls"]
        if endpoint_url:
            cmd.extend(["--endpoint-url", endpoint_url])
        if bucket:
            cmd.append(f"s3://{bucket}")
            
        subprocess.run(cmd, check=True, capture_output=True, timeout=10)
        _rich_log("S3 credentials verified via bucket access.", "green", "✓")
        return True
    except Exception as e:
        _rich_log(f"Warning: Could not verify S3 access: {e}. Proceeding anyway...", "yellow", "⚠")
        return True

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


load_dotenv(REPO_ROOT / ".env")
load_dotenv(Path.cwd() / ".env")

# RunPod API configuration
RUNPOD_API_KEY = os.environ.get("OricliAlpha_Key")


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


import yaml


def calculate_required_vram(
    model_type: str,
    dataset_size_chars: int = 0,
    batch_size: int = 4,
    sequence_length: int = 512,
    model_name: Optional[str] = None,
    is_quantized: bool = False,
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
        # Check for 3B+ models
        is_large_model = False
        if model_name:
            name_lower = model_name.lower()
            if "3b" in name_lower or "phi-3.5" in name_lower or "llama-3.2" in name_lower:
                is_large_model = True
            elif "7b" in name_lower or "8b" in name_lower:
                is_large_model = True
                # Force at least 40GB for 7B+ even with LoRA/Quant
                return 40

        if is_large_model:
            # 3B models: ~6GB weights (16-bit), ~2GB (4-bit)
            # LoRA + Optimizer: ~4-8GB (DPO doubles this)
            # Activations: ~4-12GB (depends on seq_len and depth)
            if is_quantized:
                base_gb = 24  # Floor for 3B quantized LoRA/DPO with headroom
            else:
                base_gb = 32  # Floor for 3B 16-bit LoRA/DPO
        else:
            # Transformer defaults to GPT-2 (124M) or DistilGPT-2 (82M)
            # Training GPT-2 with Adam needs ~10-12GB for stability
            base_gb = 12

    # 2. Dataset Scaling (Data loading buffer, shuffling, caching)
    # Add ~1GB for every 150M characters of data (more aggressive)
    data_gb = math.ceil(dataset_size_chars / 150_000_000)

    # 3. Hyperparameter Scaling
    # Batch size: linear scaling
    # Sequence length: quadratic scaling for self-attention
    # Scaling factor increases for larger models due to hidden dimension size
    hp_scale = 3.0 if (model_name and "3b" in model_name.lower()) else 1.0
    hp_multiplier = (batch_size / 4) * ((sequence_length / 512) ** 2) * hp_scale

    # Total calculation
    estimated = base_gb + data_gb + (4 * hp_multiplier) # Increased multiplier for activations

    # Add a safety headroom (25%)
    total_with_headroom = math.ceil(estimated * 1.25)

    # Absolute floors based on model size
    if model_name:
        name_lower = model_name.lower()
        if "3b" in name_lower or "phi-3.5" in name_lower or "llama-3.2" in name_lower:
            return max(30, total_with_headroom) # Aim for at least 30GB (triggers 40GB+ pods)
        elif "7b" in name_lower or "8b" in name_lower:
            return max(48, total_with_headroom)

    return max(12, total_with_headroom)


def get_task_details(args) -> Dict[str, Any]:
    """
    Extract model details from args, curriculum, or profile YAML.
    """
    model_type = "transformer"  # default
    model_name = None
    dataset_size = 0
    batch_size = 4  # default
    seq_len = 512  # default
    is_quantized = False

    # 1. Check if we have a profile YAML in train_args
    profile_path = None
    if hasattr(args, "train_args") and args.train_args:
        for i, arg in enumerate(args.train_args):
            if arg == "--profile" and i + 1 < len(args.train_args):
                profile_path = Path(args.train_args[i + 1])
                break
    
    if profile_path and profile_path.exists():
        try:
            with open(profile_path, "r") as f:
                profile = yaml.safe_load(f)
                model_type = profile.get("model_type", model_type)
                
                t_config = profile.get("transformer_config", {})
                if t_config:
                    model_name = t_config.get("model_name")
                    seq_len = t_config.get("max_length", seq_len)
                    batch_size = t_config.get("batch_size", batch_size)
                    if t_config.get("_load_4bit") or t_config.get("_load_8bit"):
                        is_quantized = True
                
                # Use top-level overrides if present
                if profile.get("batch_size"):
                    batch_size = profile.get("batch_size")
                
                # Estimate dataset size from books
                book_ids = profile.get("book_ids", [])
                dataset_size = len(book_ids) * 50_000_000 # Heuristic: 50MB per book
        except Exception as e:
            _rich_log(f"Warning: Failed to parse profile for VRAM estimation: {e}", "yellow", "⚠")

    # 2. Check if we're in curriculum mode (if profile didn't already set things)
    if args.curriculum and not model_name:
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
                    / "oricli_core"
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

    # 3. Extract/Override from train_args if provided
    if hasattr(args, "train_args") and args.train_args:
        # Simple parser for forwarded args
        for i, arg in enumerate(args.train_args):
            if arg == "--batch-size" and i + 1 < len(args.train_args):
                try:
                    batch_size = int(args.train_args[i + 1])
                except ValueError:
                    pass
            elif arg == "--model-type" and i + 1 < len(args.train_args):
                model_type = args.train_args[i + 1]
            elif arg == "--model-name" and i + 1 < len(args.train_args):
                model_name = args.train_args[i + 1]

    # 4. Explicit args on bridge take precedence
    if args.batch_size:
        batch_size = args.batch_size

    return {
        "model_type": model_type,
        "model_name": model_name,
        "dataset_size": dataset_size,
        "batch_size": batch_size,
        "sequence_length": seq_len,
        "is_quantized": is_quantized,
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
        # 1. ATTEMPT GRAPHQL (Primary)
        field_sets = [
            "id name displayName memoryInGb securePrice communityPrice availability",
            "id name displayName memoryInGb securePrice communityPrice",
            "id displayName memoryInGb securePrice communityPrice",
        ]
        for fields in field_sets:
            query = f"query {{ gpuTypes {{ {fields} }} }}"
            data = self._query(query, log_errors=False, allow_http_error=True)
            
            if "errors" in data:
                # Catch internal server error specifically
                is_internal = any("INTERNAL_SERVER_ERROR" in str(e) for e in data["errors"])
                if is_internal:
                    _rich_log("RunPod GraphQL internal error. Pausing 30s before retry...", "yellow", "⏳")
                    time.sleep(30)
                continue
                
            res = data.get("data", {}).get("gpuTypes", [])
            if res:
                return res
        
        # 2. FALLBACK TO REST API (If GraphQL fails or returns empty)
        _rich_log("Attempting REST API fallback for GPU inventory...", "cyan", "🌐")
        try:
            # RunPod has a semi-public REST endpoint for gpu-types
            rest_url = "https://api.runpod.io/utility/v1/gpu-types"
            resp = requests.get(rest_url, timeout=10)
            if resp.status_code == 200:
                rest_data = resp.json()
                # The REST schema is slightly different, we need to map it to our internal Dict structure
                gpus = []
                for g in rest_data.get("gpuTypes", []):
                    gpus.append({
                        "id": g.get("id"),
                        "name": g.get("name"),
                        "displayName": g.get("displayName"),
                        "memoryInGb": g.get("memoryInGb"),
                        "securePrice": g.get("securePrice"),
                        "communityPrice": g.get("communityPrice"),
                        "availability": True # REST doesn't always show status, assume true and let creation fail if wrong
                    })
                if gpus:
                    _rich_log(f"REST Fallback successful: Found {len(gpus)} GPU types.", "green", "✓")
                    return gpus
        except Exception as e:
            _rich_log(f"REST Fallback failed: {e}", "dim")

        _rich_log("Warning: All GPU inventory queries failed. Check API Key or RunPod Status.", "red", "✗")
        return []

    @staticmethod
    def gpu_is_available(gpu: Dict, required_count: int = 1) -> bool:
        """Check if GPU has enough stock for the request."""
        # 1. Check stockStatus (The most accurate)
        if "stockStatus" in gpu and gpu.get("stockStatus") is not None:
            status = str(gpu.get("stockStatus")).lower()
            if status == "out_of_stock":
                return False
            # If requesting a cluster (>3 pods), we ideally want 'high' stock
            if required_count > 3 and status == "low":
                return False
            return True
            
        # 2. Check legacy availability boolean/number
        if "availability" in gpu and gpu.get("availability") is not None:
            avail = gpu.get("availability")
            if isinstance(avail, bool):
                return avail
            if isinstance(avail, (int, float)):
                return avail > 0
            status = str(avail).lower()
            return status in ("available", "in_stock", "ok", "true", "ready")
            
        # Unknown; assume available
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
            "query { myself { clientBalance } }",
            "query { myself { hostBalance } }",
            "query { myself { balance } }", # Fallback for old versions
        ]
        for q in queries:
            data = self._query(q, log_errors=False, allow_http_error=True)
            myself = data.get("data", {}).get("myself", {}) if isinstance(data, dict) else {}
            for key in ("clientBalance", "hostBalance", "balance"):
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
        cloud_type: str = "SECURE",
    ):
        input_data = {
            "name": name,
            "gpuTypeId": gpu_type_id,
            "gpuCount": 1,
            "cloudType": cloud_type,
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
        if result and "data" in result and result["data"]:
            return result["data"].get("podFindAndDeployOnDemand")
        return None

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

    def get_clusters(self) -> List[Dict]:
        """List all active clusters."""
        query = """
        query {
          clusters {
            id
            name
            status
            clusterType
            nodeCount
            pods {
              id
              name
              runtime {
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
        return result.get("data", {}).get("clusters", [])

    def create_cluster(
        self,
        name: str,
        gpu_type_id: str,
        pod_count: int,
        gpu_count_per_pod: int = 1,
        bid_per_gpu: Optional[float] = None,
        image: Optional[str] = None,
        template_id: Optional[str] = None,
        volume_mount_path: str = "/workspace",
        ssh_key_value: Optional[str] = None,
        volume_id: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        """Create a new instant cluster using nodeGroups."""
        if bid_per_gpu:
            _rich_log("Warning: bid_per_gpu is not supported for clusters and will be ignored.", "yellow", "⚠")

        input_data = {
            "clusterName": name,
            "gpuTypeId": gpu_type_id,
            "gpuCountPerPod": gpu_count_per_pod,
            "podCount": pod_count,
            "type": "SLURM",
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
            for k in ["PUBLIC_KEY", "SSH_PUBLIC_KEY", "RUNPOD_PUBLIC_KEY", "TCP_PORT_22", "SSH_KEY"]:
                env_vars.append({"key": k, "value": ssh_key_value})

        if env_vars:
            input_data["env"] = env_vars

        if volume_id:
            input_data["networkVolumeId"] = volume_id

        if template_id:
            input_data["templateId"] = template_id
        elif image:
            input_data["imageName"] = image
        else:
            # Fallback to default if somehow neither is set
            input_data["imageName"] = "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04"

        query = """
        mutation createCluster($input: CreateClusterInput!) {
          createCluster(input: $input) {
            id
            name
          }
        }
        """
        result = self._query(query, variables={"input": input_data})
        if result and "data" in result and result["data"]:
            return result["data"].get("createCluster")
        return None

    def delete_cluster(self, cluster_id: str):
        """Delete an entire cluster."""
        query = """
        mutation deleteCluster($input: DeleteClusterInput!) {
          deleteCluster(input: $input)
        }
        """
        result = self._query(query, variables={"input": {"clusterId": cluster_id}})
        return result.get("data", {}).get("deleteCluster")


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


def ensure_oricli_installed(
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
    benchmark: bool = False,
    internal_bench: bool = False,
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
    s3_key = f"s3://{s3_bucket}/{s3_prefix}.tar" if s3_bucket else ""
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

    # S3 restore logic: pull to a unique temp dir then atomic swap
    s3_restore = ""
    if s3_key:
        s3_restore = (
            f'if [ ! -d {workdir}/oricli ] || [ "{force_reinstall}" = "True" ] || [ "{force_reinstall}" = "1" ]; then '
            f"  echo '[*] Syncing latest code from S3...'; "
            f"  rm -rf {workdir}/oricli; " # Pre-clean to ensure no weird FS locks
            f"  CUR_TIME=$(date +%s); "
            f"  EXTRACT_DIR={workdir}/oricli_$CUR_TIME; "
            f"  mkdir -p $EXTRACT_DIR; "
            f"  {cred_export} aws s3 cp {s3_key} - {aws_flags} | tar -xf - --no-same-owner -C $EXTRACT_DIR; "
            f"  if [ -d $EXTRACT_DIR ]; then mv $EXTRACT_DIR {workdir}/oricli; else echo '[ERROR] S3 extraction failed'; exit 1; fi; "
            f"fi; "
        )

    install_cmd = (
        "set -e; "
        f"benchmark='{benchmark}'; "
        f"internal_bench='{internal_bench}'; "
        f"force_reinstall='{force_reinstall}'; "
        f"{cred_export}"
        f"{s3_restore}"
        f"cd {workdir}/oricli; "
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
        "  echo '[INFO] Purging old oricli-core installations to ensure fresh code usage...'; "
        '  "$VENV_PY" -m pip uninstall -y oricli-core 2>/dev/null || true; '
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
        '"$VENV_PY" -m pip install --upgrade "bitsandbytes>=0.46.1" scipy datasets transformers accelerate huggingface_hub pyarrow wikipedia internetarchive kaggle regex pandas peft trl numpy Pillow torch torchvision torchaudio xxhash shortuuid libtmux python-dotenv uvicorn fastapi pydantic beautifulsoup4 PyPDF2 PyYAML tensorflow keras -q || true; '
        'if [ -d LiveBench ] && ([ "$benchmark" = "True" ] || [ "$internal_bench" = "True" ]); then '
        "  echo '[INFO] LiveBench detected and requested. Installing in editable mode...'; "
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
        "sleep 5; "
        "ollama list >/dev/null 2>&1 || true; "
        f"ollama pull {model_name}; "
        "echo ollama_ready"
    )

    _run_ssh(ssh_key, pod_ip, pod_port, pod_id, proxy, ollama_cmd, progress=progress, task_id=task_id)


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
    # Scale back concurrency to avoid 524 (Timeout) errors on Cloudflare/RunPod
    for key, val in [
        ("default.s3.max_concurrent_requests", "20"),
        ("default.s3.multipart_chunksize", "64MB"),
        ("default.s3.multipart_threshold", "64MB"),
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
    """Archive local repo to a temp file then upload to S3 (more reliable for S3-compatible providers)."""
    import tempfile
    
    # Create a temporary file for the archive
    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        
    try:
        _rich_log(f"Archiving local repo to {tmp_path.name}...", "cyan", "📦")
        tar_cmd = [
            "tar",
            "-chf",
            str(tmp_path),
            "--exclude=.git",
            "--exclude=__pycache__",
            "--exclude=.venv",
            "--exclude=*.pyc",
            "--exclude=*.tmp",
            "--exclude=.cursor",
            "--exclude=conductor",
            "--exclude=plans",
            "--exclude=tests",
            "--exclude=docs",
            "--exclude=build",
            "--exclude=*.egg-info",
            "--exclude=runs",
            "--exclude=checkpoints",
            "--exclude=snapshots",
            "--exclude=*.log",
            "--exclude=models",
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
        
        # Run tar
        subprocess.run(tar_cmd, check=True)
        archive_size_mb = tmp_path.stat().st_size / (1024 * 1024)
        _rich_log(f"Archive created ({archive_size_mb:.1f} MB). Uploading to S3...", "cyan", "📤")
        
        _aws_configure_fast(region, endpoint_url)
        _s3_abort_zombies(bucket, prefix, region, endpoint_url)
        s3_key = f"s3://{bucket}/{prefix}.tar"
        
        aws_cmd = ["aws", "s3", "cp", str(tmp_path), s3_key] + _aws_cli_flags(region, endpoint_url)
        
        # Run upload with progress visibility
        subprocess.run(aws_cmd, check=True)
        _rich_log("Repo archive uploaded to S3.", "bold green", "✓")
        
    finally:
        # Cleanup temp file
        if tmp_path.exists():
            tmp_path.unlink()


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
                # Use capture_output if progress is provided to keep the console clean
                subprocess.run(cmd_list, check=check, capture_output=bool(progress))
                return
            except subprocess.CalledProcessError as e:
                # 255 usually means SSH connection failed
                if e.returncode == 255:
                    attempt += 1
                    if attempt > retries:
                        raise e
                    _rich_log(f"SSH 255 (Connection lost). Retry {attempt}/{retries} in {retry_delay_s}s...", "dim", "⏳")
                    time.sleep(retry_delay_s)
                    continue
                raise e

    # ALWAYS try the proxy fallback if it's available and we are hitting 255s
    # Direct IP can often drop during heavy disk I/O cleanup
    try:
        if pod_ip and str(pod_ip) != "ssh.runpod.io":
            _try(_ssh_base(ssh_key, str(pod_port), f"root@{pod_ip}") + [cmd])
        else:
            # Fallback/Direct Proxy
            _try(_ssh_base(ssh_key, "22", proxy or f"{pod_id}-22@ssh.runpod.io") + [cmd])
    except subprocess.CalledProcessError as e:
        if pod_id and e.returncode == 255:
            _rich_log(
                "Direct SSH failed (255); forcing proxy fallback.",
                "yellow",
                "⚠",
                progress=progress,
                task_id=task_id,
            )
            # Use the global proxy pattern
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
    src: str = "/workspace/oricli",
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
    s3_key = f"s3://{bucket}/{prefix}.tar"

    if direction == "push":
        cmd = (
            f"{cred_export}{aws_cfg}{abort_zombies}"
            f"if command -v mbuffer > /dev/null 2>&1; then "
            f"  {tar_pipe_push.format(src=src)} | mbuffer -m 256M -P 80 | aws s3 cp - {s3_key} {aws_flags}; "
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


def pre_sync_cleanup(
    pod_ip: str,
    pod_port: int,
    ssh_key: str,
    workdir: str,
    pod_id: str = None,
    proxy: str = None,
    progress=None,
    task_id=None,
):
    _rich_log("Performing pre-sync disk cleanup on pod...", "cyan", "🧹", progress=progress, task_id=task_id)
    
    # Aggressive but shallow cleanup of logs and temporary files
    cleanup_cmd = (
        f"find {workdir} -maxdepth 2 -name '*.log' -delete 2>/dev/null || true; "
        f"find {workdir} -maxdepth 2 -name '*.tmp' -delete 2>/dev/null || true; "
        f"rm -rf {workdir}/oricli/oricli_core/models/neural_text_generator/snapshots/* 2>/dev/null || true; "
        f"rm -rf {workdir}/oricli/oricli_core/models/neural_text_generator/checkpoints/* 2>/dev/null || true; "
        f"rm -rf {workdir}/oricli/oricli_core/models/neural_text_generator/runs/* 2>/dev/null || true; "
        f"rm -rf {workdir}/oricli/runs/* 2>/dev/null || true; "
        f"rm -rf {workdir}/oricli/build/* 2>/dev/null || true; "
        f"rm -rf /root/.cache/pip/* 2>/dev/null || true; "
        f"rm -rf /root/.cache/huggingface/* 2>/dev/null || true; "
        f"rm -rf /tmp/* 2>/dev/null || true; "
        "df -h /workspace"
    )
    
    _run_ssh(ssh_key, pod_ip, pod_port, pod_id, proxy, cleanup_cmd, progress=progress, task_id=task_id)

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

    rsync_info = ["--quiet"] if progress else []

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
        "--include",
        "oricli_core/data/rfal_lessons.jsonl",
        "--include",
        "oricli_core/data/search.py",
        "--include",
        "oricli_core/data/__init__.py",
        "--exclude",
        "oricli_core/data/*",
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

    def _run_rsync(target_host, target_port):
        cmd = [
            "rsync",
            "-rlptzL",
            "--human-readable",
            "--no-perms",
            "-e",
            _ssh_e(ssh_key, str(target_port)),
            str(local_path) + "/",
            f"{target_host}:{workdir}/oricli",
        ] + common_excludes + rsync_info
        
        proc = subprocess.run(cmd, check=False, capture_output=bool(progress))
        return proc

    # Determine initial target
    if pod_ip and str(pod_ip) != "ssh.runpod.io":
        host = f"root@{pod_ip}"
        port = pod_port
    else:
        host = proxy or f"{pod_id}-22@ssh.runpod.io"
        port = 22

    proc = _run_rsync(host, port)
    
    # Handle retry/fallback
    if proc.returncode == 255 and pod_id and host != f"{pod_id}-22@ssh.runpod.io":
        _rich_log("Direct rsync failed (255); retrying via proxy.", "yellow", "⚠", progress=progress, task_id=task_id)
        proc = _run_rsync(f"{pod_id}-22@ssh.runpod.io", 22)

    if proc.returncode != 0 and proc.returncode != 23:
        raise subprocess.CalledProcessError(proc.returncode, "rsync")
    elif proc.returncode == 23:
        _rich_log("Rsync partial transfer (23). Safe to proceed.", "dim", "ℹ", progress=progress, task_id=task_id)


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

    src_dir = local_path / "oricli_core" / "models"
    if not src_dir.exists():
        _rich_log(
            "No local models directory found to sync.", "yellow", "⚠", progress=progress, task_id=task_id
        )
        return

    common_args = [
        "rsync",
        "-rlptzL",
        "--exclude", "runs",
        "--exclude", "checkpoints",
        "--exclude", "*.log",
    ]

    if proxy:
        rsync_cmd = common_args + [
            "-e",
            _ssh_e(ssh_key, "22"),
            str(src_dir) + "/",
            f"{proxy}:{workdir}/oricli/oricli_core/models/",
        ]
        subprocess.run(rsync_cmd, check=True)
        return

    rsync_cmd = common_args + [
        "-e",
        _ssh_e(ssh_key, str(pod_port)),
        str(src_dir) + "/",
        f"root@{pod_ip}:{workdir}/oricli/oricli_core/models/",
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
            # Adjust command for proxy
            new_cmd = common_args + [
                "-e",
                _ssh_e(ssh_key, "22"),
                str(src_dir) + "/",
                f"{pod_id}-22@ssh.runpod.io:{workdir}/oricli/oricli_core/models/",
            ]
            proc = subprocess.run(new_cmd, check=False)
            if proc.returncode not in (0, 23):
                raise subprocess.CalledProcessError(proc.returncode, new_cmd)


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


def _display_cluster_status(pods: List[Dict]):
    """Display real-time status of all pods in the cluster."""
    if not USE_RICH:
        print("\n--- Cluster Status ---")
        for p in pods:
            print(f"Pod {p['id']}: {p.get('desiredStatus', 'UNKNOWN')}")
        return

    table = Table(title="OricliAlpha Cluster Orchestration Status", box=box.ROUNDED, border_style="cyan")
    table.add_column("Pod ID", style="magenta")
    table.add_column("Type", style="blue")
    table.add_column("IP Address", style="green")
    table.add_column("SSH Port", style="yellow")
    table.add_column("Status", style="bold")

    for i, p in enumerate(pods):
        role = "Master" if i == 0 else f"Worker-{i}"
        p_id = p["id"]
        runtime = p.get("runtime") or {}
        ports = runtime.get("ports") or []
        
        # Extract IP/Port for display
        ssh_port_info = next(
            (
                pt
                for pt in ports
                if (
                    pt.get("isIpPublic")
                    or not any(pt.get("ip", "").startswith(pref) for pref in ["10.", "172.", "192."])
                )
                and pt.get("privatePort") == 22
            ),
            None,
        )
        
        ip_str = "ssh.runpod.io" if not ssh_port_info else ssh_port_info["ip"]
        port_str = "22 (Proxy)" if not ssh_port_info else str(ssh_port_info["publicPort"])
        status = p.get("desiredStatus", "RUNNING")
        
        table.add_row(p_id, role, ip_str, port_str, status)

    console.print()
    console.print(table)
    console.print()


def _init_pod_worker(p, bridge, args):
    """Worker function to initialize a single pod in parallel."""
    p_id = p["id"]
    p_runtime = p.get("runtime") or {}
    p_ports = p_runtime.get("ports") or []
    
    # Find SSH port
    p_ssh_port_info = next(
        (
            pt
            for pt in p_ports
            if (
                pt.get("isIpPublic")
                or not any(pt.get("ip", "").startswith(pref) for pref in ["10.", "172.", "192."])
            )
            and pt.get("privatePort") == 22
        ),
        None,
    )
    
    p_ssh_proxy = f"{p_id}-22@ssh.runpod.io"
    if not p_ssh_port_info:
        p_ip = "ssh.runpod.io"
        p_port = 22
    else:
        p_ip = p_ssh_port_info["ip"]
        p_port = p_ssh_port_info["publicPort"]
        # If we have a direct IP, we only use proxy as a fallback if the user didn't provide one
        if args.ssh_proxy:
            p_ssh_proxy = args.ssh_proxy
    
    # Run initialization steps with high resilience
    # 1. Stabilize SSH
    setup_pod_env(p_ip, p_port, args.ssh_key, p_id, p_ssh_proxy, bridge=bridge)
    
    # 2. Cleanup & Sync (Wrap in internal retry for flaky proxy moments)
    max_init_retries = 3
    for attempt in range(max_init_retries):
        try:
            pre_sync_cleanup(p_ip, p_port, args.ssh_key, args.volume_mount_path, p_id, p_ssh_proxy)
            
            # If S3 is enabled, skip the fragile SSH-based rsync for code and models.
            # The 'ensure_oricli_installed' step will pull everything reliably from AWS.
            if not args.use_s3:
                sync_code(p_ip, p_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, p_id, p_ssh_proxy)
                
                if args.benchmark or args.internal_bench:
                    sync_models_to_pod(p_ip, p_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, p_id, p_ssh_proxy)
            else:
                _rich_log(f"Pod {p_id}: Skipping rsync (S3 strategy active).", "dim", "☁")
                
            ensure_oricli_installed(
                p_ip, p_port, args.ssh_key, args.volume_mount_path, p_id, p_ssh_proxy,
                s3_bucket=args.s3_bucket if args.use_s3 else None,
                s3_prefix=args.s3_prefix if args.use_s3 else None,
                s3_region=args.s3_region if args.use_s3 else None,
                s3_endpoint=args.s3_endpoint if args.use_s3 else None,
                force_reinstall=args.force_refresh,
                pip_debug=args.pip_debug,
                pip_stream=args.pip_stream,
                editable_install=args.editable_install,
                benchmark=args.benchmark,
                internal_bench=args.internal_bench
            )
            
            if args.auto_distill or (args.teacher_model and args.teacher_model != "phi4:latest") or not args.no_ollama:
                # Actually, let's make it even stricter: only install if distillation is active
                # or if specifically requested via NOT having --no-ollama.
                # But wait, --no-ollama defaults to False, so it currently ALWAYS runs.
                # Let's flip the logic to be more efficient.
                should_setup_ollama = args.auto_distill or (args.teacher_model and args.teacher_model != "phi4:latest")
                if should_setup_ollama:
                    setup_ollama(p_ip, p_port, args.ssh_key, args.teacher_model, args.ollama_model_dir, p_id, p_ssh_proxy)
                else:
                    _rich_log(f"Pod {p_id}: Skipping Ollama (no distillation active).", "dim", "ℹ")
            return p_id
        except Exception as e:
            if attempt < max_init_retries - 1:
                _rich_log(f"Pod {p_id} init attempt {attempt+1} failed ({e}). Retrying in 10s...", "yellow", "⚠")
                time.sleep(10)
            else:
                raise e


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
        f"Starting training on pod {pod_id}...", "bold green", "🏋", progress=progress, task_id=task_id
    )
    # Filter out any double-dash separators that might be caught in the middle of train_args
    train_args = [a for a in train_args if a != "--"]
    args_str = " ".join(train_args)
    env_prefix = "PYTHONUNBUFFERED=1 "
    # Force plain output for clusters to avoid interwoven progress bar mess
    if "--plain-output" in train_args or (args.cluster_size and args.cluster_size > 1):
        env_prefix += "MAVAIA_PLAIN_OUTPUT=1 "
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        env_prefix += f"HF_TOKEN='{hf_token}' "
    
    if "run_tests.py" in script_rel or "train" in script_rel:
        env_prefix += "MAVAIA_ENABLE_HEAVY_MODULES=true "

    python_cmd = f"cd {workdir}/oricli && export PYTHONPATH=. && PYTHON_EXE=$(if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi); {env_prefix}$PYTHON_EXE {script_rel} {args_str}"

    if proxy:
        ssh_cmd = _ssh_base(ssh_key, "22", proxy) + [python_cmd]
    else:
        ssh_cmd = _ssh_base(ssh_key, str(pod_port), f"root@{pod_ip}") + [python_cmd]

    # REAL-TIME PREFIXED OUTPUT
    # We use a subshell to prefix every line with the pod ID
    try:
        # Use a short version of pod ID for cleaner logs
        short_id = pod_id[:6] if pod_id else "node"
        color = "cyan" # Default
        
        # We can alternate colors for nodes if we want to be really fancy
        # but for now, simple prefixing is best
        prefix = f"[{short_id}] "
        
        process = subprocess.Popen(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        for line in process.stdout:
            # Print with the prefix
            if USE_RICH:
                # Handle potentially rich-formatted lines from the pod
                console.print(f"[bold {color}]{prefix}[/] {line.strip()}")
            else:
                print(f"{prefix}{line.strip()}")
                
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, ssh_cmd)
            
    except Exception as e:
        if pod_id and "255" in str(e):
            _rich_log(f"Pod {pod_id}: Connection dropped (255).", "yellow", "⚠")
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
import json
from pathlib import Path

# Force heavy modules for the health check
os.environ['MAVAIA_ENABLE_HEAVY_MODULES'] = 'true'
os.environ['MAVAIA_STRICT_INIT'] = 'true'

def check_fs():
    print("[HEALTH-FS] Checking filesystem for models...")
    base_dir = Path('/workspace/oricli/oricli_core/models/neural_text_generator')
    if not base_dir.exists():
        print(f"[HEALTH-FS] Base directory {{base_dir}} does NOT exist.")
        return
    
    print(f"[HEALTH-FS] Base directory {{base_dir}} exists.")
    print(f"[HEALTH-FS] Contents: {{os.listdir(base_dir)}}")
    
    latest_ptr = base_dir / "latest_run.txt"
    if latest_ptr.exists():
        raw = latest_ptr.read_text().strip()
        # The file may contain a full absolute local path (e.g. /Users/cass/.../runs/20260226_213048)
        # On the pod we only care about the run ID (the last path component)
        run_id = Path(raw).name
        print(f"[HEALTH-FS] latest_run.txt raw value: {{raw}}")
        print(f"[HEALTH-FS] Resolved run_id: {{run_id}}")
        run_dir = base_dir / "runs" / run_id
        if run_dir.exists():
            print(f"[HEALTH-FS] Run directory {{run_dir}} exists.")
            print(f"[HEALTH-FS] Run contents: {{os.listdir(run_dir)}}")
            ckpt_dir = run_dir / "checkpoints"
            if ckpt_dir.exists():
                print(f"[HEALTH-FS] Checkpoints: {{os.listdir(ckpt_dir)}}")
        else:
            print(f"[HEALTH-FS] Run directory {{run_dir}} NOT found.")

try:
    check_fs()
    
    print("[HEALTH] Checking torch and CUDA...")
    import torch
    print(f"[HEALTH] Torch version: {{torch.__version__}}")
    print(f"[HEALTH] CUDA available: {{torch.cuda.is_available()}}")
    if torch.cuda.is_available():
        print(f"[HEALTH] GPU: {{torch.cuda.get_device_name(0)}}")
    
    print("[HEALTH] Discovering modules (MAVAIA_ENABLE_HEAVY_MODULES=true)...")
    from oricli_core.brain.registry import ModuleRegistry
    ModuleRegistry.discover_modules(verbose=False)
    
    print("[HEALTH] Retrieving cognitive_generator...")
    cg = ModuleRegistry.get_module("cognitive_generator")
    if not cg:
        print("[HEALTH] ERROR: Could not find 'cognitive_generator' in registry.")
        sys.exit(1)
        
    print("[HEALTH] Attempting tiny generation...")
    res = cg.execute(
        operation="generate_response",
        params={{
            "input": "Hello",
            "max_tokens": 5
        }}
    )
    
    text = res.get('text', '')
    print(f"[HEALTH] Result text: '{{text}}'")
    
    # Check if we got the 'analyzing' placeholder
    if "I'm analyzing your request" in text:
        print("[HEALTH] WARNING: Placeholder detected. Models are NOT loaded.")
        # If models are missing, try to report why NTG failed
        ntg = ModuleRegistry.get_module("neural_text_generator")
        if ntg:
            print(f"[HEALTH] NTG model_dir: {{ntg.model_dir}}")
            print(f"[HEALTH] NTG char_model: {{ntg.char_model is not None}}")
            # Try to load explicitly
            load_res = ntg.execute("load_model", {{"model_type": "character"}})
            print(f"[HEALTH] Explicit load result: {{load_res}}")
        sys.exit(2)
    else:
        print("[HEALTH] SUCCESS: Real model output detected.")
        sys.exit(0)

except Exception as e:
    print(f"[HEALTH] ERROR: {{str(e)}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
    
    remote_cmd = f"""
cd {workdir}/oricli && \
PYTHON_EXE=$(if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi); \
cat << 'EOF' > model_health_check.py
{health_script}
EOF
PYTHONPATH=. $PYTHON_EXE model_health_check.py
"""

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
    # Filter out any double-dash separators that might be caught in the middle of bench_args
    bench_args = [a for a in bench_args if a != "--"]
    
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

    log_path = f"{workdir}/oricli/server.log"

    # Build a robust single script to run on the pod
    remote_script = f"""
set -e
export MAVAIA_ENABLE_HEAVY_MODULES=true

# Cleanup old logs and temporary data to save disk space
echo "[DEBUG] Cleaning up old logs and snapshots..."
find {workdir}/oricli -name "*.log" -type f -mtime +1 -delete 2>/dev/null || true
rm -rf {workdir}/oricli/oricli_core/models/neural_text_generator/snapshots/* 2>/dev/null || true

PYTHON_EXE=$(if [ -f {workdir}/oricli/.venv/bin/python ]; then echo {workdir}/oricli/.venv/bin/python; else echo python3; fi)
echo "[DEBUG] Using Python: $PYTHON_EXE"

cd {workdir}/oricli
echo "[DEBUG] Starting API server..."
{env_prefix} PYTHONPATH=. nohup $PYTHON_EXE -m oricli_core.api.server --host 127.0.0.1 --port 8000 --no-auto-port > {log_path} 2>&1 &
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

cd {workdir}/oricli/LiveBench/livebench
echo "[DEBUG] Cleaning old benchmark data..."
# Archive existing results instead of deleting them to avoid data loss on partial runs
rm -rf data_old/
if [ -d data/ ]; then mv data/ data_old/; fi
rm -f oricli_result.json livebench_results_*.json

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
            "rsync", "-rlptz",
            "-e", _ssh_e(ssh_key, "22"),
            f"{proxy}:{workdir}/oricli/oricli_core/models/neural_text_generator/",
            str(dest_dir) + "/",
        ]
        subprocess.run(scp_cmd, check=True)
        return

    scp_cmd = [
        "rsync", "-rlptz",
        "-e", _ssh_e(ssh_key, str(pod_port)),
        f"root@{pod_ip}:{workdir}/oricli/oricli_core/models/neural_text_generator/",
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
            proxy_cmd = [
                "rsync", "-rlptz",
                "-e", _ssh_e(ssh_key, "22"),
                f"{pod_id}-22@ssh.runpod.io:{workdir}/oricli/oricli_core/models/neural_text_generator/",
                str(dest_dir) + "/",
            ]
            proc = subprocess.run(proxy_cmd, check=False)
            if proc.returncode != 0 and proc.returncode != 23:
                raise subprocess.CalledProcessError(proc.returncode, proxy_cmd)
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

    remote_base = f"{workdir}/oricli/LiveBench/livebench"
    
    def run_sync(host_str, port_str):
        ssh_cmd = _ssh_e(ssh_key, port_str)
        # 1. Pull root level JSON results
        sync_root_cmd = [
            "rsync", "-rlptz",
            "-e", ssh_cmd,
            "--include=livebench_results_*.json",
            "--include=oricli_result.json",
            "--exclude=*",
            f"{host_str}:{remote_base}/",
            str(local_path) + "/",
        ]
        # 2. Pull the entire data directory
        sync_data_cmd = [
            "rsync", "-rlptz",
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

    dest_dir = local_path / "oricli_core" / "evaluation" / "results"
    dest_dir.mkdir(parents=True, exist_ok=True)

    def run_sync(host_str, port_str):
        ssh_cmd = _ssh_e(ssh_key, port_str)
        sync_cmd = [
            "rsync", "-rlptz",
            "-e", ssh_cmd,
            f"{host_str}:{workdir}/oricli/oricli_core/evaluation/results/",
            str(dest_dir) + "/",
        ]
        # Also ensure any root-level report HTMLs are caught
        sync_html_cmd = [
            "rsync", "-rlptz",
            "--include=report_*.html",
            "--exclude=*",
            "-e", ssh_cmd,
            f"{host_str}:{workdir}/oricli/oricli_core/evaluation/results/",
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
    (dest_dir / "models").mkdir(parents=True, exist_ok=True)
    (dest_dir / "data_cache").mkdir(parents=True, exist_ok=True)

    if proxy:
        rsync_cmd = [
            "rsync", "-rlptz",
            "-e", _ssh_e(ssh_key, "22"),
            f"{proxy}:{workdir}/oricli/oricli_core/models/neural_text_generator/",
            str(dest_dir / "models") + "/",
        ]
        cache_cmd = [
            "rsync", "-rlptz",
            "-e", _ssh_e(ssh_key, "22"),
            f"{proxy}:{workdir}/oricli/oricli_core/data/",
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
        "rsync", "-rlptz",
        "-e", _ssh_e(ssh_key, str(pod_port)),
        f"root@{pod_ip}:{workdir}/oricli/oricli_core/models/neural_text_generator/",
        str(dest_dir / "models") + "/",
    ]
    cache_cmd = [
        "rsync", "-rlptz",
        "-e", _ssh_e(ssh_key, str(pod_port)),
        f"root@{pod_ip}:{workdir}/oricli/oricli_core/data/",
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
            proxy_rsync_cmd = [
                "rsync", "-rlptz",
                "-e", _ssh_e(ssh_key, "22"),
                f"{pod_id}-22@ssh.runpod.io:{workdir}/oricli/oricli_core/models/neural_text_generator/",
                str(dest_dir / "models") + "/",
            ]
            proxy_cache_cmd = [
                "rsync", "-rlptz",
                "-e", _ssh_e(ssh_key, "22"),
                f"{pod_id}-22@ssh.runpod.io:{workdir}/oricli/oricli_core/data/",
                str(dest_dir / "data_cache") + "/",
            ]
            for cmd in (proxy_rsync_cmd, proxy_cache_cmd):
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

    # BLACKWELL EXCLUSION: Only excluding smaller PRO cards that definitely lack VRAM headroom
    incompatible_keywords = ["PRO 4500", "PRO 5000"]

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

    # BALANCED HEADROOM SCORING: Prioritize high-VRAM options with reasonable cost
    def _score(gpu):
        price = gpu["securePrice"] + storage_overhead
        vram = gpu["memoryInGb"]
        # Bias towards VRAM: (VRAM^1.5) / Price
        # This makes an 80GB card significantly more attractive than a 24GB card 
        # even if it costs more per GB, prioritizing stability for large models.
        return (vram ** 1.5) / price

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
            "name": "oricli_distill",
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
            "name": "oricli_logic",
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
            "name": "oricli_tone",
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
        f"cd {workdir}/oricli && "
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
        ensure_oricli_installed(
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
        f"cd {workdir}/oricli; "
        f"SNAP_DIR={workdir}/oricli/oricli_core/models/neural_text_generator/snapshots/{{ts}}; "
        'mkdir -p "$SNAP_DIR"; '
        'cp -a oricli_core/models/neural_text_generator/checkpoints "$SNAP_DIR" 2>/dev/null || true; '
        'cp -a oricli_core/models/neural_text_generator/runs "$SNAP_DIR" 2>/dev/null || true; '
        'cp -a oricli_core/models/neural_text_generator/latest_run.txt "$SNAP_DIR" 2>/dev/null || true; '
        'cp -a oricli_core/models/neural_text_generator/*.keras "$SNAP_DIR" 2>/dev/null || true; '
        'cp -a oricli_core/models/neural_text_generator/*.json "$SNAP_DIR" 2>/dev/null || true; '
        'echo "snapshot_saved"'
    ).format(ts=timestamp)

    if proxy:
        _run_ssh(ssh_key, None, 22, pod_id, proxy, snapshot_cmd, progress=progress, task_id=task_id)
        return

    _run_ssh(ssh_key, pod_ip, pod_port, pod_id, proxy, snapshot_cmd, progress=progress, task_id=task_id)


def _resolve_topic_datasets(topics: List[str]) -> Dict[str, str]:
    """Search for best-matching datasets for a list of topics."""
    _rich_log(f"Resolving datasets for {len(topics)} topics...", "cyan", "🔍")
    from oricli_core.data.search import DatasetSearch
    
    search_service = DatasetSearch()
    topic_map = {}
    
    for topic in topics:
        _rich_log(f"Searching for '{topic}'...", "dim", "🔎")
        results = search_service.search_all(topic, limit_per_source=3)
        # Filter out gated datasets for now
        public_results = [r for r in results if not r.gated]
        
        if public_results:
            best_match = public_results[0]
            topic_map[topic] = best_match.id
            _rich_log(f"Topic '{topic}' -> {best_match.source}:{best_match.name}", "green", "💎")
        else:
            _rich_log(f"Error: No public datasets found for topic '{topic}'.", "red", "✗")
            sys.exit(1)
            
    return topic_map


def register_trained_adapters(local_path: Path):
    """Scan for trained adapters and register them with the AdapterRouter."""
    _rich_log("Scanning for new adapters to register with OricliAlpha Core...", "cyan", "🛰")
    
    # Standard location for remote model weights
    remote_models_dir = local_path / "models" / "neural_text_generator_remote"
    if not remote_models_dir.exists():
        return

    # 1. Collect adapters to register
    new_adapters = {} # adapter_name -> full_path
    
    for adapter_path in remote_models_dir.iterdir():
        if adapter_path.is_dir() and adapter_path.name.startswith("adapter_"):
            # Check if it has LoRA weights
            if (adapter_path / "adapter_config.json").exists():
                adapter_name = adapter_path.name.replace("adapter_", "")
                new_adapters[adapter_name] = str(adapter_path.absolute())

    # Also check the main transformer checkpoint dir (base LoRA if not named)
    transformer_dir = remote_models_dir / "transformer"
    if transformer_dir.exists() and (transformer_dir / "adapter_config.json").exists():
        new_adapters["primary_lora"] = str(transformer_dir.absolute())

    if not new_adapters:
        _rich_log("No new adapters found to register.", "dim", "ℹ")
        return

    # 2. Try to register via OricliAlphaClient (Preferred)
    try:
        from oricli_core.client import OricliAlphaClient
        client = OricliAlphaClient()
        
        for name, path in new_adapters.items():
            _rich_log(f"Registering adapter '{name}' via client...", "dim", "🛰")
            try:
                client.brain.adapter_router.register_intent(
                    intent=name,
                    adapter_id=path
                )
                _rich_log(f"Successfully registered adapter '{name}' via client.", "green", "✓")
            except Exception as e:
                _rich_log(f"Failed to register adapter {name} via client: {e}", "yellow", "⚠")
        return
    except Exception as e:
        _rich_log(f"OricliAlphaClient unavailable for registration ({e}). Falling back to direct config update.", "yellow", "⚠")

    # 3. Direct JSON Fallback (Resilient Path)
    config_path = local_path / "oricli_core" / "brain" / "modules" / "adapter_router_config.json"
    
    try:
        # Load existing or create new
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"routing_table": {}, "intent_labels": ["general", "math", "coding", "creative", "logic"], "config": {}}
            
        routing_table = data.get("routing_table", {})
        intent_labels = data.get("intent_labels", [])
        
        updated = False
        for name, path in new_adapters.items():
            if routing_table.get(name) != path:
                routing_table[name] = path
                if name not in intent_labels:
                    intent_labels.append(name)
                updated = True
                _rich_log(f"Registered adapter '{name}' in config file.", "green", "✓")
        
        if updated:
            data["routing_table"] = routing_table
            data["intent_labels"] = intent_labels
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            _rich_log(f"Updated AdapterRouter config file at {config_path.name}", "bold green", "✨")
        else:
            _rich_log("No changes needed to config file.", "dim", "ℹ")
            
    except Exception as e:
        _rich_log(f"CRITICAL: Failed to update AdapterRouter config directly: {e}", "red", "✗")


def main():
    parser = argparse.ArgumentParser(description="OricliAlpha RunPod Training Bridge")
    parser.add_argument("--pod-id", help="Existing pod ID to use")
    parser.add_argument("--gpu", default=None, help="GPU type for new pod (defaults to auto-selection)")
    parser.add_argument(
        "--image",
        default="runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04",
        help="Container image",
    )
    parser.add_argument("--template", help="RunPod Template ID (overrides --image if provided)")
    parser.add_argument(
        "--ssh-key",
        default=str(Path.home() / ".ssh" / "oricli_key"),
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
        "--cluster-size",
        type=int,
        default=1,
        help="Number of pods to launch in an Instant Cluster (max 10)",
    )
    parser.add_argument(
        "--vpc",
        action="store_true",
        default=True,
        help="Enable Global Networking (VPC) for cluster pods (default: True)",
    )
    parser.add_argument(
        "--topics",
        type=str,
        nargs="+",
        help="List of training topics for smart cluster allocation (e.g. 'cybersecurity' 'biology')",
    )
    parser.add_argument(
        "--pods-per-topic",
        type=int,
        default=1,
        help="Number of pods to assign to each topic in the cluster (default: 1)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-manage: terminate active pods, pick best GPU within price range, and train",
    )
    parser.add_argument(
        "--max-price", type=float, default=2.50, help="Max hourly price for auto GPU selection"
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
    parser.add_argument("--s3-bucket", default=os.environ.get("AWS_BUCKET_NAME", "sxzm7zw9w9"), help="S3 bucket name")
    parser.add_argument("--s3-region", default=os.environ.get("AWS_REGION", "eu-ro-1"), help="S3 region")
    parser.add_argument(
        "--s3-endpoint", 
        default=os.environ.get("MAVAIA_S3_ENDPOINT", "https://s3api-eu-ro-1.runpod.io"), 
        help="S3 endpoint URL"
    )
    parser.add_argument("--s3-prefix", default="oricli", help="S3 prefix for repo/workspace sync")
    parser.add_argument(
        "--s3-ollama-prefix", default="ollama", help="S3 prefix for Ollama model storage"
    )
    parser.add_argument(
        "--upload-to-s3",
        action="store_true",
        help="Upload local project root to S3 before cluster creation (Local+S3 strategy)",
    )
    parser.add_argument(
        "--use-s3",
        action="store_true",
        default=False,
        help="Use S3 for project synchronization (mandatory for Local+S3 strategy)",
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
        help="Attach an existing RunPod network volume by ID (optional if using --upload-to-s3)",
    )
    parser.add_argument(
        "--alias", default="oricli_train", help="Alias for pod name (default: oricli_train)"
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
        "--time-limit",
        type=int,
        help="Maximum training time in SECONDS (Sentinel hard-stop)",
    )
    parser.add_argument(
        "--dynamic-threshold",
        action="store_true",
        help="Enable adaptive plateau detection (Sentinel)",
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
        help="Disable editable install for oricli.",
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
        help="Run OricliAlpha's internal knowledge benchmark (run_tests.py --internal-bench) on the pod.",
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
        "--find-elective",
        "--find-stage",
        type=str,
        dest="find_elective",
        help="Search for a dataset based on a phrase/category and train it as an elective",
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Perform dataset discovery or stage addition without starting training",
    )
    parser.add_argument(
        "--add-stage",
        type=str,
        help="Search for a dataset and permanently add it as a new curriculum stage",
    )
    parser.add_argument(
        "--auto-select",
        action="store_true",
        help="Auto-select the best match for --find-elective without interaction",
    )
    parser.add_argument(
        "--lora",
        action="store_true",
        help="Enable LoRA fine-tuning for non-curriculum training",
    )
    parser.add_argument(
        "--adapter-name",
        type=str,
        help="Custom name for the trained LoRA adapter (elective name)",
    )
    parser.add_argument(
        "--train-rfal",
        action="store_true",
        help="Run RFAL DPO alignment training using collected rfal_lessons.jsonl",
    )
    parser.add_argument(
        "--train-jit",
        action="store_true",
        help="Run JIT knowledge absorption training using verified search facts",
    )
    parser.add_argument(
        "--train-tool-bench",
        action="store_true",
        help="Run Tool-Efficacy training using collected corrections",
    )
    parser.add_argument(
        "--execute-goal",
        type=str,
        help="Execute a specific sovereign goal by ID (Long Horizon Persistence)",
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

    # Pre-initialize price range for use in auto-selection fallbacks
    min_price = float(args.min_price)
    max_price = float(args.max_price)
    if args.auto_price_range:
        try:
            min_str, max_str = args.auto_price_range.split("-", 1)
            min_price = float(min_str.strip())
            max_price = float(max_str.strip())
        except Exception:
            pass

    if args.list_stages:
        subprocess.run([sys.executable, "scripts/train_curriculum.py", "--list-stages"])
        return 0

    # Refresh API Key from environment (after load_dotenv)
    global RUNPOD_API_KEY
    RUNPOD_API_KEY = os.environ.get("OricliAlpha_Key")

    if not RUNPOD_API_KEY:
        _rich_log("Error: OricliAlpha_Key not found in .env", "red", "✗")
        sys.exit(1)

    _rich_log(f"Initializing RunPod Bridge (API: {RUNPOD_ENDPOINT})...", "cyan", "🚀")
    bridge = RunPodBridge(RUNPOD_API_KEY)
    
    # Pre-flight auth check
    balance = bridge.get_balance()
    if balance is None:
        _rich_log("CRITICAL: Failed to authorize with RunPod API. Check your OricliAlpha_Key in .env", "red", "✗")
        sys.exit(1)
    _rich_log(f"Authorized! Account Balance: ${balance:.2f}", "green", "✓")

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
                            if str(p.get("name", "")).startswith("oricli_"):
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
        "AWS_BUCKET_NAME": args.s3_bucket,
        "MAVAIA_S3_ENDPOINT": args.s3_endpoint,
        "MAVAIA_S3_PREFIX": args.s3_prefix,
        "MAVAIA_CLUSTER_SYNC": "true" if args.cluster_size > 1 else "false",
        "KAGGLE_USERNAME": os.environ.get("KAGGLE_USERNAME"),
        "KAGGLE_KEY": os.environ.get("KAGGLE_KEY"),
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
        model_name=details.get("model_name"),
        is_quantized=details.get("is_quantized", False),
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

    # TOPIC RESOLUTION & CLUSTER SCALING
    topic_dataset_map = {}
    if args.topics:
        topic_dataset_map = _resolve_topic_datasets(args.topics)
        # Automatic cluster sizing based on topics
        required_pods = len(args.topics) * args.pods_per_topic
        if args.cluster_size < required_pods:
            _rich_log(f"Auto-Scaling Cluster: {len(args.topics)} topics x {args.pods_per_topic} pods = {required_pods} pods.", "cyan", "📈")
            args.cluster_size = required_pods
        
        # Topic-based allocation requires auto mode or cluster mode
        if not args.pod_id and not args.fleet:
            args.auto = True

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

    # Determine if we should use auto-selection or specific GPU
    # If the user passed --auto, it ALWAYS takes precedence.
    # If they passed --gpu AND NOT --auto, we use their specific GPU.
    # Otherwise, if --gpu is the default (None) and --auto is False, we might need a default or error.
    
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
            if str(p.get("name", "")).startswith("oricli_"):
                _rich_log(f"Terminating existing pod {p['id']} ({p.get('name')})", "yellow", "💥")
                bridge.terminate_pod(p["id"])

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
            gpu_id = best_gpu.get("name") or best_gpu.get("id")
            auto_candidate_gpus = filtered_gpus
            _rich_log(f"Auto-selected best match: {best_gpu['displayName']}", "green", "✓")
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
        incompatible_keywords = ["PRO 4500", "PRO 5000"]
        if args.gpu and any(kw in args.gpu for kw in incompatible_keywords):
            _rich_log(
                f"GPU '{args.gpu}' is known to be incompatible with our current software stack.",
                "red",
                "✗",
            )
            sys.exit(1)

        gpu_ids = [g["id"] for g in gpu_types]
        gpu_names = [g.get("name") for g in gpu_types if g.get("name")]

        gpu_id = None
        if args.gpu and args.gpu in gpu_ids:
            gpu_id = args.gpu
        elif args.gpu and args.gpu in gpu_names:
            gpu_id = args.gpu
        elif args.gpu:
            # Fallback mapping
            mapped_id = args.gpu.lower().replace(" ", "_").replace("nvidia_", "")
            if mapped_id in gpu_ids:
                gpu_id = mapped_id
            elif f"gpu_{mapped_id}" in gpu_ids:
                gpu_id = f"gpu_{mapped_id}"
            else:
                _rich_log(
                    f"Warning: GPU '{args.gpu}' not found in available inventory. Falling back to --auto selection...",
                    "yellow",
                    "⚠",
                )
                # FORCE AUTO MODE
                args.auto = True
                filtered_gpus = _select_candidate_gpus(bridge, min_price, max_price, args.min_vram)
                if filtered_gpus:
                    best_gpu = filtered_gpus[0]
                    gpu_id = best_gpu.get("name") or best_gpu.get("id")
                    auto_candidate_gpus = filtered_gpus
                    _rich_log(f"Auto-selected replacement: {best_gpu['displayName']}", "green", "✓")
                else:
                    _rich_log(f"Auto-selection failed: No available GPUs matching {args.min_vram}GB VRAM / ${max_price}/hr", "red", "✗")
                    sys.exit(1)
        else:
            # No GPU requested and not in auto mode? 
            # This should ideally not happen due to the logic above, but let's be safe.
            _rich_log("No GPU specified and auto-selection not triggered correctly. Forcing auto-selection...", "yellow", "⚠")
            args.auto = True
            filtered_gpus = _select_candidate_gpus(bridge, min_price, max_price, args.min_vram)
            if filtered_gpus:
                best_gpu = filtered_gpus[0]
                gpu_id = best_gpu.get("name") or best_gpu.get("id")
                auto_candidate_gpus = filtered_gpus
                _rich_log(f"Auto-selected best match: {best_gpu['displayName']}", "green", "✓")
            else:
                _rich_log(f"Auto-selection failed: No available GPUs matching requirements.", "red", "✗")
                sys.exit(1)

    if args.upload_to_s3 or args.use_s3:
        if not check_s3_credentials():
            sys.exit(1)

    if args.upload_to_s3:
        _rich_log("Upload to S3 requested. Syncing local project root...", "cyan", "📦")
        s3_sync_local_to_bucket(
            REPO_ROOT,
            args.s3_bucket,
            args.s3_prefix,
            args.s3_region,
            args.s3_endpoint,
        )
        # Ensure use_s3 is True for subsequent pod initialization
        args.use_s3 = True

    elif args.use_s3:
        # If use_s3 is manually set without upload, we assume data is already there 
        # but we might still want to refresh it if it's the first run
        _rich_log("S3 sync enabled. Using existing S3 archive for pod initialization.", "cyan", "☁")

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
                    if isinstance(candidate, dict):
                        # For clusters, the 'name' field typically holds the short slug (e.g. gpu-nvidia-rtx-6000-ada)
                        candidate_id = candidate.get("name") or candidate.get("id")
                        candidate_display = candidate.get("displayName") or candidate_id
                    else:
                        candidate_id = candidate
                        candidate_display = candidate

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

                    # 1. AVAILABILITY PRE-CHECK (STOCK SENSITIVE)
                    availability_snapshot = bridge.get_gpu_types_with_availability()
                    candidate_info = next(
                        (g for g in availability_snapshot if g.get("id") == candidate_id or g.get("name") == candidate_id), None
                    )
                    
                    if candidate_info is not None:
                        # Check for enough stock for the whole cluster
                        if not bridge.gpu_is_available(candidate_info, required_count=args.cluster_size):
                            stock_status = candidate_info.get("stockStatus", "UNKNOWN")
                            _rich_log(
                                f"Skipping {candidate_display}: Insufficient stock for {args.cluster_size} pods (Status: {stock_status}).",
                                "yellow",
                                "⏳",
                                progress=progress,
                                task_id=pod_task,
                            )
                            continue

                    # 2. PROCEED TO CREATION
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

                    pod_name = args.alias or "oricli_train"
                    if args.cluster_size > 1:
                        _rich_log(f"Orchestrating Virtual Cluster of {args.cluster_size} pods...", "cyan", "🪄")
                        
                        pods = []
                        import concurrent.futures
                        
                        def _launch_single_pod(idx):
                            suffix = f"_{idx+1}"
                            member_name = pod_name + suffix
                            
                            _rich_log(f"Launching virtual cluster member {idx+1}/{args.cluster_size}: {member_name}", "dim", "🚀")
                            
                            # Determine cloud type based on GPU candidate
                            c_type = "SECURE" if candidate.get("securePrice") else "COMMUNITY"
                            
                            res = bridge.create_pod(
                                name=member_name,
                                gpu_type_id=candidate_id,
                                template_id=args.template,
                                image=current_image,
                                ssh_key_value=args.ssh_key_value,
                                data_center_id=args.data_center,
                                volume_id=args.volume_id if args.volume_id else None,
                                volume_mount_path=args.volume_mount_path,
                                env=pod_env,
                                cloud_type=c_type
                            )
                            return res

                        with concurrent.futures.ThreadPoolExecutor(max_workers=args.cluster_size) as executor:
                            launch_futures = [executor.submit(_launch_single_pod, i) for i in range(args.cluster_size)]
                            for f in concurrent.futures.as_completed(launch_futures):
                                try:
                                    p_res = f.result()
                                    if p_res:
                                        pods.append(p_res)
                                except Exception as e:
                                    _rich_log(f"Virtual cluster member launch failed: {e}", "red", "✗")

                        if len(pods) < args.cluster_size:
                            _rich_log(f"Only {len(pods)}/{args.cluster_size} pods launched. Retrying next candidate...", "yellow", "⚠")
                            # Cleanup partial cluster
                            for p in pods:
                                try:
                                    bridge.terminate_pod(p["id"])
                                except Exception:
                                    pass
                            continue
                        
                        _rich_log(f"Virtual Cluster of {len(pods)} pods provisioned! Waiting for constituent pods...", "cyan", "⏳")
                        
                        # Wait for all pods to have runtime data
                        cluster_ready = False
                        while True:
                            all_ready = True
                            fresh_pods = bridge.get_pods()
                            cluster_ids = {p["id"] for p in pods}
                            
                            current_cluster_pods = [p for p in fresh_pods if p["id"] in cluster_ids]
                            
                            if len(current_cluster_pods) < args.cluster_size:
                                all_ready = False
                            else:
                                for cp in current_cluster_pods:
                                    runtime = cp.get("runtime")
                                    if not runtime or not runtime.get("ports") or not runtime.get("uptimeInSeconds", 0) > 0:
                                        all_ready = False
                                        break
                            
                            if all_ready and len(current_cluster_pods) == args.cluster_size:
                                pods = current_cluster_pods
                                _rich_log(f"All {args.cluster_size} pods in virtual cluster are ready!", "bold green", "✓")
                                cluster_ready = True
                                break
                            
                            time.sleep(10)
                        
                        if cluster_ready:
                            # Set first pod as 'pod' for any remaining single-pod logic
                            pod = pods[0]
                            break
                    else:
                        # Single pod logic (existing)
                        pod_result = bridge.create_pod(
                            name=pod_name,
                            gpu_type_id=candidate_id,
                            template_id=args.template,
                            image=current_image,
                            ssh_key_value=args.ssh_key_value,
                            data_center_id=args.data_center,
                            volume_id=args.volume_id if args.volume_id else None,
                            volume_mount_path=args.volume_mount_path,
                            env=pod_env,
                        )
                        if not pod_result:
                            # If auto-mode, continue to next candidate
                            continue

                        pod_id = pod_result["id"]
                        progress.update(pod_task, description=f"Found pod {pod_id}! Launching...")

                        poll_start = time.time()
                        while True:
                            all_pods = bridge.get_pods()
                            pod = next((p for p in all_pods if p["id"] == pod_id), None)
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
                        if pod:
                            pods = [pod]
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
        # Initialization phase (parallel across all pods in cluster)
        import concurrent.futures

        _rich_log(f"Initializing {len(pods)} pod(s) in parallel...", "cyan", "⚡")
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(pods)) as executor:
            futures = [executor.submit(_init_pod_worker, p, bridge, args) for p in pods]
            for future in concurrent.futures.as_completed(futures):
                try:
                    p_id = future.result()
                    _rich_log(f"Pod {p_id} fully initialized.", "green", "✓")
                except Exception as e:
                    _rich_log(f"Pod initialization failed: {e}", "red", "✗")
                    failed = True

        if failed:
            _rich_log("One or more pods failed to initialize. Terminating...", "red", "✗")
            
            # Re-fetch pods to see what's actually still there
            try:
                active_pods = bridge.get_pods()
                active_ids = {ap["id"] for ap in active_pods}
            except Exception:
                active_ids = set()

            # For virtual clusters, we always terminate the specific list of pods
            for p in pods:
                if p["id"] in active_ids:
                    _rich_log(f"Terminating member {p['id']}...", "dim")
                    bridge.terminate_pod(p["id"])
            sys.exit(1)

        # Re-fetch fresh pod info to ensure we have final runtime/port data for all pods
        fresh_pods_list = bridge.get_pods()
        cluster_ids = {p["id"] for p in pods}
        pods = [p for p in fresh_pods_list if p["id"] in cluster_ids]
        
        # Display final cluster state
        _display_cluster_status(pods)
        
        # Designate master pod (first in list)
        pod = pods[0]
        runtime_info = pod.get("runtime") or {}
        ports_info = runtime_info.get("ports") or []
        ssh_port_info = next(
            (
                pt
                for pt in ports_info
                if (
                    pt.get("isIpPublic")
                    or not any(pt.get("ip", "").startswith(pref) for pref in ["10.", "172.", "192."])
                )
                and pt.get("privatePort") == 22
            ),
            None,
        )
        
        if not ssh_port_info:
            pod_ip = "ssh.runpod.io"
            pod_port = 22
            args.ssh_proxy = f"{pod['id']}-22@ssh.runpod.io"
        else:
            pod_ip = ssh_port_info["ip"]
            pod_port = ssh_port_info["publicPort"]

        # After initialization, we exit the Progress block and resume normal scrolling logs for training
        if not args.no_watchdog:
            interval_minutes = float(args.watchdog_minutes or 0.0)
            if interval_minutes > 0:
                watchdog_stop = threading.Event()

                def _watchdog_loop():
                    interval_s = max(60.0, interval_minutes * 60.0)
                    while not watchdog_stop.wait(interval_s):
                        try:
                            # 1. Cluster Health Check
                            current_active_pods = bridge.get_pods()
                            active_ids = {p["id"] for p in current_active_pods}
                            
                            for p in pods:
                                if p["id"] not in active_ids:
                                    _rich_log(f"Watchdog: Pod {p['id']} is missing! Triggering emergency exit.", "red", "🚨")
                                    os.kill(os.getpid(), signal.SIGINT)
                                    return

                            # 2. S3-Based Sync (For ALL pods in cluster)
                            if args.use_s3:
                                _rich_log(f"Watchdog: S3 sync for {len(pods)} pod(s)...", "cyan", "🐕")
                                for p in pods:
                                    # Snapshot first (remotely tar logs/checkpoints)
                                    # Note: Using p_id specific proxy if possible
                                    p_proxy = f"{p['id']}-22@ssh.runpod.io"
                                    
                                    # Snapshot
                                    remote_snapshot(
                                        "ssh.runpod.io", 22, args.ssh_key, args.volume_mount_path, p["id"], p_proxy
                                    )
                                    # Push to S3 (specific to each pod's prefix)
                                    s3_sync_pod(
                                        "ssh.runpod.io", 22, args.ssh_key, 
                                        args.s3_bucket, f"{args.s3_prefix}/{p['id']}", 
                                        args.s3_region, args.s3_endpoint, "push",
                                        pod_id=p["id"], proxy=p_proxy
                                    )

                            # 3. Master Node Sync (Local)
                            _rich_log("Watchdog: snapshot + sync (Master)", "cyan", "🐕")
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
                default_model = "oricli_core/models/neural_text_generator"
                latest_run_ptr = (
                    REPO_ROOT
                    / "oricli_core"
                    / "models"
                    / "neural_text_generator"
                    / "latest_run.txt"
                )
                if latest_run_ptr.exists():
                    try:
                        raw = latest_run_ptr.read_text().strip()
                        # File stores either:
                        #   - Just the run ID: "20260226_213048"  (new format)
                        #   - Full abs local path (old format, backward compat)
                        # In both cases we want just the basename (run ID).
                        run_id = Path(raw).name
                        if run_id:
                            default_model = f"oricli_core/models/neural_text_generator/runs/{run_id}"
                    except Exception:
                        pass

                # Make path absolute for pod context since we cd into LiveBench/livebench
                if not default_model.startswith("/"):
                    default_model = f"{args.volume_mount_path}/oricli/{default_model}"

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
                bench_args.extend(["--model-display-name", "oricli"])

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
                    src=f"{args.volume_mount_path}/oricli",
                )
        elif args.internal_bench:
            _rich_log("Starting OricliAlpha Internal Knowledge Benchmark...", "bold green", "🚀")
            
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
            if args.lora:
                train_args.append("--lora")
            if args.adapter_name:
                train_args.extend(["--adapter-name", args.adapter_name])
            if args.time_limit:
                train_args.extend(["--time-limit", str(args.time_limit)])
            if args.dynamic_threshold:
                train_args.append("--dynamic-threshold")
            
            # Forward Cluster Networking details if applicable
            if args.cluster_size > 1:
                # The master pod needs to know how many nodes are in the cluster
                # and its own internal address for coordination.
                if "--nnodes" not in train_args:
                    train_args.extend(["--nnodes", str(args.cluster_size)])
                
                # Internal DNS for RunPod VPC is usually <pod_id>.runpod.internal
                master_internal_addr = f"{pods[0]['id']}.runpod.internal"
                if "--master-addr" not in train_args:
                    train_args.extend(["--master-addr", master_internal_addr])
                
                _rich_log(f"Cluster Config: Nodes={args.cluster_size}, Master={master_internal_addr}", "dim", "🌐")

            if args.train_rfal:
                _rich_log("RFAL Alignment Pass: Training on collected lessons", "bold cyan", "🎓")
                train_args.append("--dpo")
                train_args.extend(["--dpo-data", "oricli_core/data/rfal_lessons.jsonl"])
                if "--adapter-name" not in train_args and not args.adapter_name:
                    train_args.extend(["--adapter-name", "rfal_alignment"])

            if args.train_jit:
                _rich_log("JIT Knowledge Absorption: Learning from verified search results", "bold yellow", "🧠")
                # JIT uses standard SFT instead of DPO for fast fact ingestion
                train_args.extend(["--source", "local", "--book-ids", "oricli_core/data/jit_absorption.jsonl"])
                if "--adapter-name" not in train_args and not args.adapter_name:
                    train_args.extend(["--adapter-name", "jit_knowledge_base"])
                if "--epochs" not in train_args:
                    train_args.extend(["--epochs", "2"]) # Higher focus for small data

            if args.train_tool_bench:
                _rich_log("Tool-Efficacy Tuning: Learning from benchmark mistakes", "bold magenta", "🛠")
                # Tool bench uses DPO to learn specifically what NOT to do
                train_args.append("--dpo")
                train_args.extend(["--dpo-data", "oricli_core/data/tool_corrections.jsonl"])
                if "--adapter-name" not in train_args and not args.adapter_name:
                    train_args.extend(["--adapter-name", "tool_efficacy_v1"])

            if args.execute_goal:
                _rich_log(f"Sovereign Goal Execution: Orchestrating Goal {args.execute_goal}", "bold cyan", "🎯")
                # Redirect bridge to use the long_horizon_planner on the pod
                script_rel = "scripts/execute_sovereign_goal.py" # New script we'll create
                train_args = ["--goal-id", args.execute_goal]

            script_rel = args.script or "scripts/train_neural_text_generator.py"
            
            # Auto-detect curriculum mode from flags
            is_curriculum_task = args.curriculum or args.find_elective or args.add_stage or args.list_stages or args.discover_only
            
            if is_curriculum_task:
                script_rel = "scripts/train_curriculum.py"
                if args.stage:
                    _rich_log(f"Targeting curriculum stages: {args.stage}", "cyan", "🎯")
                    if "--stages" not in train_args:
                        train_args.extend(["--stages", args.stage])
                
                if args.find_elective:
                    _rich_log(f"Dynamic discovery: '{args.find_elective}'", "cyan", "🔍")
                    if "--find-elective" not in train_args:
                        train_args.extend(["--find-elective", args.find_elective])
                    if args.auto_select and "--auto-select" not in train_args:
                        train_args.append("--auto-select")
                
                if args.add_stage:
                    _rich_log(f"Permanently adding stage: '{args.add_stage}'", "cyan", "➕")
                    if "--add-stage" not in train_args:
                        train_args.extend(["--add-stage", args.add_stage])
                    if args.auto_select and "--auto-select" not in train_args:
                        train_args.append("--auto-select")
                
                if args.list_stages:
                    _rich_log("Requesting curriculum stage listing", "cyan", "📋")
                    if "--list-stages" not in train_args:
                        train_args.append("--list-stages")

                if args.discover_only:
                    _rich_log("Discovery-only mode active", "cyan", "🔎")
                    if "--discover-only" not in train_args:
                        train_args.append("--discover-only")
                
                if not any([args.stage, args.find_elective, args.add_stage, args.list_stages, args.discover_only]):
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

            # SMART ALLOCATION: Partition cluster by topic
            if args.topics and len(pods) >= len(args.topics):
                _rich_log(f"Partitioning cluster into {len(args.topics)} groups...", "cyan", "✂")
                
                # Use ThreadPool to launch group-specific tasks
                def _launch_topic_group(topic_idx, topic):
                    dataset = topic_dataset_map.get(topic)
                    # Assign pods to this topic
                    start_pod_idx = topic_idx * args.pods_per_topic
                    group_pods = pods[start_pod_idx : start_pod_idx + args.pods_per_topic]
                    if not group_pods: return
                    
                    # Master pod for this group
                    master_pod = group_pods[0]
                    m_id = master_pod["id"]
                    
                    # Setup group-specific training args
                    group_args = list(train_args)
                    
                    # Find SSH details for this group master
                    m_runtime = master_pod.get("runtime") or {}
                    m_ports = m_runtime.get("ports") or []
                    m_ssh_port_info = next((pt for pt in m_ports if (pt.get("isIpPublic") or not any(pt.get("ip", "").startswith(pref) for pref in ["10.", "172.", "192."])) and pt.get("privatePort") == 22), None)
                    
                    m_ssh_proxy = None
                    if not m_ssh_port_info:
                        m_ssh_proxy = f"{m_id}-22@ssh.runpod.io"
                        m_ip = "ssh.runpod.io"
                        m_port = 22
                    else:
                        m_ip = m_ssh_port_info["ip"]
                        m_port = m_ssh_port_info["publicPort"]
                    
                    # Inject topic-specific data
                    # If using train_curriculum, we'll try to find a stage or use --find-elective
                    if is_curriculum_task:
                        # Remove any global discovery flags and replace with topic-specific
                        g_args = [a for a in group_args if a not in ["--find-elective", "--add-stage", "--stages"]]
                        # Use --find-elective for this specific topic to trigger discovery on pod
                        # Always use --auto to trigger training after discovery in this mode
                        g_args.extend(["--find-elective", topic, "--auto-select", "--auto"])
                        # Use unique adapter name for this topic
                        g_args.extend(["--adapter-name", f"topic_{topic.replace(' ', '_')}"])
                        _rich_log(f"Group '{topic}': Launching on pod {m_id} with dataset discovery...", "green", "🚀")
                        remote_train(m_ip, m_port, args.ssh_key, g_args, args.volume_mount_path, m_id, m_ssh_proxy, script_rel="scripts/train_curriculum.py")
                    else:
                        # standard NTG training
                        if "--source" not in group_args:
                            group_args.extend(["--source", "huggingface", "--book-ids", "roneneldan/TinyStories"])
                        else:
                            group_args.extend(["--book-ids", dataset])
                        
                        group_args.extend(["--adapter-name", f"topic_{topic.replace(' ', '_')}"])
                        _rich_log(f"Group '{topic}': Launching on pod {m_id} using {dataset or 'TinyStories'}...", "green", "🚀")
                        remote_train(m_ip, m_port, args.ssh_key, group_args, args.volume_mount_path, m_id, m_ssh_proxy, script_rel="scripts/train_neural_text_generator.py")

                with concurrent.futures.ThreadPoolExecutor(max_workers=len(args.topics)) as group_executor:
                    group_futures = [group_executor.submit(_launch_topic_group, i, t) for i, t in enumerate(args.topics)]
                    concurrent.futures.wait(group_futures)
                
                _rich_log("All topic groups finished execution.", "bold green", "✨")
                
            else:
                # Standard Virtual Cluster execution (Parallel training on all nodes)
                _rich_log(f"Launching synchronized training on {len(pods)} nodes...", "bold cyan", "🚀")
                
                def _launch_train_on_node(node_idx, node_pod):
                    node_id = node_pod["id"]
                    # Setup node-specific args
                    node_args = list(train_args)
                    if "--node-rank" not in node_args:
                        node_args.extend(["--node-rank", str(node_idx)])
                    
                    # Find SSH details for this specific node
                    n_runtime = node_pod.get("runtime") or {}
                    n_ports = n_runtime.get("ports") or []
                    n_ssh_port_info = next((pt for pt in n_ports if (pt.get("isIpPublic") or not any(pt.get("ip", "").startswith(pref) for pref in ["10.", "172.", "192."])) and pt.get("privatePort") == 22), None)
                    
                    n_ssh_proxy = None
                    if not n_ssh_port_info:
                        n_ssh_proxy = f"{node_id}-22@ssh.runpod.io"
                        n_ip = "ssh.runpod.io"
                        n_port = 22
                    else:
                        n_ip = n_ssh_port_info["ip"]
                        n_port = n_ssh_port_info["publicPort"]

                    # Default to HuggingFace if no source provided
                    if "--source" not in node_args and script_rel.endswith("train_neural_text_generator.py"):
                        node_args.extend(["--source", "huggingface", "--book-ids", "roneneldan/TinyStories"])

                    _rich_log(f"Node {node_idx} ({node_id}): Starting training...", "dim", "🏋")
                    remote_train(
                        n_ip, n_port, args.ssh_key, node_args, args.volume_mount_path, node_id, n_ssh_proxy, script_rel=script_rel
                    )

                with concurrent.futures.ThreadPoolExecutor(max_workers=len(pods)) as train_executor:
                    train_futures = [train_executor.submit(_launch_train_on_node, i, p) for i, p in enumerate(pods)]
                    # Wait for the first one to finish or fail
                    concurrent.futures.wait(train_futures, return_when=concurrent.futures.FIRST_COMPLETED)
                
                _rich_log("Virtual cluster training sequence complete.", "bold green", "✨")
            
            # Artifact Collection (Unified path)
            _rich_log("Starting cluster-wide artifact synchronization...", "cyan", "📥")
            for p in pods:
                p_id = p["id"]
                p_runtime = p.get("runtime") or {}
                p_ports = p_runtime.get("ports") or []
                p_ssh_port_info = next((pt for pt in p_ports if (pt.get("isIpPublic") or not any(pt.get("ip", "").startswith(pref) for pref in ["10.", "172.", "192."])) and pt.get("privatePort") == 22), None)
                
                p_ssh_proxy = None
                if not p_ssh_port_info:
                    p_ssh_proxy = f"{p_id}-22@ssh.runpod.io"
                    p_ip = "ssh.runpod.io"
                    p_port = 22
                else:
                    p_ip = p_ssh_port_info["ip"]
                    p_port = p_ssh_port_info["publicPort"]

                get_artifacts(p_ip, p_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, p_id, p_ssh_proxy)
                sync_training_data(p_ip, p_port, args.ssh_key, REPO_ROOT, args.volume_mount_path, p_id, p_ssh_proxy)
            
            # Register newly trained adapters with the AdapterRouter
            register_trained_adapters(REPO_ROOT)

            if args.use_s3:
                # Sync master pod to S3
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
                    src=f"{args.volume_mount_path}/oricli",
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
                        src=f"{args.volume_mount_path}/ollama",
                    )
                except Exception as ollama_e:
                    _rich_log(f"Ollama S3 push skipped: {ollama_e}", "yellow", "⚠")

            _rich_log("Cluster training successful! All artifacts retrieved.", "bold green", "✓")

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
                # Register any synchronized adapters
                register_trained_adapters(REPO_ROOT)
                _rich_log("Sync successful!", "bold green", "✓")
                break
            except Exception as e:
                _rich_log(f"Sync attempt {attempt+1} failed: {_redact_secrets(str(e))}", "red", "✗")
                if attempt < 2:
                    time.sleep(5)

    except Exception as e:
        failed = True
        _rich_log(f"Error detected: {_redact_secrets(str(e))}. Skipping snapshot to save disk space.", "red", "✗")
        # try:
        #     remote_snapshot(
        #         pod_ip, pod_port, args.ssh_key, args.volume_mount_path, pod["id"], args.ssh_proxy
        #     )
        # except Exception as snap_e:
        #     _rich_log(f"Snapshot failed: {snap_e}", "red", "✗")
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
            # Register any synchronized adapters
            register_trained_adapters(REPO_ROOT)
            if args.use_s3:
                s3_sync_pod(
                    pod_ip,
                    pod_port,
                    args.ssh_key,
                    args.s3_bucket,
                    f"{args.s3_prefix}/{pod['id']}",
                    args.s3_region,
                    args.s3_endpoint,
                    "push",
                    pod["id"],
                    args.ssh_proxy,
                    src="/workspace/oricli",
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
        
        # Determine if we need to clean up a cluster or a single pod
        if 'cluster_id' in locals() and cluster_id:
            _rich_log(f"Terminating entire cluster {cluster_id}...", "red", "💥")
            bridge.delete_cluster(cluster_id)
        elif pod and pod.get("id") and pod["id"] != "dry-run-id":
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
