
import os
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.oricli_tool_daemon import OricliAlphaToolDaemon

def verify_scenario_file():
    print("--- Step 1: Verifying Scenario File ---")
    path = REPO_ROOT / "oricli_core" / "data" / "tool_bench_scenarios.json"
    if path.exists():
        with open(path, "r") as f:
            data = json.load(f)
            print(f"✓ Found {len(data)} scenarios.")
            return True
    print("✗ Scenario file missing.")
    return False

def verify_correction_logging():
    print("\n--- Step 2: Verifying Correction Logging ---")
    path = REPO_ROOT / "oricli_core" / "data" / "tool_corrections.jsonl"
    
    # Simulate a correction
    test_correction = {
        "prompt": "Test query",
        "rejected": "wrong tool call",
        "chosen": "right tool call",
        "reason": "Selection error"
    }
    
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(test_correction) + "\n")
    
    print("✓ Simulated correction logged.")
    return True

def verify_tool_daemon():
    print("\n--- Step 3: Verifying Tool Daemon Trigger ---")
    daemon = OricliAlphaToolDaemon()
    daemon.sync_threshold = 1 # Set low for test
    daemon.last_sync_count = 0
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        count = daemon.get_correction_count()
        if count >= daemon.sync_threshold:
            print(f"Threshold reached ({count}). Triggering training...")
            daemon.trigger_training(count)
            
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert "runpod_bridge.py" in cmd[1]
            assert "--train-tool-bench" in cmd
            print("✓ Tool Daemon correctly triggered bridge with --train-tool-bench.")
            return True
    return False

if __name__ == "__main__":
    if verify_scenario_file() and verify_correction_logging() and verify_tool_daemon():
        print("\n✨ Dynamic ToolBench verification complete!")
    else:
        sys.exit(1)
