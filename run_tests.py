#!/usr/bin/env python3
"""
OricliAlpha Core Test Suite - CLI Wrapper
===================================
A high-performance wrapper for the OricliAlpha evaluation framework.
Supports both interactive and non-interactive (argument-based) execution.

Usage:
  # Run all tests
  ./run_tests.py

  # Run OricliAlpha's internal knowledge benchmark (Science, Logic, History)
  ./run_tests.py --internal-bench

  # Run tests for a specific module
  ./run_tests.py --module chain_of_thought

  # Enter interactive evaluation shell
  ./run_tests.py --interactive
"""

import sys
import os
import argparse

# Add current directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


def _maybe_reexec_in_venv() -> None:
    """Prefer the repo virtualenv automatically for consistent deps."""
    venv_python = os.path.join(BASE_DIR, ".venv", "bin", "python")
    if not os.path.exists(venv_python):
        return
    venv_root = os.path.join(BASE_DIR, ".venv")
    current = os.path.abspath(sys.executable)
    if current.startswith(os.path.join(venv_root, "bin") + os.sep):
        return
    os.execv(venv_python, [venv_python, os.path.abspath(__file__), *sys.argv[1:]])

# Unbuffer stdout for immediate feedback
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

def main():
    _maybe_reexec_in_venv()
    # If no arguments provided, we'll default to running all tests
    # unless the user wants to see help.
    
    # We use a custom parser to explain the most common options,
    # then we pass everything to the core test_runner.
    
    parser = argparse.ArgumentParser(
        description="OricliAlpha Core Test Suite Wrapper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False # We handle help manually to show BOTH wrapper and core options
    )
    
    # Wrapper-specific simplified args
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message")
    parser.add_argument("-i", "--interactive", action="store_true", help="Start interactive evaluation shell")
    parser.add_argument("-b", "--internal-bench", action="store_true", help="Run internal knowledge benchmark")
    parser.add_argument("-m", "--module", type=str, help="Filter by specific brain module")
    parser.add_argument("-c", "--category", type=str, help="Filter by test category")
    parser.add_argument("--skip-modules", action="store_true", help="Skip module discovery for faster startup")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    
    # Check for help
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print("\nAdvanced options are available in the core runner:")
        try:
            from oricli_core.evaluation.test_runner import main as core_main
            # Execute with --help to show full core options
            sys.argv = [sys.argv[0], "--help"]
            core_main()
        except Exception:
            parser.print_help()
        return

    try:
        from oricli_core.evaluation.test_runner import main as core_main
        
        # Only print header if not quiet
        if "--quiet" not in sys.argv:
            print("=" * 70, flush=True)
            print("OricliAlpha Core Evaluation System".center(70), flush=True)
            print(f"Time: {os.popen('date').read().strip()}".center(70), flush=True)
            print("=" * 70, flush=True)
            print(flush=True)
        
        # Call core main - it will handle the rest of the arguments
        core_main()
        
    except KeyboardInterrupt:
        print("\n\nTest run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
