
import os
import sys
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.modules.subconscious_field import SubconsciousFieldModule
from oricli_core.brain.modules.cognitive_generator import CognitiveGeneratorModule

def verify_subconscious_vibration():
    print("--- Step 1: Verifying Vibration ---")
    field = SubconsciousFieldModule()
    field.execute("clear_field", {})
    
    # Mock embeddings
    field.embeddings = MagicMock()
    mock_vector = [0.1] * 384
    field.embeddings.execute.return_value = {"embedding": mock_vector, "dimension": 384}
    
    field.execute("vibrate", {"text": "Blockchain is a distributed ledger."})
    
    state = field.execute("get_mental_state", {})
    if state.get("success") and state.get("vibration_count") == 1:
        print(f"✓ Vibration recorded. Mental state dimension: {state.get('dimension')}")
        return True
    else:
        print("✗ Vibration failed.")
        return False

def verify_generator_integration():
    print("\n--- Step 2: Verifying Generator Integration ---")
    cog_gen = CognitiveGeneratorModule()
    
    # Mock the field
    cog_gen.subconscious_field = MagicMock()
    mock_ms = [0.5] * 384
    cog_gen.subconscious_field.execute.return_value = {"success": True, "mental_state": mock_ms}
    
    intent = cog_gen._detect_intent("Tell me about consensus algorithms")
    
    if intent.get("mental_state") == mock_ms:
        print("✓ Generator correctly retrieved mental state during intent detection.")
        return True
    else:
        print("✗ Generator failed to retrieve mental state.")
        return False

if __name__ == "__main__":
    try:
        if verify_subconscious_vibration() and verify_generator_integration():
            print("\n✨ Persistent Memory Subconscious verified!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
