#!/usr/bin/env python3
"""
Test routing accuracy and table management of the Adapter Router module.
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mavaia_core.brain.registry import ModuleRegistry
from mavaia_core.client import MavaiaClient

def test_intent_registration():
    """Verify that intents can be registered and listed."""
    print("Testing intent registration...")
    
    # Ensure heavy modules are enabled for torch
    os.environ["MAVAIA_ENABLE_HEAVY_MODULES"] = "true"
    
    router = ModuleRegistry.get_module("adapter_router")
    if not router:
        print("✗ Failed to get adapter_router instance")
        sys.exit(1)
        
    # Register a new intent
    res = router.execute("register_intent", {"intent": "coding", "adapter_id": "mavaia/python-lora"})
    if res.get("success") and res.get("intent") == "coding":
        print("✓ intent 'coding' registered")
    else:
        print(f"✗ Failed to register intent: {res}")
        sys.exit(1)
        
    # List intents
    list_res = router.execute("list_intents", {})
    if "coding" in list_res.get("intents", []) and list_res.get("routing_table", {}).get("coding") == "mavaia/python-lora":
        print("✓ intent 'coding' found in list and routing table")
    else:
        print(f"✗ intent 'coding' NOT found in list or table: {list_res}")
        sys.exit(1)

def test_routing_logic():
    """Verify routing logic with mocked embeddings."""
    print("\nTesting routing logic...")
    
    # Mock embeddings module
    mock_emb = MagicMock()
    # Ensure it returns the format AdapterRouter expects
    mock_emb.execute.return_value = {"success": True, "embedding": [0.1] * 384}
    
    # Setup mock registry to return our mock embedding module only for "embeddings"
    original_get_module = ModuleRegistry.get_module
    
    def side_effect(name, **kwargs):
        if name == "embeddings":
            return mock_emb
        return original_get_module(name, **kwargs)
    
    with patch("mavaia_core.brain.registry.ModuleRegistry.get_module", side_effect=side_effect):
        router = ModuleRegistry.get_module("adapter_router")
        
        # Register mapping
        router.execute("register_intent", {"intent": "math", "adapter_id": "mavaia/math-lora"})
        
        # Route input
        route_res = router.execute("route_input", {"text": "calculate 2+2"})
        
        if route_res.get("success") and "intent" in route_res:
            intent = route_res.get("intent")
            adapter = route_res.get("adapter_id")
            
            # Check if we got a real intent or a fallback
            if "Fallback" in route_res.get("metadata", {}).get("info", ""):
                print(f"✓ Input handled via fallback (expected without PyTorch)")
            else:
                print(f"✓ Input routed to intent: {intent}, adapter: {adapter}")
        else:
            print(f"✗ Routing failed: {route_res}")
            sys.exit(1)

def test_fallback():
    """Verify fallback to base model when embeddings fail."""
    print("\nTesting fallback logic...")
    
    router = ModuleRegistry.get_module("adapter_router")
    
    with patch.object(router, "_get_embeddings", return_value=None):
        route_res = router.execute("route_input", {"text": "something unknown"})
        
        if route_res.get("intent") == "general" and route_res.get("adapter_id") is None:
            print("✓ Correctly fell back to 'general' intent / None adapter")
        else:
            print(f"✗ Fallback failed: {route_res}")
            sys.exit(1)

if __name__ == "__main__":
    try:
        test_intent_registration()
        test_routing_logic()
        test_fallback()
        print("\n✨ All Phase 2 tests passed!")
    except Exception as e:
        print(f"✗ Tests failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
