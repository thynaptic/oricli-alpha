
import os
import sys
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.modules.arc_solver import ARCSolverModule
from oricli_core.brain.modules.arc_data_augmentation import ARCTask

def verify_arc_ensemble():
    print("--- Verifying ARC Ensemble System ---")
    solver = ARCSolverModule()
    solver.initialize()
    
    # 1. Test Induction Success Case
    print("\n[Test 1] Induction Success (Move Down)")
    train_input = [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
    train_output = [[0, 0, 0], [1, 0, 0], [0, 0, 0]]
    test_input = [[0, 0, 2], [0, 0, 0], [0, 0, 0]]
    expected_output = [[0, 0, 0], [0, 0, 2], [0, 0, 0]]
    
    # Mock modules
    with patch('oricli_core.brain.registry.ModuleRegistry.get_module') as mock_get:
        # Mock induction to succeed
        mock_induction = MagicMock()
        mock_induction.execute.return_value = {
            "success": True, 
            "prediction": expected_output,
            "method": "induction"
        }
        
        # Mock transduction (should still be called if method='ensemble')
        mock_transduction = MagicMock()
        mock_transduction.execute.return_value = {"success": False}
        
        mock_get.side_effect = lambda name: mock_induction if name == "arc_induction" else mock_transduction
        
        res = solver.execute("solve_arc_ensemble", {
            "train_examples": [(train_input, train_output)],
            "test_input": test_input,
            "method": "induction"
        })
        
        if res.get("success") and res.get("method_used") == "induction":
            print("✓ Correctly solved via Induction.")
        else:
            print(f"✗ Induction success test failed: {res}")
            return False

    # 2. Test Transduction Fallback Case
    print("\n[Test 2] Transduction Fallback (Induction Fails)")
    # Mock modules
    with patch('oricli_core.brain.registry.ModuleRegistry.get_module') as mock_get:
        # Mock induction to fail
        mock_induction = MagicMock()
        mock_induction.execute.return_value = {"success": False}
        
        # Mock transduction to succeed
        mock_transduction = MagicMock()
        mock_transduction.execute.return_value = {
            "success": True, 
            "prediction": [[1,1], [1,1]],
            "method": "transduction"
        }
        
        mock_get.side_effect = lambda name: mock_induction if name == "arc_induction" else mock_transduction
        
        res = solver.execute("solve_arc_ensemble", {
            "train_examples": [(train_input, train_output)],
            "test_input": test_input,
            "method": "auto"
        })
        
        if res.get("success") and res.get("method_used") == "transduction":
            print("✓ Correctly fell back to Transduction.")
            return True
        else:
            print(f"✗ Transduction fallback test failed: {res}")
            return False

if __name__ == "__main__":
    try:
        if verify_arc_ensemble():
            print("\n✨ ARC Hybrid System verified!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
