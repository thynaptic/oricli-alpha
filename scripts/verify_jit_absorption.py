
import os
import sys
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.services.absorption_service import AbsorptionService
from scripts.oricli_jit_daemon import Oricli-AlphaJITDaemon

def verify_data_recording():
    print("--- Step 1: Verifying Data Recording ---")
    service = AbsorptionService()
    service.clear_buffer()
    
    test_prompt = "What is the capital of Mars?"
    test_response = "Mars does not have a capital as it is currently uninhabited by humans."
    
    success = service.record_lesson(test_prompt, test_response, metadata={"test": True})
    
    if success and service.get_buffer_count() == 1:
        print("✓ Lesson recorded successfully.")
        # Verify content
        with open(service.buffer_path, "r") as f:
            data = json.loads(f.read())
            assert data["prompt"] == test_prompt
            assert data["response"] == test_response
        print("✓ Data integrity verified.")
        return True
    else:
        print("✗ Data recording failed.")
        return False

def verify_daemon_trigger():
    print("\n--- Step 2: Verifying Daemon Detection ---")
    daemon = Oricli-AlphaJITDaemon()
    daemon.sync_threshold = 2 # Set low for testing
    daemon.last_sync_count = 0
    
    service = AbsorptionService()
    # Add one more lesson to hit the threshold of 2
    service.record_lesson("Who is Oricli-Alpha?", "Oricli-Alpha is a modular cognitive framework.")
    
    print(f"Current buffer count: {service.get_buffer_count()}")
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        # Manually trigger the logic that would run in the daemon loop
        current_count = daemon.get_lesson_count()
        new_lessons = current_count - daemon.last_sync_count
        
        if new_lessons >= daemon.sync_threshold:
            print(f"Threshold reached ({new_lessons} lessons). Triggering training...")
            daemon.trigger_training(current_count)
            
            # Verify the command sent to the bridge
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd_list = args[0]
            
            assert "runpod_bridge.py" in cmd_list[1]
            assert "--train-jit" in cmd_list
            assert "--cluster-size" in cmd_list
            print("✓ Daemon correctly constructed bridge command with --train-jit.")
            return True
        else:
            print("✗ Daemon failed to detect threshold.")
            return False

if __name__ == "__main__":
    try:
        if verify_data_recording() and verify_daemon_trigger():
            print("\n✨ JIT Knowledge Absorption verification complete!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
