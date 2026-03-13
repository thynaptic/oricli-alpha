#!/usr/bin/env python3
"""Test script to check if test_runner imports without hanging"""
import sys
import signal
import time

def timeout_handler(signum, frame):
    print("TIMEOUT: Import took too long (>10 seconds)")
    sys.exit(1)

# Set a 10 second timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)

try:
    print("Attempting to import test_runner...")
    start = time.time()
    import oricli_core.evaluation.test_runner
    elapsed = time.time() - start
    signal.alarm(0)  # Cancel alarm
    print(f"✓ Import successful in {elapsed:.2f} seconds")
    print(f"✓ TestRunnerCLI is: {oricli_core.evaluation.test_runner.TestRunnerCLI}")
    print(f"✓ _get_cli_class function exists: {hasattr(oricli_core.evaluation.test_runner, '_get_cli_class')}")
except Exception as e:
    signal.alarm(0)
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
