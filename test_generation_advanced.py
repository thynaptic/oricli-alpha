import sys
from pprint import pprint

from oricli_core.brain.registry import ModuleRegistry

def test_generation():
    print("=== OricliAlpha Text Generation Readiness Report ===")
    
    print("\n1. Initializing OricliAlpha Module Registry...")
    ModuleRegistry.discover_modules(verbose=False)
    
    print("\n2. Retrieving neural_text_generator module...")
    ntg = ModuleRegistry.get_module("neural_text_generator")
    
    if not ntg:
        print("Failed to retrieve neural_text_generator! Gap identified.")
        sys.exit(1)
        
    print("Initializing neural_text_generator...")
    ntg.initialize()
    
    print("\n3. Testing execution dependencies (TensorFlow/Keras)...")
    # Quick dummy call to check if TF drops an error right away
    mock_res = ntg.execute("generate_text", {"seed": "test", "length": 10})
    if mock_res.get("error") and "TensorFlow/Keras not available" in str(mock_res.get("error")):
        print("-> [GAP] TensorFlow/Keras is not installed in the environment.")
    else:
        print("-> [OK] TensorFlow dependencies appear to be available.")
        
    print("\n4. Checking Model State...")
    model_state = ntg.execute("get_model_info", {})
    if not model_state.get("success"):
        print("-> [ERROR] Failed to fetch model info:", model_state.get("error"))
    else:
        info = model_state.get("info", {})
        print(f"-> Character Model loaded: {info.get('char_model_loaded')}")
        print(f"-> Word Model loaded: {info.get('word_model_loaded')}")
        print(f"-> Transformer Model loaded: {info.get('transformer_model_loaded')}")
        
        if not any([info.get('char_model_loaded'), info.get('word_model_loaded'), info.get('transformer_model_loaded')]):
            print("-> [GAP] No neural models are currently loaded. Needs training or downloading.")
    
    print("\n5. Testing general cognitive_generator ...")
    cog_gen = ModuleRegistry.get_module("cognitive_generator")
    if cog_gen:
        print("-> [OK] cognitive_generator retrieved.")
        result = cog_gen.execute(
            operation="generate_response",
            params={
                "input": "Progress report.",
                "context": "",
                "persona": "oricli_standalone"
            }
        )
        if result.get("success"):
            print("-> [OK] cognitive_generator generated mock/fallback text:")
            print("\n" + result.get("text", ""))
            print("\n-> [GAP] cognitive_generator appears to be using a fallback echo generation method instead of a deep neural model.")
        else:
            print("-> [ERROR] cognitive_generator failed to generate.")
    
    print("\n=== End of Report ===")

if __name__ == "__main__":
    test_generation()
