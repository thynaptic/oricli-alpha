import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from oricli_core.brain.registry import ModuleRegistry

def test_cog_gen():
    print("Discovering modules...")
    ModuleRegistry.discover_modules()
    
    print("Getting cognitive_generator module...")
    cg = ModuleRegistry.get_module("cognitive_generator")
    if not cg:
        print("cognitive_generator module not found!")
        return
    
    print("Executing generate_response for 'What is sfumato?'...")
    start_time = time.time()
    try:
        res = cg.execute("generate_response", {"input": "What is sfumato?"})
        duration = time.time() - start_time
        print(f"Result (took {duration:.2f}s): {res.get('text')}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cog_gen()
