#!/usr/bin/env python3
"""
End-to-end test for the Agent Factory and Hive Swarm integration.
"""

import sys
from pathlib import Path
import json
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oricli_core.client import OricliAlphaClient

def test_factory_swarm_flow():
    print("\n--- Testing Agent Factory -> Swarm Execution Flow ---")
    client = OricliAlphaClient(base_url="http://localhost:8080", api_key="test_key")
    
    agent_name = "FactoryRobot"
    
    # 1. Create a custom agent with a specific skill overlay
    print(f"1. Creating agent '{agent_name}' in the factory...")
    try:
        client.agents.create({
            "name": agent_name,
            "description": "A robot agent created by the factory",
            "allowed_modules": ["cognitive_generator", "skill_manager"],
            "skill_overlays": ["senior_python_dev"], # Using an existing skill
            "system_instructions": "You are a helpful factory robot.",
            "model_preference": "frob/qwen3.5-instruct"
        })
        print("   Agent created successfully.")
    except Exception as e:
        print(f"   Failed to create agent: {e}")
        return

    # 2. Verify agent is listed
    print("2. Verifying agent is listed in /v1/agents...")
    agents = client.agents.list()
    if any(a["name"] == agent_name for a in agents):
        print(f"   Found '{agent_name}' in the agent list.")
    else:
        print(f"   '{agent_name}' NOT found in the agent list.")
        return

    # 3. Execute a chat completion using the custom agent
    # This should trigger Swarm delegation with the FactoryRobot profile
    print(f"3. Executing chat completion with model='{agent_name}' (via Swarm)...")
    print("   Wait... the Hive is deliberating (this may take up to a minute)...")
    try:
        # We use a custom httpx client inside chat create, but we can't easily set timeout there
        # So we trust the 300s default we set in OricliAlphaClient
        response = client.chat.completions.create(
            model=agent_name,
            messages=[{"role": "user", "content": "Explain what a decorator is in Python."}],
            max_tokens=100
        )
        print("\n--- Response from FactoryRobot ---")
        print(response.choices[0].message.content)
        print("----------------------------------")
        print("   Swarm execution successful.")
    except Exception as e:
        print(f"   Swarm execution failed: {e}")

    # 4. Cleanup
    print(f"4. Deleting agent '{agent_name}'...")
    client.agents.delete(agent_name)
    print("   Cleanup complete.")

if __name__ == "__main__":
    test_factory_swarm_flow()
