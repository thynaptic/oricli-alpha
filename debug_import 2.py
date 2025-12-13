#!/usr/bin/env python3
"""Debug script to find where import hangs"""
import sys
import traceback
import importlib.util

print("Step 1: Loading file...")
with open('mavaia_core/evaluation/test_runner.py', 'r') as f:
    content = f.read()
print(f"  File loaded: {len(content)} bytes")

print("\nStep 2: Compiling...")
try:
    code = compile(content, 'mavaia_core/evaluation/test_runner.py', 'exec')
    print("  ✓ Compiled successfully")
except Exception as e:
    print(f"  ✗ Compile error: {e}")
    sys.exit(1)

print("\nStep 3: Creating module namespace...")
module_dict = {'__name__': 'mavaia_core.evaluation.test_runner', '__file__': 'mavaia_core/evaluation/test_runner.py'}

print("\nStep 4: Executing module (this is where it might hang)...")
print("  (This will import dependencies and execute module-level code)")
try:
    exec(code, module_dict)
    print("  ✓ Module executed successfully")
    print(f"  TestRunnerCLI = {module_dict.get('TestRunnerCLI')}")
    print(f"  _get_cli_class = {module_dict.get('_get_cli_class')}")
except KeyboardInterrupt:
    print("\n  ✗ Interrupted - import is hanging")
    sys.exit(1)
except Exception as e:
    print(f"  ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n✓ Import completed successfully!")
