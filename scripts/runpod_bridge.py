import os
import sys
import json
import time
import subprocess
import argparse
import requests
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

    def create_pod(self, name: str, gpu_type_id: str, template_id: Optional[str] = None, image: Optional[str] = None, volume_mount_path: str = "/workspace", ssh_key_value: Optional[str] = None):
        input_fields = [
            f'name: "{name}"',
            f'gpuTypeId: "{gpu_type_id}"',
            f'gpuCount: 1',
            f'volumeInGb: 20',
            f'containerDiskInGb: 10',
            f'volumeMountPath: "{volume_mount_path}"'
        ]
        
        env_vars = []
        if ssh_key_value:
            env_vars.append(f'{{key: "PUBLIC_KEY", value: "{ssh_key_value}"}}')
            env_vars.append(f'{{key: "SSH_PUBLIC_KEY", value: "{ssh_key_value}"}}')

        if env_vars:
            input_fields.append(f'env: [{", ".join(env_vars)}]')
        
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
            "apt-get update && apt-get install -y rsync python3-venv && python3 -m pip install --upgrade pip"
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

def ensure_mavaia_installed(pod_ip: str, pod_port: int, ssh_key: str, pod_id: str = None, proxy: str = None):
    print("[*] Installing mavaia_core + training deps in pod venv...")

    if proxy:
        host = proxy
        port = "22"
    else:
        host = f"root@{pod_ip}"
        port = str(pod_port)

    install_cmd = (
        "set -e; "
        "cd /workspace/mavaia; "
        "python3 -m venv .venv; "
        ". .venv/bin/activate; "
        "pip install --upgrade pip setuptools wheel; "
        "pip install -e '.[train_neural]' torch transformers; "
        ".venv/bin/python -c \"import mavaia_core; print('mavaia_core_ok')\""
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


def sync_code(pod_ip: str, pod_port: int, ssh_key: str, local_path: Path, pod_id: str = None, proxy: str = None):
    print(f"[*] Syncing code to pod...")
    
    if proxy:
        rsync_cmd = [
            "rsync", "-avz", "--progress",
            "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22",
            "--exclude", ".git", "--exclude", "__pycache__", "--exclude", ".venv",
            str(local_path) + "/",
            f"{proxy}:/workspace/mavaia"
        ]
        subprocess.run(rsync_cmd, check=True)
        return
        
    rsync_cmd = [
        "rsync", "-avz", "--progress",
        "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p {pod_port}",
        "--exclude", ".git", "--exclude", "__pycache__", "--exclude", ".venv",
        "--exclude", ".cursor", "--exclude", ".vscode", "--exclude", "tmp",
        str(local_path) + "/",
        f"root@{pod_ip}:/workspace/mavaia"
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
            rsync_cmd[-1] = f"{pod_id}-22@ssh.runpod.io:/workspace/mavaia"
            proc = subprocess.run(rsync_cmd, check=False)
            if proc.returncode != 0 and proc.returncode != 23:
                raise subprocess.CalledProcessError(proc.returncode, rsync_cmd)
            elif proc.returncode == 23:
                print("[*] Rsync finished with status 23 (Partial Transfer) via proxy. Safe to proceed.")

def remote_train(pod_ip: str, pod_port: int, ssh_key: str, train_args: List[str], pod_id: str = None, proxy: str = None):
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
            f"cd /workspace/mavaia && /workspace/mavaia/.venv/bin/python scripts/train_neural_text_generator.py {args_str}"
        ]
        subprocess.run(ssh_cmd, check=True)
        return

    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "PasswordAuthentication=no",
        "-i", ssh_key,
        "-p", str(pod_port),
        f"root@{pod_ip}",
        f"cd /workspace/mavaia && /workspace/mavaia/.venv/bin/python scripts/train_neural_text_generator.py {args_str}"
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

def get_artifacts(pod_ip: str, pod_port: int, ssh_key: str, local_path: Path, pod_id: str = None, proxy: str = None):
    print(f"[*] Pulling trained models from pod...")

    dest_dir = local_path / "models" / "neural_text_generator_remote"
    dest_dir.mkdir(parents=True, exist_ok=True)

    if proxy:
        scp_cmd = [
            "rsync", "-avz",
            "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p 22",
            f"{proxy}:/workspace/mavaia/mavaia_core/models/neural_text_generator/",
            str(dest_dir) + "/",
        ]
        subprocess.run(scp_cmd, check=True)
        return

    scp_cmd = [
        "rsync", "-avz",
        "-e", f"ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no -i {ssh_key} -p {pod_port}",
        f"root@{pod_ip}:/workspace/mavaia/mavaia_core/models/neural_text_generator/",
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
            scp_cmd[4] = f"{pod_id}-22@ssh.runpod.io:/workspace/mavaia/mavaia_core/models/neural_text_generator/"
            proc = subprocess.run(scp_cmd, check=False)
            if proc.returncode != 0 and proc.returncode != 23:
                raise subprocess.CalledProcessError(proc.returncode, scp_cmd)
            elif proc.returncode == 23:
                print("[*] Rsync finished with status 23 (Partial Transfer) via proxy. Safe to proceed.")

def main():
    parser = argparse.ArgumentParser(description="Mavaia RunPod Training Bridge")
    parser.add_argument("--pod-id", help="Existing pod ID to use")
    parser.add_argument("--gpu", default="NVIDIA A40", help="GPU type for new pod")
    parser.add_argument("--image", default="runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04", help="Container image")
    parser.add_argument("--template", default="runpod-torch-v240", help="RunPod Template ID")
    parser.add_argument("--ssh-key", default=str(Path.home() / ".ssh" / "mavaia_key"), help="Path to your local private SSH key")
    parser.add_argument("--ssh-key-value", help="Public SSH key content (or name) to inject into the pod")
    parser.add_argument("--ssh-proxy", help="Full SSH proxy host (e.g. 68aeykzanq67mn-64411855@ssh.runpod.io)")
    parser.add_argument("--auto", action="store_true", help="Auto-manage: terminate active pods, pick best GPU under $0.50/hr, and train")
    parser.add_argument("--max-price", type=float, default=0.50, help="Max hourly price for auto GPU selection")
    parser.add_argument("--terminate", action="store_true", help="Terminate pod after training")
    parser.add_argument("--dry-run", action="store_true", help="Just print commands")
    
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

    pod = None
    if args.auto:
        print("[*] Auto-manage enabled: Finding existing pods...")
        pods = bridge.get_pods()
        for p in pods:
            print(f"[*] Terminating existing pod {p['id']} ({p.get('name')})...")
            bridge.terminate_pod(p['id'])
        
        print(f"[*] Finding best NVIDIA GPU under ${args.max_price}/hr...")
        gpu_types = bridge._query("query { gpuTypes { id displayName memoryInGb securePrice communityPrice } }").get("data", {}).get("gpuTypes", [])
        
        # Filter for nvidia, price <= args.max_price
        filtered_gpus = [
            g for g in gpu_types 
            if "NVIDIA" in g.get('id', '').upper() 
            and g.get('communityPrice') is not None 
            and g['communityPrice'] <= args.max_price
            and g.get('memoryInGb') is not None
        ]
        
        if not filtered_gpus:
            print(f"[!] No suitable GPUs found under ${args.max_price}/hr.")
            sys.exit(1)
            
        # Sort by memory descending, then price ascending (highest memory, lowest price tiebreaker)
        filtered_gpus.sort(key=lambda x: (x['memoryInGb'], -x['communityPrice']), reverse=True)
        best_gpu = filtered_gpus[0]
        gpu_id = best_gpu['id']
        
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

    if not pod and gpu_id:
        print(f"[*] Launching pod with GPU: {gpu_id}...")
        if args.dry_run:
            print(f"[DRY-RUN] Would launch {gpu_id} pod with template {args.template}")
            pod = {"id": "dry-run-id", "runtime": {"ports": [{"ip": "1.2.3.4", "publicPort": 1234, "isIpPublic": True}]}}
        else:
            pod_result = bridge.create_pod(
                name="mavaia-trainer", 
                gpu_type_id=gpu_id, 
                template_id=args.template, 
                image=args.image,
                ssh_key_value=args.ssh_key_value
            )
            if not pod_result:
                print("[!] Failed to create pod.")
                sys.exit(1)
            pod_id = pod_result['id']
            print(f"[*] Pod {pod_id} launched. Waiting for it to be ready...")
            
            # Polling for readiness
            while True:
                pods = bridge.get_pods()
                pod = next((p for p in pods if p['id'] == pod_id), None)
                if pod and pod.get("runtime") and pod["runtime"].get("uptimeInSeconds", 0) > 0:
                    break
                time.sleep(10)

    # Get SSH details
    # Look for privatePort 22, then fallback to first available public port
    public_ports = [p for p in pod.get("runtime", {}).get("ports", []) if p.get("isIpPublic")]
    ssh_port_info = next((p for p in public_ports if p.get("privatePort") == 22), None)
    
    if not ssh_port_info and public_ports:
        # Fallback to first available if 22 isn't explicitly found
        ssh_port_info = public_ports[0]
        print(f"[*] Warning: Port 22 not found; falling back to port {ssh_port_info['publicPort']} (mapped from {ssh_port_info['privatePort']})")
    
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

    try:
        setup_pod_env(pod_ip, pod_port, args.ssh_key, pod['id'], args.ssh_proxy)
        sync_code(pod_ip, pod_port, args.ssh_key, REPO_ROOT, pod['id'], args.ssh_proxy)
        ensure_mavaia_installed(pod_ip, pod_port, args.ssh_key, pod['id'], args.ssh_proxy)
        remote_train(pod_ip, pod_port, args.ssh_key, args.train_args, pod['id'], args.ssh_proxy)
        get_artifacts(pod_ip, pod_port, args.ssh_key, REPO_ROOT, pod['id'], args.ssh_proxy)

        
        print("[*] Remote training successful! Artifacts retrieved.")
        
    finally:
        if args.terminate:
            print(f"[*] Terminating pod {pod['id']}...")
            bridge.terminate_pod(pod['id'])
        else:
            print(f"[*] Stopping pod {pod['id']} (saving costs)...")
            bridge.stop_pod(pod['id'])

if __name__ == "__main__":
    main()
