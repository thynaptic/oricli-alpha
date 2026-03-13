#!/usr/bin/env python3
"""
Test script to diagnose server startup issues
"""
import sys
import traceback

print("=" * 60)
print("Testing server startup step by step...")
print("=" * 60)

# Step 1: Import check
print("\n[1] Testing imports...")
try:
    import uvicorn
    print("  ✓ uvicorn imported")
except Exception as e:
    print(f"  ✗ uvicorn import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    from fastapi import FastAPI
    print("  ✓ fastapi imported")
except Exception as e:
    print(f"  ✗ fastapi import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 2: Create app
print("\n[2] Testing app creation...")
try:
    from oricli_core.api.server import create_app
    print("  ✓ create_app imported")
except Exception as e:
    print(f"  ✗ create_app import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("  Creating app...")
    app = create_app()
    print(f"  ✓ App created with {len(app.routes)} routes")
except Exception as e:
    print(f"  ✗ App creation failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 3: Test OricliAlphaClient
print("\n[3] Testing OricliAlphaClient initialization...")
try:
    from oricli_core.client import OricliAlphaClient
    print("  ✓ OricliAlphaClient imported")
except Exception as e:
    print(f"  ✗ OricliAlphaClient import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("  Initializing OricliAlphaClient...")
    client = OricliAlphaClient()
    print("  ✓ OricliAlphaClient initialized")
except Exception as e:
    print(f"  ✗ OricliAlphaClient initialization failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 4: Test uvicorn startup (non-blocking test)
print("\n[4] Testing uvicorn configuration...")
try:
    import uvicorn
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8005,
        log_level="info",
    )
    print("  ✓ Uvicorn config created")
    print(f"  Config: host={config.host}, port={config.port}")
except Exception as e:
    print(f"  ✗ Uvicorn config failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("All startup checks passed!")
print("=" * 60)

