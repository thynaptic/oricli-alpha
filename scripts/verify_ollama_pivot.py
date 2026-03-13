
import os
import sys
import json
import requests
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from oricli_core.brain.modules.cognitive_generator import CognitiveGeneratorModule
from oricli_core.brain.modules.text_generation_engine import TextGenerationEngineModule

def verify_ollama_provider():
    print("--- Step 1: Verifying Ollama Provider Module ---")
    from oricli_core.brain.modules.ollama_provider import OllamaProviderModule
    provider = OllamaProviderModule()
    
    # Mock requests to avoid dependency on running Ollama during test
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {"response": "Hello from Ollama", "done": True}
        mock_post.return_value.status_code = 200
        
        res = provider.execute("generate", {"prompt": "Hi"})
        if res.get("success") and "Ollama" in res.get("text"):
            print("✓ Ollama Provider correctly proxied generation request.")
            return True
        else:
            print("✗ Ollama Provider failed.")
            return False

def verify_engine_integration():
    print("\n--- Step 2: Verifying Engine Integration ---")
    engine = TextGenerationEngineModule()
    engine._ensure_modules_loaded()
    
    # Mock the ollama_provider
    engine.ollama_provider = MagicMock()
    engine.ollama_provider.execute.return_value = {"success": True, "text": "Ollama response"}
    
    res = engine.execute("generate_with_neural", {"prompt": "Test"})
    if res.get("success") and res.get("method") == "ollama":
        print("✓ TextGenerationEngine correctly prioritized Ollama.")
        return True
    else:
        print("✗ Engine integration failed.")
        return False

def verify_generator_bypass():
    print("\n--- Step 3: Verifying Generator Instruction Bypass ---")
    cog_gen = CognitiveGeneratorModule()
    cog_gen._ensure_modules_loaded()
    
    # Mock ollama_provider
    cog_gen.ollama_provider = MagicMock()
    cog_gen.ollama_provider.execute.return_value = {
        "success": True, 
        "text": "This is a direct Ollama synthesis that is long enough to pass."
    }
    
    # Mock architect to see if it gets called (it SHOULD NOT if bypass works)
    cog_gen.pathway_architect = MagicMock()
    
    res = cog_gen.execute("generate_response", {"input": "Simple query"})
    
    if res.get("method") == "ollama_direct":
        print("✓ CognitiveGenerator successfully bypassed pipeline for direct Ollama synthesis.")
        if not cog_gen.pathway_architect.execute.called:
            print("✓ Verified: Expensive architect logic was skipped.")
            return True
    
    print("✗ Generator bypass failed.")
    return False

if __name__ == "__main__":
    try:
        if verify_ollama_provider() and verify_engine_integration() and verify_generator_bypass():
            print("\n✨ Ollama Strategic Pivot verified!")
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
