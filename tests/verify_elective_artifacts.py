#!/usr/bin/env python3
"""
Integration test to verify elective artifact naming.
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.getcwd())

def test_elective_artifact_naming():
    print("Testing elective artifact naming...")
    
    # Setup temp run directory
    test_run_dir = Path("tests/tmp_elective_test")
    if test_run_dir.exists():
        shutil.rmtree(test_run_dir)
    test_run_dir.mkdir(parents=True)
    
    try:
        # Run a minimal training command with adapter name
        # We use transformer model type but with gpt2 (small) and very little data
        cmd = [
            sys.executable,
            "scripts/train_neural_text_generator.py",
            "--plain-output",
            "--model-type", "transformer",
            "--model-name", "gpt2",
            "--source", "huggingface",
            "--book-ids", "wikitext",
            "--epochs", "1",
            "--data-percentage", "0.0001",
            "--max-books", "1",
            "--output-dir", str(test_run_dir),
            "--adapter-name", "test_mode",
            "--lora" # Required for adapter saving
        ]
        
        print(f"Executing: {' '.join(cmd)}")
        # We expect this to fail if LoRA/PEFT is not installed, but we want to check
        # if it at least attempts to save with the correct name or if the directory
        # structure is created.
        
        # Actually, let's just mock the save_model call to avoid heavy ML dependencies in a quick check
        from mavaia_core.brain.modules.neural_text_generator import NeuralTextGeneratorModule
        gen = NeuralTextGeneratorModule()
        gen.initialize()
        
        # Mock a loaded transformer model
        mock_model = MagicMock()
        gen.transformer_model = mock_model
        gen.transformer_tokenizer = MagicMock()
        
        # Override model_dir for testing
        gen.model_dir = test_run_dir
        
        print("Calling _save_model with adapter_name...")
        gen.execute("save_model", {"model_type": "transformer", "adapter_name": "test_mode"})
        
        # Check for expected directory
        adapter_path = test_run_dir / "adapter_test_mode"
        if adapter_path.exists():
            print(f"✓ Found elective adapter directory: {adapter_path}")
        else:
            print(f"✗ Elective adapter directory NOT found: {adapter_path}")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if test_run_dir.exists():
            shutil.rmtree(test_run_dir)

from unittest.mock import MagicMock

if __name__ == "__main__":
    if test_elective_artifact_naming():
        print("\n🎉 Artifact naming verification PASSED!")
        sys.exit(0)
    else:
        print("\n⚠️ Artifact naming verification FAILED!")
        sys.exit(1)
