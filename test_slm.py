import sys
import logging
from mavaia_core.brain.modules.cognitive_generator import CognitiveGeneratorModule

logging.basicConfig(level=logging.INFO)

def run_test():
    generator = CognitiveGeneratorModule()
    
    # Needs a registry load to pick up modules correctly
    from mavaia_core.brain.registry import ModuleRegistry
    ModuleRegistry.discover_modules()

    print("=== TEST 1: Python Code ===")
    res = generator.execute("generate_response", {
        "input": "Write a python function that adds two numbers, and nothing else.",
        "context": ""
    })
    print("RES:", res.get("response", res))

    print("\n=== TEST 2: High Precision ===")
    res2 = generator.execute("generate_response", {
        "input": "I need you to list the colors of the rainbow, formatted as a JSON array.",
        "context": ""
    })
    print("RES 2:", res2.get("response", res2))

if __name__ == "__main__":
    run_test()
