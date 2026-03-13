#!/usr/bin/env python3
"""
Test RunPod Cluster orchestration logic.
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.runpod_bridge import _init_pod_worker

def test_init_pod_worker():
    """Verify that _init_pod_worker executes all setup steps."""
    mock_pod = {
        "id": "test-pod-123",
        "runtime": {
            "ports": [
                {"privatePort": 22, "publicPort": 12345, "ip": "1.2.3.4", "isIpPublic": True}
            ]
        }
    }
    
    mock_bridge = MagicMock()
    mock_args = MagicMock()
    mock_args.ssh_key = "mock-key"
    mock_args.volume_mount_path = "/workspace"
    mock_args.use_s3 = False
    mock_args.no_ollama = False
    mock_args.benchmark = False
    mock_args.internal_bench = False
    mock_args.force_refresh = False
    mock_args.pip_debug = False
    mock_args.pip_stream = False
    mock_args.editable_install = False
    mock_args.ssh_proxy = None
    
    with patch("scripts.runpod_bridge.setup_pod_env") as mock_setup, \
         patch("scripts.runpod_bridge.pre_sync_cleanup") as mock_cleanup, \
         patch("scripts.runpod_bridge.sync_code") as mock_sync, \
         patch("scripts.runpod_bridge.ensure_oricli_installed") as mock_install, \
         patch("scripts.runpod_bridge.setup_ollama") as mock_ollama:
         
        p_id = _init_pod_worker(mock_pod, mock_bridge, mock_args)
        
        assert p_id == "test-pod-123"
        assert mock_setup.called
        assert mock_cleanup.called
        assert mock_sync.called
        assert mock_install.called
        assert mock_ollama.called
        
        # Verify IP/Port extraction
        args, kwargs = mock_setup.call_args
        assert args[0] == "1.2.3.4"
        assert args[1] == 12345
        print("✓ _init_pod_worker verified")

if __name__ == "__main__":
    try:
        test_init_pod_worker()
        print("\n✨ Cluster orchestration tests passed!")
    except Exception as e:
        print(f"✗ Tests failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
