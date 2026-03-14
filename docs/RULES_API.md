# Oricli-Alpha External Rules API

## Overview
Oricli-Alpha uses declarative `.ori` files to define global rules for safety, routing preferences, and resource policies. Internally, the `RulesEngine` parses these files and evaluates high-level contexts to enforce constraints and suggest execution pathways.

With the **External Rules API**, you can dynamically create, update, list, and delete these rules from an external application (like a HUD or dashboard) without needing to modify the local file system.

## 1. Using the REST API

All operations are available via the Native Sovereign API on port `8081` (default).

### List Rules
`GET /v1/rules`
Returns a list of all loaded rules.

**Response:**
```json
{
  "success": true,
  "rules": [
    {
      "name": "global_safety",
      "description": "Core safety and sandboxing constraints...",
      "scope": "global",
      "categories": ["safety"],
      "constraints": ["deny: shell_sandbox_service on paths outside /workspace and /tmp"],
      "routing_preferences": [],
      "resource_policies": []
    }
  ]
}
```

### Get a Specific Rule
`GET /v1/rules/{rule_name}`
Retrieve details of a specific rule.

### Create a Rule
`POST /v1/rules`
Create a new `.ori` rule file and load it into memory.

**Request:**
```json
{
  "name": "custom_routing",
  "description": "Custom routing rules for specific tasks.",
  "scope": "global",
  "categories": ["routing"],
  "constraints": [],
  "routing_preferences": ["prefer: code_agent for syntax_analysis"],
  "resource_policies": []
}
```

### Update a Rule
`PUT /v1/rules/{rule_name}`
Update an existing rule. The request body is the same as the creation endpoint.

### Delete a Rule
`DELETE /v1/rules/{rule_name}`
Remove a rule from the system.

---

## 2. Using the Python Client

The `OricliAlphaClient` includes a `rules` namespace to interact programmatically, both locally and remotely.

```python
from oricli_core.client import OricliAlphaClient

client = OricliAlphaClient(base_url="http://localhost:8081", api_key="your_key")

# List all rules
rules = client.rules.list()
print([r["name"] for r in rules])

# Create a new rule
new_rule = client.rules.create({
    "name": "strict_resources",
    "description": "Strict resource limits",
    "scope": "global",
    "categories": ["resources"],
    "constraints": [],
    "routing_preferences": [],
    "resource_policies": ["max_heavy_modules_per_request: 1"]
})

# Retrieve a specific rule
strict_rule = client.rules.get("strict_resources")

# Update a rule
client.rules.update("strict_resources", {
    "description": "Updated strict resource limits",
    "scope": "global",
    "categories": ["resources"],
    "constraints": [],
    "routing_preferences": [],
    "resource_policies": ["max_heavy_modules_per_request: 2"]
})

# Delete a rule
client.rules.delete("strict_resources")
```

## 3. How Rules Are Used
Once a rule is created via the API, it is instantly available to the `RulesEngine`.

Whenever Oricli-Alpha plans an execution path (e.g., via `strategic_planner` or `swarm_broker`), the `RulesEngine.evaluate_request` method is called to check the current context against all loaded constraints, routing preferences, and resource policies. This ensures that dynamic changes to rules instantly affect system behavior without a restart.
