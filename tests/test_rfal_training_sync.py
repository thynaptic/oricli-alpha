#!/usr/bin/env python3
"""
Test RunPod bridge integration for RFAL DPO training.
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

def test_bridge_rfal_flag():
    """Verify that --train-rfal correctly sets up DPO training args."""
    print("Testing --train-rfal flag handling in bridge...")
    
    # 1. Setup all mocks
    mocks = [
        patch("scripts.runpod_bridge.RunPodBridge"),
        patch("scripts.runpod_bridge.get_task_details"),
        patch("scripts.runpod_bridge.calculate_required_vram"),
        patch("scripts.runpod_bridge._rich_log"),
        patch("scripts.runpod_bridge.remote_train"),
        patch("scripts.runpod_bridge.setup_pod_env"),
        patch("scripts.runpod_bridge.ensure_mavaia_installed"),
        patch("scripts.runpod_bridge.pre_sync_cleanup"),
        patch("scripts.runpod_bridge.setup_ollama"),
        patch("scripts.runpod_bridge.sync_code"),
        patch("scripts.runpod_bridge.sync_models_to_pod"),
        patch("scripts.runpod_bridge.sync_training_data"),
        patch("scripts.runpod_bridge.get_artifacts"),
        patch("scripts.runpod_bridge.get_bench_results"),
        patch("scripts.runpod_bridge.remote_snapshot"),
        patch("scripts.runpod_bridge.summarize_results"),
        patch("scripts.runpod_bridge.register_trained_adapters"),
        patch("scripts.runpod_bridge.s3_sync_local_to_bucket"),
        patch("scripts.runpod_bridge.s3_sync_pod"),
        patch("scripts.runpod_bridge.RUNPOD_API_KEY", "mock-key")
    ]
    
    # Start all patches
    started_mocks = [p.start() for p in mocks]
    
    try:
        mock_bridge_cls = started_mocks[0]
        mock_get_details = started_mocks[1]
        mock_calc_vram = started_mocks[2]
        mock_remote_train = started_mocks[4]
        
        mock_get_details.return_value = {"model_type": "transformer", "dataset_size": 0, "batch_size": 1, "sequence_length": 512}
        mock_calc_vram.return_value = 8
        
        mock_bridge = mock_bridge_cls.return_value
        mock_bridge.get_pods.return_value = [{
            "id": "mock-pod-id",
            "name": "mavaia_train",
            "desiredStatus": "RUNNING",
            "runtime": {
                "uptimeInSeconds": 100,
                "ports": [{"ip": "1.2.3.4", "isIpPublic": True, "privatePort": 22, "publicPort": 12345}]
            }
        }]
        
        from scripts.runpod_bridge import main
        
        # Simulate running bridge with --train-rfal
        test_args = [
            "--train-rfal",
            "--pod-id", "mock-pod-id",
            "--train-args", "--model-type", "transformer"
        ]
        
        with patch.object(sys, 'argv', ["scripts/runpod_bridge.py"] + test_args):
            try:
                main()
            except SystemExit:
                pass
                
        # Verify remote_train was called with --dpo and --dpo-data
        if mock_remote_train.called:
            args, kwargs = mock_remote_train.call_args
            passed_args = args[3]
            print(f"✓ remote_train called with args: {passed_args}")
            
            if "--dpo" in passed_args and "--dpo-data" in passed_args:
                print("✓ --dpo and --dpo-data flags correctly forwarded")
                idx = passed_args.index("--dpo-data")
                if passed_args[idx+1] == "mavaia_core/data/rfal_lessons.jsonl":
                    print("✓ Correct DPO data path forwarded")
                else:
                    print(f"✗ Incorrect DPO data path: {passed_args[idx+1]}")
                    sys.exit(1)
            else:
                print("✗ DPO flags NOT forwarded to remote_train")
                sys.exit(1)
        else:
            print("✗ remote_train was NOT called")
            sys.exit(1)
            
    finally:
        # Stop all patches in reverse order
        for p in reversed(mocks):
            p.stop()

if __name__ == "__main__":
    try:
        test_bridge_rfal_flag()
        print("\n✨ All Phase 4 Training Sync tests passed!")
    except Exception as e:
        print(f"✗ Tests failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
