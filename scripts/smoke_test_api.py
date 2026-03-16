#!/usr/bin/env python3
"""
Oricli-Alpha API Smoke Test Framework
Validates all major API categories for v0.5.0-alpha.
"""

import requests
import json
import time
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8089/v1"

def print_test_start(name: str):
    print(f"\n[TEST] {name}...", end=" ", flush=True)

def print_result(success: bool, detail: str = ""):
    if success:
        print("✅ PASSED")
    else:
        print(f"❌ FAILED - {detail}")

def test_health():
    print_test_start("System Health")
    try:
        resp = requests.get(f"{BASE_URL}/health")
        data = resp.json()
        success = resp.status_code == 200 and data.get("status") == "ready"
        print_result(success)
        return success
    except Exception as e:
        print_result(False, str(e))
        return False

def test_health_detailed():
    print_test_start("Detailed Health (Nervous System)")
    try:
        resp = requests.get(f"{BASE_URL}/health/detailed")
        data = resp.json()
        # Verify we have some modules
        success = resp.status_code == 200 and len(data) > 0
        print_result(success, f"Found {len(data)} modules")
        return success
    except Exception as e:
        print_result(False, str(e))
        return False

def test_chat_completions():
    print_test_start("Casual Conversation (OpenAI Alias)")
    try:
        payload = {
            "model": "oricli-swarm",
            "messages": [{"role": "user", "content": "Hello, who are you?"}],
            "temperature": 0.7
        }
        resp = requests.post(f"{BASE_URL}/chat/completions", json=payload)
        data = resp.json()
        success = resp.status_code == 200 and "choices" in data
        print_result(success)
        return success
    except Exception as e:
        print_result(False, str(e))
        return False

def test_swarm_run():
    print_test_start("Sovereign Hive (Swarm Run)")
    try:
        payload = {
            "operation": "reason",
            "params": {
                "query": "Explain the benefit of a Go-native backbone."
            }
        }
        resp = requests.post(f"{BASE_URL}/swarm/run", json=payload)
        data = resp.json()
        success = resp.status_code == 200 and data.get("success") == True
        print_result(success)
        return success
    except Exception as e:
        print_result(False, str(e))
        return False

def test_ingestion_and_recall():
    print_test_start("Ingestion & Recall (World Knowledge)")
    try:
        # 1. Add Fact
        payload = {
            "fact": "The secret code for the smoke test is BLAZE-2026.",
            "entities": ["smoke test", "code"],
            "confidence": 1.0
        }
        add_resp = requests.post(f"{BASE_URL}/knowledge/world/add", json=payload)
        if add_resp.status_code != 200:
            print_result(False, f"Add fact failed: {add_resp.status_code}")
            return False
        
        # 2. Recall (Query)
        query_resp = requests.get(f"{BASE_URL}/knowledge/world/query?query=BLAZE-2026")
        query_data = query_resp.json()
        facts = query_data.get("facts", [])
        if facts is None: facts = []
        success = query_resp.status_code == 200 and len(facts) > 0
        print_result(success, "Fact recalled" if success else "Fact not found")
        return success
    except Exception as e:
        print_result(False, str(e))
        return False

def test_agent_factory():
    print_test_start("Agent Factory (Lifecycle)")
    try:
        # 1. List
        resp = requests.get(f"{BASE_URL}/agents")
        if resp.status_code != 200:
            print_result(False, "Failed to list agents")
            return False
        
        # 2. Create (201 Created)
        new_agent = {
            "name": f"Tester_{int(time.time())}",
            "description": "Smoke test agent",
            "allowed_modules": ["code_service"]
        }
        create_resp = requests.post(f"{BASE_URL}/agents", json=new_agent)
        success = create_resp.status_code in [200, 201]
        print_result(success, f"Status {create_resp.status_code}")
        return success
    except Exception as e:
        print_result(False, str(e))
        return False

def test_metrics_and_traces():
    print_test_start("Introspection (Metrics & Traces)")
    try:
        m_resp = requests.get(f"{BASE_URL}/metrics")
        t_resp = requests.get(f"{BASE_URL}/traces")
        success = m_resp.status_code == 200 and t_resp.status_code == 200
        print_result(success)
        return success
    except Exception as e:
        print_result(False, str(e))
        return False

def run_all_tests():
    print("=== Oricli-Alpha v0.5.0-alpha Smoke Test (100% Target) ===")
    results = []
    results.append(test_health())
    results.append(test_health_detailed())
    results.append(test_chat_completions())
    results.append(test_swarm_run())
    results.append(test_ingestion_and_recall())
    results.append(test_agent_factory())
    results.append(test_metrics_and_traces())
    
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"\n=== Summary: {passed}/{total} tests passed ===")
    if passed < total:
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
