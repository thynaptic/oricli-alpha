
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.mavaia_metacognition_daemon import MetacognitionDaemon

def verify_metacognition_cycle():
    print("--- Step 1: Initializing Daemon ---")
    daemon = MetacognitionDaemon()
    
    # Mock dependencies
    daemon.trace_diag = MagicMock()
    daemon.refactor = MagicMock()
    daemon.cog_gen = MagicMock()
    daemon.sandbox = MagicMock()
    
    print("\n--- Step 2: Mocking Anomaly Detection ---")
    mock_anomaly = {
        "issue_type": "high_latency",
        "module": "agent_pipeline",
        "description": "Sequential execution is slow.",
        "context": "File: agent_pipeline.py"
    }
    daemon.trace_diag.execute.return_value = {
        "success": True,
        "findings": [mock_anomaly]
    }
    
    print("\n--- Step 3: Mocking Patch Generation ---")
    mock_patch = "def execute_parallel():\n    pass # Optimized!"
    daemon.cog_gen.execute.return_value = {"text": mock_patch}
    
    print("\n--- Step 4: Mocking Sandbox Validation ---")
    daemon.sandbox.execute.return_value = {"success": True}
    
    print("\n--- Step 5: Running Cycle ---")
    daemon.run_cycle()
    
    print("\n--- Step 6: Verifying Proposal Generation ---")
    docs_dir = REPO_ROOT / "docs"
    proposals = list(docs_dir.glob("REFORM_PROPOSAL_*.md"))
    
    if proposals:
        latest = sorted(proposals)[-1]
        content = latest.read_text()
        if "agent_pipeline" in content and "Optimized!" in content:
            print(f"✓ Reform Proposal correctly generated: {latest.name}")
            return True
        else:
            print("✗ Proposal content mismatch.")
            return False
    else:
        print("✗ No proposal generated.")
        return False

if __name__ == "__main__":
    try:
        if verify_metacognition_cycle():
            print("\n✨ Autonomic Self-Modification infrastructure verified!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
