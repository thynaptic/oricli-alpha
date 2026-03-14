#!/usr/bin/env python3
"""
Test script for the Decentralized Execution via OricliAlphaClient.
Verifies that passing model='oricli-swarm' drops the query onto the bus.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oricli_core.client import OricliAlphaClient
from oricli_core.brain.registry import ModuleRegistry

if __name__ == "__main__":
    print("Warming up modules to spawn HiveNodes...")
    ModuleRegistry.discover_modules()
    
    # Force initialization of some modules to register their HiveNodes
    ModuleRegistry.get_module("swarm_broker")
    ModuleRegistry.get_module("cognitive_generator")
    
    client = OricliAlphaClient()
    
    print("\n--- Testing Chat Completion via Swarm ---")
    try:
        response = client.chat.completions.create(
            model="oricli-swarm",
            messages=[{"role": "user", "content": "Explain the concept of Swarm Intelligence briefly."}],
            max_tokens=100
        )
        print(f"Response: {response.choices[0].message.content}")
        print("Success! Hive swarm handles generation.")
    except Exception as e:
        print(f"Failed: {e}")
