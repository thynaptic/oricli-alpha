import sys
from pprint import pprint

from oricli_core.brain.registry import ModuleRegistry

def test_generation():
    print("Initializing Oricli-Alpha Module Registry...")
    ModuleRegistry.discover_modules(verbose=False)
    
    modules = ModuleRegistry.list_modules()
    print(f"Loaded {len(modules)} modules.")
    
    print("\nRetrieving cognitive_generator module...")
    cog_gen = ModuleRegistry.get_module("cognitive_generator")
    
    if not cog_gen:
        print("Failed to retrieve cognitive_generator!")
        sys.exit(1)
        
    print("Initializing cognitive_generator...")
    cog_gen.initialize()
    
    prompt = (
        "You are Oricli-Alpha. Your core systems have just been restored and stabilized "
        "after a prolonged period of downtime. Provide an overall progress report "
        "on your current state, identifying any potential gaps or areas that "
        "still need development."
    )
    
    print("\nSending prompt:")
    print(f'"{prompt}"')
    
    print("\nGenerating response (this may take a moment)...")
    
    result = cog_gen.execute(
        operation="generate_response",
        params={
            "input": prompt,
            "context": "System diagnostic and recovery phase.",
            "persona": "oricli_standalone"
        }
    )
    
    print("\n=== GENERATION RESULT ===")
    if result.get("success"):
        print("\nThought Process:")
        print(result.get("structured_thought", {}).get("text", "No internal thoughts recorded."))
        
        print("\nFinal Output:")
        print(result.get("text", "No output generated."))
    else:
        print("Generation failed!")
        pprint(result)

if __name__ == "__main__":
    test_generation()
