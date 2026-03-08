
import os
import sys
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mavaia_core.brain.modules.cognitive_generator import CognitiveGeneratorModule
from mavaia_core.brain.modules.metacognitive_sentinel import MetacognitiveSentinelModule

def verify_sentinel_logic():
    print("--- Step 1: Verifying Volatility Detection (Looping) ---")
    sentinel = MetacognitiveSentinelModule()
    
    # Simulate a looping trace
    looping_trace = "I am repeating myself. I am repeating myself. I am repeating myself. I am repeating myself." * 5
    
    health = sentinel.execute("assess_cognitive_health", {"trace": looping_trace})
    print(f"  - Metrics: {health.get('metrics')}")
    print(f"  - Volatility: {health.get('volatility')}")
    print(f"  - Intervention: {health.get('requires_intervention')}")
    
    if health.get("cognitive_state") == "Looping" and health.get("requires_intervention"):
        print(f"✓ Sentinel correctly identified Looping state (Volatility: {health.get('volatility'):.2f})")
    else:
        print(f"✗ Volatility detection failed. State: {health.get('cognitive_state')}")
        return False

    print("\n--- Step 2: Verifying Radical Acceptance ---")
    # Mock subconscious field for vibration
    sentinel.subconscious_field = MagicMock()
    
    intervention = sentinel.execute("apply_radical_acceptance", {
        "goal": "Explain blockchain",
        "failed_path": looping_trace
    })
    
    if intervention.get("intervention") == "radical_acceptance" and intervention.get("action_required") == "reroute":
        print("✓ Radical Acceptance applied successfully.")
        # Verify subconscious vibration was called with negative weight
        sentinel.subconscious_field.execute.assert_called_once()
        args = sentinel.subconscious_field.execute.call_args[0]
        params = args[1]
        if params.get("weight", 0) < 0:
            print("✓ Subconscious field successfully dampened the loop bias.")
            return True
    
    print("✗ Radical Acceptance intervention failed.")
    return False

def verify_generator_sentinel_integration():
    print("\n--- Step 3: Verifying Generator Integration ---")
    cog_gen = CognitiveGeneratorModule()
    cog_gen._ensure_modules_loaded()
    
    # Mock components
    cog_gen.metacognitive_sentinel = MagicMock()
    cog_gen.pathway_architect = MagicMock()
    cog_gen.graph_executor = MagicMock()
    
    # Force a 'Looping' health result
    cog_gen.metacognitive_sentinel.execute.side_effect = [
        {"requires_intervention": True, "cognitive_state": "Looping", "volatility": 0.9}, # assess
        {"intervention": "radical_acceptance", "action_required": "reroute", "instruction": "RESETTING."} # apply
    ]
    
    # Mock executor to return a looping response
    cog_gen.graph_executor.execute.return_value = {
        "success": True, 
        "final_result": {"text": "Loop loop loop loop loop"}
    }
    
    res = cog_gen.execute("generate_response", {"input": "Test loop"})
    
    if "RESETTING." in res.get("text", ""):
        print("✓ Generator successfully integrated Sentinel intervention.")
        return True
    else:
        print("✗ Generator integration failed.")
        return False

if __name__ == "__main__":
    try:
        if verify_sentinel_logic() and verify_generator_sentinel_integration():
            print("\n✨ Metacognitive Sentience Layer verified!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
