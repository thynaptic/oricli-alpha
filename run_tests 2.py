#!/usr/bin/env python3
"""
Simple wrapper script to run the Mavaia test suite
Usage: python3 run_tests.py [--module MODULE] [--category CATEGORY] [--skip-modules]
"""

import sys
import os

# Check for help flags FIRST, before any expensive imports
if '--help' in sys.argv or '-h' in sys.argv:
    # Import and call main directly - it will handle help quickly
    # The lazy imports we added should prevent discovery during import
    pass  # Fall through to import and show full help

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Unbuffer stdout for immediate output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

# Also try to set unbuffered mode
try:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1)
except Exception:
    pass  # If it fails, continue anyway

try:
    from mavaia_core.evaluation.test_runner import main
    
    # Only print header if not showing help
    if '--help' not in sys.argv and '-h' not in sys.argv:
        print("=" * 60, flush=True)
        print("Mavaia Core Test Suite", flush=True)
        print("=" * 60, flush=True)
        print(flush=True)
    
    main()
except KeyboardInterrupt:
    print("\n\nTest run interrupted by user", flush=True)
    sys.exit(130)
except Exception as e:
    print(f"\n\nERROR: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
