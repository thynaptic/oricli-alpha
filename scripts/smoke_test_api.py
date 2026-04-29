#!/usr/bin/env python3
"""
ORI API Smoke Test Framework
Validates all major API categories including the Task Platform.

Usage:
  python3 smoke_test_api.py [--url http://localhost:8089/v1] [--key ori.<prefix>.<secret>]
"""

import argparse
import os
import requests
import json
import time
import sys
from typing import Dict, Any, Optional

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--url", default=os.environ.get("ORI_BASE_URL", "http://localhost:8089/v1"))
parser.add_argument("--key", default=os.environ.get("ORI_API_KEY", ""))
args, _ = parser.parse_known_args()

BASE_URL = args.url
API_KEY = args.key
HEADERS = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}

def print_test_start(name: str):
    print(f"\n[TEST] {name}...", end=" ", flush=True)

def print_result(success: bool, detail: str = ""):
    if success:
        print("✅ PASSED")
    else:
        print(f"❌ FAILED - {detail}")

def get(path: str) -> requests.Response:
    return requests.get(f"{BASE_URL}{path}", headers=HEADERS)

def post(path: str, body: dict) -> requests.Response:
    return requests.post(f"{BASE_URL}{path}", json=body, headers={**HEADERS, "Content-Type": "application/json"})

def patch(path: str, body: dict) -> requests.Response:
    return requests.patch(f"{BASE_URL}{path}", json=body, headers={**HEADERS, "Content-Type": "application/json"})

def delete(path: str) -> requests.Response:
    return requests.delete(f"{BASE_URL}{path}", headers=HEADERS)

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

# ─── Task Platform ─────────────────────────────────────────────────────────────

def test_task_crud() -> bool:
    print_test_start("Task CRUD (create / list / get / patch / delete)")
    task_id: Optional[str] = None
    try:
        # Create
        r = post("/tasks", {
            "title": "Follow up with plumber",
            "surface": "home",
            "priority": 2,
            "steps": [
                {"title": "Draft message", "action": "draft", "args": {"topic": "plumber callback"}, "order_num": 1}
            ]
        })
        assert r.status_code == 201, f"create status {r.status_code}: {r.text}"
        task_id = r.json()["id"]
        assert task_id, "no id in create response"

        # List
        r = get("/tasks?surface=home&limit=5")
        assert r.status_code == 200
        assert r.json().get("count", 0) >= 1

        # Get with steps
        r = get(f"/tasks/{task_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["title"] == "Follow up with plumber"
        assert len(data.get("steps", [])) >= 1, "steps not returned"

        # Patch
        r = patch(f"/tasks/{task_id}", {"priority": 5})
        assert r.status_code == 200
        assert r.json().get("priority") == 5

        print_result(True, f"task_id={task_id}")
        return True
    except Exception as e:
        print_result(False, str(e))
        return False
    finally:
        if task_id:
            delete(f"/tasks/{task_id}")

def test_task_steps() -> bool:
    print_test_start("Task Steps (add / patch / delete)")
    task_id: Optional[str] = None
    try:
        task_id = post("/tasks", {"title": "Steps test task", "surface": "api"}).json()["id"]

        # Add step
        r = post(f"/tasks/{task_id}/steps", {"title": "Research step", "action": "research", "order_num": 1})
        assert r.status_code == 201
        step_id = r.json()["id"]
        assert step_id

        # Patch step
        r = patch(f"/tasks/{task_id}/steps/{step_id}", {"status": "done", "result": "found some info"})
        assert r.status_code == 200
        assert "updated" in r.json()

        # Delete step
        r = delete(f"/tasks/{task_id}/steps/{step_id}")
        assert r.status_code == 200
        assert "deleted" in r.json()

        print_result(True)
        return True
    except Exception as e:
        print_result(False, str(e))
        return False
    finally:
        if task_id:
            delete(f"/tasks/{task_id}")

def test_task_execute_status() -> bool:
    print_test_start("Task Execute (GET status check)")
    task_id: Optional[str] = None
    try:
        task_id = post("/tasks", {"title": "Exec status test", "surface": "api"}).json()["id"]
        r = get(f"/tasks/{task_id}/execute")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data, f"no status field: {data}"
        print_result(True, f"status={data['status']}")
        return True
    except Exception as e:
        print_result(False, str(e))
        return False
    finally:
        if task_id:
            delete(f"/tasks/{task_id}")

def test_entity_lifecycle() -> bool:
    print_test_start("Entity lifecycle (upsert / event / get / search)")
    entity_id: Optional[str] = None
    try:
        # Upsert entity
        r = post("/entities", {"name": "Mike the Plumber", "kind": "vendor", "aliases": ["the plumber"]})
        assert r.status_code == 200
        entity_id = r.json()["id"]
        assert entity_id

        # Record event
        r = post(f"/entities/{entity_id}/events", {
            "kind": "invoice",
            "content": "Invoice #2024-08 — pipe repair $340",
            "metadata": {"amount": "340"}
        })
        assert r.status_code == 201
        ev_id = r.json()["id"]
        assert ev_id

        # Get with history
        r = get(f"/entities/{entity_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["entity"]["name"] == "Mike the Plumber"
        assert len(data.get("events", [])) >= 1, "event history not hydrated"

        # Search
        r = get("/entities?search=plumber")
        assert r.status_code == 200
        assert r.json().get("count", 0) >= 1

        print_result(True, f"entity_id={entity_id}, events={len(data.get('events', []))}")
        return True
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
    print(f"=== ORI API Smoke Test ===")
    print(f"Target: {BASE_URL}")
    print(f"Auth:   {'key set' if API_KEY else 'none (dev mode)'}\n")

    results = []

    print("── Core ──")
    results.append(test_health())
    results.append(test_health_detailed())
    results.append(test_chat_completions())
    results.append(test_swarm_run())
    results.append(test_ingestion_and_recall())
    results.append(test_agent_factory())
    results.append(test_metrics_and_traces())

    print("\n── Task Platform ──")
    results.append(test_task_crud())
    results.append(test_task_steps())
    results.append(test_task_execute_status())
    results.append(test_entity_lifecycle())

    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"\n=== Summary: {passed}/{total} tests passed ===")
    if passed < total:
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
