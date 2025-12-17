#!/usr/bin/env python3
"""
Diagnose Virtual Environment Issues
Checks for common venv problems and suggests fixes
"""

import sys
import os
import subprocess
from pathlib import Path

def check_venv():
    """Check virtual environment status"""
    print("=" * 80)
    print("Virtual Environment Diagnostic")
    print("=" * 80)
    print()
    
    # Check if we're in a venv
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if in_venv:
        print(f"✓ Currently in virtual environment: {sys.prefix}")
    else:
        print("✗ Not in a virtual environment")
        venv_path = Path.cwd() / ".venv"
        if venv_path.exists():
            print(f"  Found .venv directory at: {venv_path}")
            print(f"  Activate it with: source .venv/bin/activate")
        print()
        return
    
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print()
    
    # Check pip
    print("Checking pip...")
    try:
        import pip
        print(f"✓ pip module found: {pip.__version__}")
    except ImportError:
        print("✗ pip module not found")
        print("  Try: python3 -m ensurepip --upgrade")
        return
    
    # Try to run pip --version (with timeout)
    print("Testing pip command...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            timeout=5,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✓ pip command works: {result.stdout.strip()}")
        else:
            print(f"✗ pip command failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("✗ pip command hangs (timeout after 5 seconds)")
        print("  This indicates a broken pip installation")
        print("  Solution: Recreate the virtual environment")
    except Exception as e:
        print(f"✗ Error testing pip: {e}")
    
    print()
    
    # Check for common issues
    print("Checking for common issues...")
    
    # Check if pip is trying to use network
    pip_config = Path.home() / ".pip" / "pip.conf"
    if pip_config.exists():
        print(f"  Found pip config at: {pip_config}")
    
    # Check environment variables
    if "PIP_INDEX_URL" in os.environ:
        print(f"  PIP_INDEX_URL: {os.environ['PIP_INDEX_URL']}")
    
    print()
    print("=" * 80)
    print("Recommendations:")
    print("=" * 80)
    print()
    print("If pip is hanging, try:")
    print("  1. Recreate the virtual environment:")
    print("     rm -rf .venv")
    print("     python3 -m venv .venv")
    print("     source .venv/bin/activate")
    print("     python3 -m pip install --upgrade pip setuptools wheel")
    print()
    print("  2. Or use the fix script:")
    print("     ./scripts/fix_venv.sh")
    print()
    print("  3. If network is the issue, try offline mode:")
    print("     pip install --no-index --find-links <local_packages> <package>")
    print()

if __name__ == "__main__":
    check_venv()

