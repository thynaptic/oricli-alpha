#!/usr/bin/env python3
"""
Test refined features of the Adapter Router module: Hot-Swap, LRU VRAM, and Async Triggers.
"""

import sys
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mavaia_core.brain.registry import ModuleRegistry

def test_lru_vram_management():
    """Verify that old adapters are unloaded when max_adapters is reached."""
    print("Testing LRU VRAM management...")
    
    os.environ["MAVAIA_ENABLE_HEAVY_MODULES"] = "true"
    
    # Mock NTG and PEFT model
    mock_ntg = MagicMock()
    mock_model = MagicMock()
    # Give it a type name that looks like PeftModel for the test logic if needed
    mock_ntg.transformer_model = mock_model
    
    # Mock PEFT model check
    mock_peft = MagicMock()
    
    with patch("mavaia_core.brain.registry.ModuleRegistry.get_module", return_value=mock_ntg):
        # Get actual router module and class
        import mavaia_core.brain.modules.adapter_router as ar_mod
        from mavaia_core.brain.modules.adapter_router import AdapterRouter
        
        # Inject mock into module globals
        ar_mod.PeftModel = mock_peft
        
        router = AdapterRouter()
        router.config["max_adapters"] = 2
        router.initialize()
        
        # Patch the internal _lazy_import_ml to prevent real peft import
        with patch("mavaia_core.brain.modules.adapter_router._lazy_import_ml"):
            # Targeted isinstance patch inside the router module
            original_isinstance = isinstance
            def isinstance_side_effect(obj, cls):
                if cls == mock_peft: # Checking against our mock PeftModel
                    return True
                return original_isinstance(obj, cls)

            with patch("mavaia_core.brain.modules.adapter_router.isinstance", side_effect=isinstance_side_effect):
                # Load 3 adapters (limit is 2)
                    router.execute("load_adapter", {"adapter_id": "adapter1"})
                    router.execute("load_adapter", {"adapter_id": "adapter2"})
                    
                    status = router.execute("status", {})
                    print(f"Active after 2 loads: {status['active_adapters']}")
                    
                    router.execute("load_adapter", {"adapter_id": "adapter3"})
                    
                    status = router.execute("status", {})
                    print(f"Active after 3rd load: {status['active_adapters']}")
                    
                    if "adapter1" not in status['active_adapters'] and len(status['active_adapters']) == 2:
                        print("✓ Oldest adapter 'adapter1' was correctly evicted")
                    else:
                        print(f"✗ LRU eviction failed: {status['active_adapters']}")
                        sys.exit(1)
                    
                    # Verify mock_model.delete_adapter was called
                    if mock_model.delete_adapter.called:
                        print("✓ model.delete_adapter was called to free VRAM")
                    else:
                        print("✗ model.delete_adapter was NOT called")
                        sys.exit(1)

def test_async_routing_trigger():
    """Verify that async_route triggers routing in the background."""
    print("\nTesting async routing trigger...")
    
    router = ModuleRegistry.get_module("adapter_router")
    
    # Mock _route_input to see if it's called
    with patch.object(router, "_route_input") as mock_route:
        res = router.execute("async_route", {"text": "next task content"})
        
        if res.get("status") == "triggered":
            print("✓ async_route reported triggered status")
        else:
            print(f"✗ async_route failed to trigger: {res}")
            sys.exit(1)
            
        # Give thread time to run
        time.sleep(0.5)
        
        if mock_route.called:
            print("✓ _route_input was called asynchronously in the background")
        else:
            print("✗ _route_input was NOT called by the background thread")
            sys.exit(1)

if __name__ == "__main__":
    try:
        test_lru_vram_management()
        test_async_routing_trigger()
        print("\n✨ All refinement tests passed!")
    except Exception as e:
        print(f"✗ Tests failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
