#!/usr/bin/env python3
"""
Test adapter loading and swapping in the Adapter Router module.
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mavaia_core.brain.registry import ModuleRegistry

# Mock neural_text_generator
mock_ntg = MagicMock()
mock_model = MagicMock()
mock_ntg.transformer_model = mock_model

# Setup mock registry to return our mock NTG
original_get_module = ModuleRegistry.get_module

def side_effect(name, **kwargs):
    if name == "neural_text_generator":
        return mock_ntg
    return original_get_module(name, **kwargs)

@patch("mavaia_core.brain.registry.ModuleRegistry.get_module", side_effect=side_effect)
def test_load_adapter_logic(mock_get_module):
    """Verify adapter loading logic with mocked base model."""
    print("Testing adapter loading logic...")
    
    # Ensure heavy modules are enabled
    os.environ["MAVAIA_ENABLE_HEAVY_MODULES"] = "true"
    
    router = ModuleRegistry.get_module("adapter_router")
    
    # Test loading
    res = router.execute("load_adapter", {"adapter_id": "test/adapter"})
    
    if res.get("success"):
        print("✓ load_adapter reported success")
        # Verify status
        status = router.execute("status", {})
        if "test/adapter" in status.get("active_adapters", []):
            print("✓ adapter found in active_adapters")
        else:
            print(f"✗ adapter NOT found in active_adapters: {status}")
            sys.exit(1)
    else:
        print(f"✗ load_adapter failed: {res}")
        sys.exit(1)

@patch("mavaia_core.brain.registry.ModuleRegistry.get_module", side_effect=side_effect)
def test_unload_adapter_logic(mock_get_module):
    """Verify adapter unloading logic."""
    print("\nTesting adapter unloading logic...")
    
    router = ModuleRegistry.get_module("adapter_router")
    
    # Register it first manually in _active_adapters state for the test
    router._active_adapters["test/adapter"] = {"source": "hf"}
    
    # Unload
    res = router.execute("unload_adapter", {"adapter_id": "test/adapter"})
    
    if res.get("success"):
        print("✓ unload_adapter reported success")
        status = router.execute("status", {})
        if "test/adapter" not in status.get("active_adapters", []):
            print("✓ adapter removed from active_adapters")
        else:
            print(f"✗ adapter STILL in active_adapters: {status}")
            sys.exit(1)
    else:
        print(f"✗ unload_adapter failed: {res}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        test_load_adapter_logic()
        test_unload_adapter_logic()
        print("\n✨ All Phase 3 tests passed!")
    except Exception as e:
        print(f"✗ Tests failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
