
import os
import sys
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.modules.speculator import SpeculatorModule
from oricli_core.services.precog_service import PreCogService

def verify_speculation_loop():
    print("--- Step 1: Verifying Speculation Trigger ---")
    speculator = SpeculatorModule()
    precog = PreCogService()
    precog.clear()
    
    # Mock dependencies
    speculator.cog_gen = MagicMock()
    speculator.pipeline = MagicMock()
    
    # Mock follow-up prediction
    follow_up = "How do I use LoRA?"
    speculator.cog_gen.execute.return_value = {
        "success": True,
        "text": f"{follow_up}\nWhat is SFT?"
    }
    
    # Mock pipeline execution for that follow-up
    mock_answer = "LoRA is a technique for efficient fine-tuning."
    speculator.pipeline.execute.return_value = {
        "success": True,
        "answer": mock_answer
    }
    
    # Run speculation synchronously for testing
    speculator._run_speculation([], "What is fine-tuning?", "Fine-tuning is...")
    
    print("\n--- Step 2: Verifying Cache Retrieval ---")
    # Check if the follow-up was cached
    cached = precog.get_cached_response(follow_up)
    
    if cached and (cached.get("answer") == mock_answer):
        print(f"✓ Speculative response correctly cached for: {follow_up}")
        
        # Test fuzzy matching
        fuzzy_query = "how to use lora" # Different case/punctuation
        fuzzy_cached = precog.get_cached_response(fuzzy_query)
        if fuzzy_cached:
            print(f"✓ Fuzzy match successful for: {fuzzy_query}")
            return True
        else:
            print("✗ Fuzzy match failed.")
            return False
    else:
        print("✗ Speculation caching failed.")
        return False

if __name__ == "__main__":
    try:
        if verify_speculation_loop():
            print("\n✨ Pre-Cog Cache infrastructure verified!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
