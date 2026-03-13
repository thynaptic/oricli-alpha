
import os
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.services.goal_service import GoalService
from scripts.oricli_goal_daemon import OricliAlphaGoalDaemon

def verify_goal_lifecycle():
    print("--- Step 1: Verifying Goal Registration ---")
    service = GoalService()
    
    test_goal = "Analyze the future of decentralized AI"
    goal_id = service.add_objective(test_goal, priority=3)
    
    objectives = service.list_objectives()
    match = next((obj for obj in objectives if obj["id"] == goal_id), None)
    
    if match and match["goal"] == test_goal:
        print(f"✓ Goal {goal_id} registered and retrieved correctly.")
    else:
        print("✗ Goal registration failed.")
        return False

    print("\n--- Step 2: Verifying Plan Persistence ---")
    test_plan = {
        "steps": [
            {"id": "step1", "action": "Research Web3 AI"},
            {"id": "step2", "action": "Compare with Centralized"}
        ],
        "executed_steps": [{"id": "step1", "success": True}]
    }
    
    service.save_plan_state(goal_id, test_plan)
    loaded = service.load_plan_state(goal_id)
    
    if loaded and len(loaded["executed_steps"]) == 1:
        print("✓ Plan state saved and resumed correctly.")
    else:
        print("✗ Plan persistence failed.")
        return False
        
    return True

def verify_goal_daemon():
    print("\n--- Step 3: Verifying Goal Daemon Orchestration ---")
    daemon = OricliAlphaGoalDaemon()
    
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock(pid=12345)
        
        # Manually trigger process_pending_goals
        daemon.process_pending_goals()
        
        # Verify bridge trigger
        mock_popen.assert_called()
        args, kwargs = mock_popen.call_args
        cmd = args[0]
        
        assert "runpod_bridge.py" in cmd[1]
        assert "--execute-goal" in cmd
        print("✓ Goal Daemon correctly constructed bridge orchestration command.")
        return True

if __name__ == "__main__":
    try:
        if verify_goal_lifecycle() and verify_goal_daemon():
            print("\n✨ Sovereign Goal Execution infrastructure verified!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
