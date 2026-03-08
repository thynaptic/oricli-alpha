
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

def verify_multi_modal_routing():
    print("--- Step 1: Verifying Multi-Modal Sensory Routing ---")
    cog_gen = CognitiveGeneratorModule()
    cog_gen._ensure_modules_loaded()
    
    # Mock a dummy image file
    test_image = REPO_ROOT / "test_sensory_input.png"
    test_image.touch()
    
    try:
        # We need to mock the architect and executor to avoid full execution during routing test
        cog_gen.pathway_architect = MagicMock()
        cog_gen.graph_executor = MagicMock()
        cog_gen.graph_executor.execute.return_value = {"success": True, "final_result": {"text": "Verified"}}
        
        # Test routing an image path
        print(f"  - Testing with mock image: {test_image}")
        res = cog_gen.execute("generate_response", {"input": str(test_image)})
        
        # Check if architect was called with vision_context
        args, kwargs = cog_gen.pathway_architect.execute.call_args
        params = args[1]
        
        if params.get("vision_context"):
            print("✓ Sensory Router correctly identified image and passed context to architect.")
            return True
        else:
            print("✗ Sensory routing failed.")
            return False
    finally:
        if test_image.exists():
            test_image.unlink()

if __name__ == "__main__":
    try:
        if verify_multi_modal_routing():
            print("\n✨ Multi-Modal Infrastructure verified!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
