#!/usr/bin/env python3
"""
Smoke test for module health diagnostics.
"""

import sys
import os
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.module_health_diagnostics import run_diagnostics

def test_diagnostics_smoke():
    """Verify that the diagnostic script can run without crashing."""
    print("Testing diagnostics script smoke run...")
    
    # We expect some modules to fail in this environment (missing torch/transformers etc)
    # but the script itself should not crash.
    try:
        result = run_diagnostics()
        print(f"Diagnostics finished. Total modules checked: {result['total']}")
        print(f"Passed: {result['passed']}, Failed: {result['failed']}")
        
        if result['total'] > 0:
            print("✓ Diagnostics script successfully analyzed modules.")
        else:
            print("✗ No modules were discovered. Check ModuleRegistry.")
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ Diagnostics script crashed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_diagnostics_smoke()
