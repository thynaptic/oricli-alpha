#!/usr/bin/env python3
"""
Test script for the External Rules API.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oricli_core.client import OricliAlphaClient

def test_rules_crud():
    print("\n--- Testing External Rules API ---")
    client = OricliAlphaClient(base_url="http://localhost:8089", api_key=None)
    
    rule_name = "test_rule_api"
    
    # 1. Create a rule
    print(f"Creating rule: {rule_name}...")
    try:
        new_rule = client.rules.create({
            "name": rule_name,
            "description": "Test rule created via API",
            "scope": "global",
            "categories": ["testing", "api"],
            "constraints": ["deny: test_module if time > 100"],
            "routing_preferences": ["prefer: test_module for testing"],
            "resource_policies": ["max_tests: 5"]
        })
        print(f"Create success: {new_rule.get('name') == rule_name}")
    except Exception as e:
        print(f"Failed to create rule: {e}")

    # 2. List rules
    print("Listing rules...")
    try:
        rules = client.rules.list()
        rule_names = [r["name"] for r in rules]
        print(f"Total rules: {len(rules)}")
        print(f"Found our new rule: {rule_name in rule_names}")
    except Exception as e:
        print(f"Failed to list rules: {e}")

    # 3. Get rule
    print(f"Getting details for {rule_name}...")
    try:
        rule = client.rules.get(rule_name)
        print(f"Rule categories: {rule.get('categories')}")
    except Exception as e:
        print(f"Failed to get rule: {e}")

    # 4. Update rule
    print(f"Updating rule {rule_name}...")
    try:
        updated_rule = client.rules.update(rule_name, {
            "description": "Updated test rule via API",
            "scope": "global",
            "categories": ["testing", "api", "updated"],
            "constraints": ["deny: test_module if time > 50"],
            "routing_preferences": ["prefer: test_module for testing"],
            "resource_policies": ["max_tests: 10"]
        })
        print(f"Update success, new categories: {updated_rule.get('categories')}")
    except Exception as e:
        print(f"Failed to update rule: {e}")

    # 5. Delete rule
    print(f"Deleting rule {rule_name}...")
    try:
        success = client.rules.delete(rule_name)
        print(f"Delete success: {success}")
        
        # Verify deletion
        rules = client.rules.list()
        rule_names = [r["name"] for r in rules]
        print(f"Rule truly deleted: {rule_name not in rule_names}")
    except Exception as e:
        print(f"Failed to delete rule: {e}")

if __name__ == "__main__":
    test_rules_crud()
