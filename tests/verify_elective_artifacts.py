#!/usr/bin/env python3
"""
Diagnostic script to verify that elective artifacts are correctly registered
with the AdapterRouter after a RunPod training session.
"""

import sys
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

def setup_mock_artifacts():
    """Create a mock structure that mimics RunPod output."""
    mock_dir = REPO_ROOT / "models" / "neural_text_generator_remote" / "curriculum" / "coding_task_20260306" / "final"
    mock_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a dummy adapter_config.json to signal it's a LoRA adapter
    (mock_dir / "adapter_config.json").write_text('{"base_model_name_or_path": "phi-3.5"}')
    print(f"✓ Created mock elective artifacts at: {mock_dir}")
    return mock_dir

def verify_registration():
    """Run the bridge registration logic and verify it hits the router."""
    print("\nVerifying registration logic...")
    
    # Import the registration function from the bridge
    from scripts.runpod_bridge import register_trained_adapters
    from mavaia_core.brain.registry import ModuleRegistry
    
    # Mock the AdapterRouter instance
    mock_router = MagicMock()
    
    with patch("mavaia_core.brain.registry.ModuleRegistry.get_module", return_value=mock_router):
        with patch("mavaia_core.client.MavaiaClient") as mock_client_cls:
            # Setup client mock
            mock_client = mock_client_cls.return_value
            mock_client.brain.adapter_router = mock_router
            
            # Trigger registration
            register_trained_adapters(REPO_ROOT)
            
            # Check if register_intent was called
            if mock_router.register_intent.called:
                args, kwargs = mock_router.register_intent.call_args
                intent = kwargs.get("intent")
                adapter_id = kwargs.get("adapter_id")
                print(f"✓ AdapterRouter.register_intent was called!")
                print(f"✓ Intent: {intent}")
                print(f"✓ Adapter Path: {adapter_id}")
                
                if intent == "coding" and "coding_task" in adapter_id:
                    print("✨ Verification SUCCESS: Bridge correctly identified and registered the elective.")
                else:
                    print(f"⚠ Verification PARTIAL: Found call but arguments differ from expected.")
            else:
                print("✗ Verification FAILED: register_intent was NOT called.")
                sys.exit(1)

def cleanup():
    """Remove mock artifacts."""
    shutil.rmtree(REPO_ROOT / "models" / "neural_text_generator_remote", ignore_errors=True)
    print("\n✓ Cleaned up mock artifacts.")

if __name__ == "__main__":
    setup_mock_artifacts()
    try:
        verify_registration()
    finally:
        cleanup()
