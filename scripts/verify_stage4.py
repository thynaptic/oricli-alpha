import os
import sys
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Load the local core module
try:
    from oricli_core.brain.modules.neural_text_generator import NeuralTextGeneratorModule
except ImportError as e:
    print(f"Error importing OricliAlpha Core: {e}")
    sys.exit(1)

model_path = REPO_ROOT / "models" / "neural_text_generator_remote" / "curriculum" / "capability_hotpot_qa_20260302_220729" / "transformer" / "model"

print(f"--- Stage 4 Capability Verification ---")
print(f"Model Path: {model_path}")

try:
    # Initialize module
    module = NeuralTextGeneratorModule()
    module.initialize()
    
    # Load Stage 4 weights via execute
    print("[*] Loading model...")
    load_result = module.execute("load_model", {
        "model_type": "transformer",
        "transformer_config": {
            "model_name": str(model_path)
        }
    })
    
    if not load_result.get("success"):
        print(f"[✗] Failed to load model: {load_result.get('error')}")
        sys.exit(1)
    
    print("[✓] Model loaded successfully.")
    
    # Sample multi-hop reasoning prompt
    prompt = "Who was the director of the movie that won the Oscar for Best Picture in 1994?"
    print(f"\nPrompt: {prompt}")
    
    print("[*] Generating response...")
    gen_result = module.execute("generate_text", {
        "prompt": prompt,
        "model_type": "transformer",
        "max_length": 100,
        "temperature": 0.7
    })
    
    if gen_result.get("success"):
        print(f"\nResponse:\n{gen_result.get('text')}")
    else:
        print(f"\n[✗] Generation failed: {gen_result.get('error')}")
        
    print("\n--- Verification Complete ---")

except Exception as e:
    print(f"Error during verification: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
