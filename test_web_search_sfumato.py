import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from oricli_core.brain.registry import ModuleRegistry

def test_minimal():
    print("Discovering modules...")
    ModuleRegistry.discover_modules()
    
    print("Getting web_search module...")
    ws = ModuleRegistry.get_module("web_search")
    if not ws:
        print("web_search module not found!")
        return
    
    print("Executing search for 'sfumato'...")
    res = ws.execute("search_web", {"query": "sfumato"})
    print(f"Result: {res}")

if __name__ == "__main__":
    test_minimal()
