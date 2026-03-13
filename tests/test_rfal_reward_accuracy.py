#!/usr/bin/env python3
"""
Test reward calculation and DPO pair generation in the RFAL Engine.
"""

import sys
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.registry import ModuleRegistry

def test_multi_factor_reward():
    """Verify that HITL, Fact, and Tone signals are correctly weighted."""
    print("Testing multi-factor reward scoring...")
    
    # Ensure heavy modules are enabled
    os.environ["MAVAIA_ENABLE_HEAVY_MODULES"] = "true"
    
    rfal = ModuleRegistry.get_module("rfal_engine")
    
    # Mock dependencies
    mock_wk = MagicMock()
    mock_ar = MagicMock()
    
    with patch("oricli_core.brain.registry.ModuleRegistry.get_module") as mock_get:
        def side_effect(name, **kwargs):
            if name == "world_knowledge":
                return mock_wk
            if name == "adapter_router":
                return mock_ar
            return ModuleRegistry.get_module(name, **kwargs)
        
        mock_get.side_effect = side_effect
        
        # Scenario: Hallucinated fact detected by WK
        # HITL: No conflict (+1.0)
        # FACT: Invalid (-1.0)
        # TONE: Match (+1.0)
        # Result: (1.0 * 0.6) + (-1.0 * 0.3) + (1.0 * 0.1) = 0.6 - 0.3 + 0.1 = 0.4?
        # Wait, if reward is positive we don't create lesson? 
        # Actually, any NEGATIVE component should probably trigger a lesson or we adjust weights.
        # Let's test a direct conflict.
        
        mock_wk.execute.return_value = {"valid": False}
        mock_ar.execute.return_value = {"intent": "coding"}
        
        res = rfal.execute("process_feedback", {
            "user_input": "Actually that's wrong.", # HITL Conflict
            "last_response": "hallucinated code",
            "prompt": "write code",
            "intent": "coding"
        })
        
        reward = res.get("reward")
        print(f"✓ Calculated reward for conflict + hallucination: {reward}")
        
        # HITL=-1.0, FACT=-1.0, TONE=1.0
        # (-1.0 * 0.6) + (-1.0 * 0.3) + (1.0 * 0.1) = -0.6 - 0.3 + 0.1 = -0.8
        if abs(reward - (-0.8)) < 1e-6:
            print("✓ Weighted reward correctly calculated")
        else:
            print(f"✗ Unexpected reward: {reward} (Expected -0.8)")
            sys.exit(1)
            
        if res.get("lesson_created"):
            print("✓ DPO lesson correctly created for negative reward")
        else:
            print("✗ Lesson NOT created for negative reward")
            sys.exit(1)

def test_persistence():
    """Verify that lessons are persisted to the JSONL file."""
    print("\nTesting lesson persistence...")
    
    rfal = ModuleRegistry.get_module("rfal_engine")
    buffer_path = Path("oricli_core/data/rfal_lessons.jsonl")
    
    # Clear file first
    if buffer_path.exists():
        os.remove(buffer_path)
        
    # Generate manual pair
    rfal.execute("generate_dpo_pair", {
        "prompt": "p",
        "chosen": "c",
        "rejected": "r"
    })
    
    if buffer_path.exists():
        content = buffer_path.read_text().strip().splitlines()
        if len(content) == 1:
            data = json.loads(content[0])
            if data["chosen"] == "c":
                print("✓ Lesson successfully persisted to JSONL")
            else:
                print(f"✗ Incorrect data in file: {data}")
                sys.exit(1)
        else:
            print(f"✗ Unexpected file line count: {len(content)}")
            sys.exit(1)
    else:
        print("✗ Lesson file NOT created")
        sys.exit(1)

if __name__ == "__main__":
    try:
        test_multi_factor_reward()
        test_persistence()
        print("\n✨ All Phase 2 Reward Engine tests passed!")
    except Exception as e:
        print(f"✗ Tests failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
