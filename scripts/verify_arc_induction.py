
import os
import sys
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.modules.arc_induction import ARCInductionModule
from oricli_core.brain.modules.arc_data_augmentation import ARCTask

def verify_arc_induction():
    print("--- Verifying ARC Induction Loop ---")
    induction = ARCInductionModule()
    
    # Simple "Move Down" task
    train_input_1 = [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
    train_output_1 = [[0, 0, 0], [1, 0, 0], [0, 0, 0]]
    
    train_input_2 = [[0, 2, 0], [0, 0, 0], [0, 0, 0]]
    train_output_2 = [[0, 0, 0], [0, 2, 0], [0, 0, 0]]
    
    test_input = [[0, 0, 3], [0, 0, 0], [0, 0, 0]]
    expected_output = [[0, 0, 0], [0, 0, 3], [0, 0, 0]]
    
    task = ARCTask(
        train_inputs=[train_input_1, train_input_2],
        train_outputs=[train_output_1, train_output_2],
        test_input=test_input
    )
    
    # Mock Ollama to return a working program
    induction.ollama_provider = MagicMock()
    induction.ollama_provider.execute.return_value = {
        "success": True,
        "text": """
```python
def transform(input_grid):
    objs = get_objects(input_grid)
    if not objs: return input_grid
    return move_object(input_grid, objs[0], 1, 0)
```
"""
    }
    
    print("  - Attempting to solve 'Move Down' task...")
    res = induction.execute("solve_task", {"task": task.to_dict()})
    
    if res.get("success"):
        prediction = res.get("prediction")
        print(f"✓ Induction found a working program.")
        print(f"✓ Prediction: {prediction}")
        if np.array_equal(np.array(prediction), np.array(expected_output)):
            print("✓ Prediction matches expected output!")
            return True
        else:
            print("✗ Prediction does not match expected output.")
            return False
    else:
        print(f"✗ Induction failed: {res.get('error')}")
        return False

if __name__ == "__main__":
    try:
        # We need to install scipy for the DSL to work
        print("  - Ensuring scipy is available for DSL...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "scipy"])
        
        if verify_arc_induction():
            print("\n✨ ARC Induction Loop verified!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
