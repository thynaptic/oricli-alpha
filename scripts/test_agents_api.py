#!/usr/bin/env python3
"""
Test script for the External Agents API (Agent Factory).
"""

import sys
from pathlib import Path
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oricli_core.client import OricliAlphaClient

def test_agents_crud():
    print("\n--- Testing External Agents API (Agent Factory) ---")
    client = OricliAlphaClient(base_url="http://localhost:8080", api_key="test_key")
    
    agent_name = "TestAgentFactory"
    
    # 1. Create an agent
    print(f"Creating agent: {agent_name}...")
    try:
        new_agent = client.agents.create({
            "name": agent_name,
            "description": "Test agent created via factory API",
            "allowed_modules": ["web_search", "code_execution"],
            "skill_overlays": ["senior_python_dev"],
            "system_instructions": "You are a factory-born agent. Be efficient.",
            "model_preference": "frob/qwen3.5-instruct"
        })
        print(f"Create success: {new_agent.get('name') == agent_name}")
    except Exception as e:
        print(f"Failed to create agent: {e}")

    # 2. List agents
    print("Listing agents...")
    try:
        agents = client.agents.list()
        agent_names = [a["name"] for a in agents]
        print(f"Total agents: {len(agents)}")
        print(f"Found our new agent: {agent_name in agent_names}")
    except Exception as e:
        print(f"Failed to list agents: {e}")

    # 3. Get agent
    print(f"Getting details for {agent_name}...")
    try:
        agent = client.agents.get(agent_name)
        print(f"Agent overlays: {agent.get('skill_overlays')}")
    except Exception as e:
        print(f"Failed to get agent: {e}")

    # 4. Update agent
    print(f"Updating agent {agent_name}...")
    try:
        updated_agent = client.agents.update(agent_name, {
            "description": "Updated factory agent",
            "allowed_modules": ["web_search", "code_execution", "shell_sandbox_service"],
            "skill_overlays": ["senior_python_dev", "technical_writer"],
            "system_instructions": "You are an updated factory-born agent.",
            "model_preference": "frob/qwen3.5-instruct"
        })
        print(f"Update success, new overlays: {updated_agent.get('skill_overlays')}")
    except Exception as e:
        print(f"Failed to update agent: {e}")

    # 5. Delete agent
    print(f"Deleting agent {agent_name}...")
    try:
        success = client.agents.delete(agent_name)
        print(f"Delete success: {success}")
        
        # Verify deletion
        agents = client.agents.list()
        agent_names = [a["name"] for a in agents]
        print(f"Agent truly deleted: {agent_name not in agent_names}")
    except Exception as e:
        print(f"Failed to delete agent: {e}")

if __name__ == "__main__":
    test_agents_crud()
