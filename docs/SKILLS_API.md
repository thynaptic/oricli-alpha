# Oricli-Alpha External Skills API

## Overview
Oricli-Alpha uses declarative `.ori` files to define dynamic skills. A skill encapsulates a specific persona, a mindset, required tools, and explicit instructions. Internally, the `skill_manager` parses these files and injects them into the execution context (like Swarm Nodes) based on trigger keywords.

With the **External Skills API**, you can dynamically create, update, list, and delete these skills from an external application (like a HUD or dashboard) without needing to modify the local file system.

## 1. Using the REST API

All operations are available via the Native Sovereign API on port `8081` (default).

### List Skills
`GET /v1/skills`
Returns a list of all loaded skills.

**Response:**
```json
{
  "success": true,
  "skills": [
    {
      "skill_name": "data_scientist",
      "description": "Expert data analysis...",
      "triggers": ["pandas", "statistics"],
      "requires_tools": ["shell_sandbox_service"],
      "mindset": "You are a Senior Data Scientist...",
      "instructions": "1. Always inspect the data..."
    }
  ]
}
```

### Get a Specific Skill
`GET /v1/skills/{skill_name}`
Retrieve details of a specific skill.

### Create a Skill
`POST /v1/skills`
Create a new `.ori` file and load it into memory.

**Request:**
```json
{
  "skill_name": "frontend_dev",
  "description": "Expert React and CSS developer.",
  "triggers": ["react", "css", "frontend"],
  "requires_tools": ["shell_sandbox_service"],
  "mindset": "You are a frontend expert...",
  "instructions": "Use modern React hooks..."
}
```

### Update a Skill
`PUT /v1/skills/{skill_name}`
Update an existing skill. The request body is the same as the creation endpoint.

### Delete a Skill
`DELETE /v1/skills/{skill_name}`
Remove a skill from the system.

---

## 2. Using the Python Client

The `OricliAlphaClient` includes a `skills` namespace to interact programmatically, both locally and remotely.

```python
from oricli_core.client import OricliAlphaClient

client = OricliAlphaClient(base_url="https://oricli.thynaptic.com")

# List all skills
skills = client.skills.list()
print([s["skill_name"] for s in skills])

# Create a new skill
new_skill = client.skills.create({
    "skill_name": "rust_engineer",
    "description": "Rust systems programmer",
    "triggers": ["rust", "cargo", "borrow checker"],
    "requires_tools": ["shell_sandbox_service"],
    "mindset": "You love memory safety and zero-cost abstractions.",
    "instructions": "1. Always run cargo clippy."
})

# Retrieve a specific skill
rust_skill = client.skills.get("rust_engineer")

# Update a skill
client.skills.update("rust_engineer", {
    "description": "Advanced Rust systems programmer",
    "triggers": ["rust", "cargo", "borrow checker", "unsafe"],
    "requires_tools": ["shell_sandbox_service"],
    "mindset": "You love memory safety.",
    "instructions": "1. Always run cargo clippy."
})

# Delete a skill
client.skills.delete("rust_engineer")
```

## 3. How Skills Are Used
Once a skill is created via the API, it is instantly available to the `skill_manager` and all components that rely on it (like Swarm Nodes and the `cognitive_generator`). 

If a user query matches one of the `triggers` defined in the skill, the `skill_manager` will automatically extract the `mindset` and `instructions` from the matched skill and inject them into the system prompt for that interaction.
