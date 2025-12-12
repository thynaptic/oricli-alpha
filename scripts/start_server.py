#!/usr/bin/env python3
"""
Server Startup Script

Provides a convenient way to start the Mavaia API server with dependency checking.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_and_start():
    """Check dependencies and start server"""
    # Check critical dependencies
    try:
        import uvicorn
        import fastapi
    except ImportError as e:
        print(f"Error: Missing required dependency: {e.name}", file=sys.stderr)
        print("\nTo install dependencies, run:", file=sys.stderr)
        print("  pip install -e .", file=sys.stderr)
        sys.exit(1)
    
    # Import and start server
    try:
        from mavaia_core.api.server import main
        main()
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    check_and_start()

