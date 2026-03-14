#!/usr/bin/env python3
"""
Test script for the Oricli Native API.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oricli_core.client import OricliAlphaClient

TEST_PORT = 8080

def test_goals():
    print("\n--- Testing Sovereign Goals ---")
    client = OricliAlphaClient(base_url=f"http://localhost:{TEST_PORT}")
    
    # 1. Create a goal
    goal_text = f"Test goal created at {time.ctime()}"
    print(f"Creating goal: {goal_text}")
    goal_id = client.goals.create(goal=goal_text, priority=2)
    print(f"Created goal ID: {goal_id}")
    
    # 2. List goals
    print("Listing goals...")
    goals = client.goals.list()
    print(f"Total goals: {len(goals)}")
    
    # 3. Get status
    print(f"Getting status for goal {goal_id}...")
    status = client.goals.get_status(goal_id)
    print(f"Goal status: {status['goal']['status']}, progress: {status['goal']['progress']}%")

def test_swarm():
    print("\n--- Testing Hive Swarm ---")
    client = OricliAlphaClient(base_url=f"http://localhost:{TEST_PORT}")
    
    # Since swarm_coordinator might not be fully functional in this env, we try to run it
    print("Triggering swarm collaboration...")
    try:
        # We use a simple query
        result = client.swarm.run(query="How to optimize a Python script?", max_rounds=1)
        print(f"Swarm run result success: {result.get('success')}")
        if result.get("session_id"):
            session_id = result.get("session_id")
            print(f"Swarm session ID: {session_id}")
            
            # Get session details
            print(f"Getting session details for {session_id}...")
            session = client.swarm.get_session(session_id)
            print(f"Session status: {session['status']}")
    except Exception as e:
        print(f"Swarm test skipped or failed (expected if module not ready): {e}")

def test_knowledge():
    print("\n--- Testing Knowledge Graph ---")
    client = OricliAlphaClient(base_url=f"http://localhost:{TEST_PORT}")
    
    print("Testing knowledge extraction...")
    try:
        text = "The Oricli-Alpha OS is a sovereign agent system developed by Mavaia."
        res = client.knowledge.extract(text=text)
        print(f"Extraction success: {res.get('success')}")
        
        # Get an entity ID from the extraction if possible, or use a known one
        entity_id = None
        if res.get("success") and res.get("triples"):
            entity_id = res["triples"][0].get("subject")
            
        if not entity_id:
            entity_id = "Oricli-Alpha"
            
        print(f"Querying knowledge graph for entity: {entity_id}...")
        query_res = client.knowledge.query(entity_id=entity_id)
        print(f"Query success: {query_res.get('success')}")
    except Exception as e:
        print(f"Knowledge test skipped or failed (expected if module not ready): {e}")

def test_ollama_aliases():
    print("\n--- Testing Ollama-style Aliases ---")
    import httpx
    
    base_url = f"http://localhost:{TEST_PORT}"
    
    # 1. /api/tags
    print("Testing /api/tags...")
    try:
        res = httpx.get(f"{base_url}/api/tags", timeout=10.0)
        if res.status_code == 200:
            models = res.json().get("models", [])
            print(f"Found {len(models)} models via Ollama alias")
        else:
            print(f"Failed /api/tags: {res.status_code}")
    except Exception as e:
        print(f"Ollama tags alias failed: {e}")
        
    # 2. /api/generate
    print("Testing /api/generate...")
    try:
        res = httpx.post(
            f"{base_url}/api/generate",
            json={"model": "oricli-cognitive", "prompt": "Say hello world.", "stream": False},
            timeout=30.0
        )
        if res.status_code == 200:
            resp_data = res.json()
            # Oricli's response structure for completions
            print(f"Ollama alias response: {resp_data['choices'][0]['message']['content'][:50]}...")
        else:
            print(f"Failed /api/generate: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Ollama generate alias failed: {e}")

if __name__ == "__main__":
    # Ensure modules are discovered
    from oricli_core.brain.registry import ModuleRegistry
    ModuleRegistry.discover_modules()
    
    test_goals()
    test_swarm()
    test_knowledge()
    test_ollama_aliases()
