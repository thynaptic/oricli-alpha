
import os
import sys
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.mavaia_dream_daemon import MavaiaDreamDaemon
from mavaia_core.services.insight_service import InsightService

def verify_dream_cycle():
    print("--- Step 1: Preparing Mock Knowledge ---")
    jit_path = REPO_ROOT / "mavaia_core/data/jit_absorption.jsonl"
    
    # Add mock facts to dream about
    facts = [
        {"response": "Mavaia uses a modular cognitive framework."},
        {"response": "Biological neurons use electrochemical signals for communication."},
        {"response": "Blockchain technology uses distributed consensus."}
    ]
    
    with open(jit_path, "w", encoding="utf-8") as f:
        for f_data in facts:
            f.write(json.dumps(f_data) + "\n")
    
    print(f"✓ Mock JIT buffer populated with {len(facts)} facts.")

    print("\n--- Step 2: Running Mock Dream Cycle ---")
    daemon = MavaiaDreamDaemon()
    daemon.cog_gen = MagicMock()
    
    # Mock successful insight generation
    mock_insight = "Mavaia's modular framework can be optimized using a blockchain-inspired consensus for cross-module validation."
    daemon.cog_gen.execute.return_value = {
        "success": True,
        "text": json.dumps({"insight": mock_insight, "score": 0.9})
    }
    
    daemon.dream_cycle()
    
    print("\n--- Step 3: Verifying Insight Recording ---")
    service = InsightService()
    untrained = service.list_untrained_insights()
    
    if untrained and untrained[0]["insight"] == mock_insight:
        print(f"✓ Novel insight correctly recorded: {mock_insight}")
        return True
    else:
        print("✗ Insight recording failed.")
        return False

if __name__ == "__main__":
    try:
        if verify_dream_cycle():
            print("\n✨ Synthetic Dream State infrastructure verified!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
