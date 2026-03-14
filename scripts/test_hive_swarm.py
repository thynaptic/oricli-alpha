#!/usr/bin/env python3
"""
Test script for Distributed Swarm Intelligence (The Hive).
Verifies the Swarm Bus, Contract Net Protocol, and Hive Node integration.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oricli_core.client import OricliAlphaClient
from oricli_core.brain.swarm_bus import get_swarm_bus

def test_hive_delegation():
    print("\n--- Testing Hive Swarm Broker ---")
    client = OricliAlphaClient()
    
    # Get the swarm broker
    broker = client.brain.swarm_broker
    
    print("Delegating a test operation to the Swarm...")
    
    # We delegate an operation that many modules might support or a specific one
    # E.g., 'status' is supported by many, let's see who bids.
    # To test actual functionality, let's use a known module's operation like 'status'
    
    result = broker.delegate_task(
        operation="status", 
        params={},
        timeout=10.0,
        bid_timeout=2.0
    )
    
    print(f"Broker Result: {json.dumps(result, indent=2)}")
    
    print("\n--- Swarm Bus History ---")
    bus = get_swarm_bus()
    history = bus.get_history()
    for msg in history:
        print(f"[{msg.timestamp}] {msg.protocol.upper()} - Topic: {msg.topic} - Sender: {msg.sender_id}")
        if msg.protocol == "bid":
            print(f"  Bid: confidence {msg.payload.get('confidence')}, cost {msg.payload.get('compute_cost')}")

if __name__ == "__main__":
    from oricli_core.brain.registry import ModuleRegistry
    print("Warming up modules to spawn HiveNodes...")
    # Discover and initialize modules
    ModuleRegistry.discover_modules()
    
    # Force initialization of some modules to register their HiveNodes
    ModuleRegistry.get_module("swarm_broker")
    ModuleRegistry.get_module("cognitive_generator")
    ModuleRegistry.get_module("python_learning_system")
    
    test_hive_delegation()
