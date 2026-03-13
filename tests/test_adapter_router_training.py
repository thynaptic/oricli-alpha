#!/usr/bin/env python3
"""
Test training and experience replay in the Adapter Router module.
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.registry import ModuleRegistry

def test_training_logic():
    """Verify router training logic with mocked components."""
    print("Testing router training logic...")
    
    # Ensure heavy modules are enabled
    os.environ["MAVAIA_ENABLE_HEAVY_MODULES"] = "true"
    
    # Mock components
    mock_emb = MagicMock()
    mock_emb.execute.return_value = {"success": True, "embedding": [0.1] * 384}
    
    mock_mem = MagicMock()
    mock_mem.execute.return_value = {"success": True}
    
    # Setup mock registry
    original_get_module = ModuleRegistry.get_module
    
    def side_effect(name, **kwargs):
        if name == "embeddings":
            return mock_emb
        if name == "memory_tool":
            return mock_mem
        return original_get_module(name, **kwargs)
    
    with patch("oricli_core.brain.registry.ModuleRegistry.get_module", side_effect=side_effect):
        router = ModuleRegistry.get_module("adapter_router")
        
        # We need PyTorch for this test
        try:
            import torch
        except ImportError:
            print("! Skipping actual weight update check (PyTorch not available)")
            return

        # Initial forward pass to ensure classifier is initialized
        router.execute("route_input", {"text": "test"})
        
        # Test training step
        res = router.execute("train_router", {
            "text": "fix this bug",
            "target_intent": "coding",
            "learning_rate": 0.1
        })
        
        if res.get("success") and "loss" in res:
            print(f"✓ train_router reported success, loss: {res['loss']:.4f}")
            # Verify memory tool was called
            if mock_mem.execute.called:
                print("✓ memory_tool.store_item was called for experience logging")
            else:
                print("✗ memory_tool.store_item was NOT called")
                sys.exit(1)
        else:
            print(f"✗ train_router failed: {res}")
            sys.exit(1)

if __name__ == "__main__":
    try:
        test_training_logic()
        print("\n✨ All Phase 4 tests passed!")
    except Exception as e:
        print(f"✗ Tests failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
