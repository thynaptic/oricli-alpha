#!/usr/bin/env python3
"""
Test discovery and basic functionality of the Adapter Router module.
"""

import sys
import os
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.registry import ModuleRegistry
from oricli_core.client import OricliAlphaClient

def test_discovery():
    """Verify that the adapter_router is discovered and registered."""
    print("Testing module discovery...")
    
    # Force discovery
    ModuleRegistry.discover_modules(verbose=True)
    
    # Check if adapter_router is in the registry
    module_names = ModuleRegistry.list_modules()
    
    if "adapter_router" in module_names:
        print("✓ adapter_router successfully discovered and registered")
    else:
        print("✗ adapter_router NOT found in ModuleRegistry")
        sys.exit(1)

def test_instantiation():
    """Verify that the adapter_router can be instantiated and basic operations work."""
    print("\nTesting module instantiation and basic operations...")
    
    # Get module instance
    router = ModuleRegistry.get_module("adapter_router")
    
    if router:
        print("✓ adapter_router instance retrieved")
    else:
        print("✗ Failed to get adapter_router instance")
        sys.exit(1)
        
    # Test 'status' operation
    status = router.execute("status", {})
    if status.get("success") and "active_adapters" in status:
        print("✓ 'status' operation successful")
    else:
        print(f"✗ 'status' operation failed: {status}")
        sys.exit(1)
        
    # Test 'route_input' operation (placeholder)
    route_res = router.execute("route_input", {"text": "test input"})
    if route_res.get("success") and "intent" in route_res:
        print("✓ 'route_input' operation successful")
    else:
        print(f"✗ 'route_input' operation failed: {route_res}")
        sys.exit(1)

def test_client_dispatch():
    """Verify that basic operations can be dispatched via OricliAlphaClient."""
    print("\nTesting client dispatch...")
    
    client = OricliAlphaClient()
    
    try:
        # Access module via proxy
        status = client.brain.adapter_router.status()
        if status.get("success"):
            print("✓ Client dispatch to 'status' successful")
        else:
            print(f"✗ Client dispatch to 'status' failed: {status}")
            sys.exit(1)
            
        # Access module via route_input
        route_res = client.brain.adapter_router.route_input(text="hello")
        if route_res.get("success"):
            print("✓ Client dispatch to 'route_input' successful")
        else:
            print(f"✗ Client dispatch to 'route_input' failed: {route_res}")
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ Client dispatch failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_discovery()
    test_instantiation()
    test_client_dispatch()
    print("\n✨ All Phase 1 tests passed!")
