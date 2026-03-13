
import os
import sys
import numpy as np
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.modules.arc_transduction_model import ARCTransductionModel

def verify_transduction_logic():
    print("--- Verifying Simple Transduction Model (CPU) ---")
    model = ARCTransductionModel()
    
    # Test 1: Geometric Symmetry (Rotate 90)
    print("\n[Test 1] Geometric Symmetry (Rotate 90)")
    train_inp = [[1, 2], [0, 0]]
    train_out = [[0, 1], [0, 2]] # Rotated 90
    test_inp = [[3, 4], [0, 0]]
    expected = [[0, 3], [0, 4]]
    
    pred = model.predict([(train_inp, train_out)], test_inp)
    if np.array_equal(np.array(pred), np.array(expected)):
        print("✓ Correctly solved via Geometric Symmetry.")
    else:
        print(f"✗ Geometric Symmetry failed. Pred: {pred}")
        return False

    # Test 2: Color Mapping
    print("\n[Test 2] Color Mapping")
    train_inp = [[1, 1], [2, 2]]
    train_out = [[3, 3], [4, 4]] # 1->3, 2->4
    test_inp = [[1, 2], [1, 2]]
    expected = [[3, 4], [3, 4]]
    
    pred = model.predict([(train_inp, train_out)], test_inp)
    if np.array_equal(np.array(pred), np.array(expected)):
        print("✓ Correctly solved via Color Mapping.")
    else:
        print(f"✗ Color Mapping failed. Pred: {pred}")
        return False

    return True

if __name__ == "__main__":
    try:
        if verify_transduction_logic():
            print("\n✨ Simple Transduction Model verified!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
