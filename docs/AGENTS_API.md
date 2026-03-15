# Oricli-Alpha External Agents API (Agent Factory)

## Overview
Oricli-Alpha allows you to dynamically craft specialized **Agents** by combining specific mindsets (**Skills**), guardrails (**Rules**), and tool access (**Modules**). This process is known as the **Agent Factory**.

With the **External Agents API**, you can create, update, list, and delete agent profiles from an external application (like your HUD). Once a profile is created, it can be instantly deployed in the Hive Swarm.

## 1. Using the REST API

All operations are available via the Native Sovereign API on port `8081` (default).

### List Agents
`GET /v1/agents`
Returns a list of all available agent profiles (Built-in + Custom).

### Create a New Agent (Factory)
`POST /v1/agents`
Define a new agent policy.

**Request:**
```json
{
  "name": "SecurityAuditor",
  "description": "Specialized agent for security analysis",
  "allowed_modules": ["web_search", "python_code_analysis", "shell_sandbox_service"],
  "skill_overlays": ["offensive_security", "technical_writer"],
  "system_instructions": "You are a strict security auditor. Focus on CVE detection.",
  "model_preference": "frob/qwen3.5-instruct"
}
```

### Update an Agent
`PUT /v1/agents/{agent_name}`
Modify an existing custom agent profile.

### Delete an Agent
`DELETE /v1/agents/{agent_name}`
Remove a custom agent profile from the factory.

---

## 2. Agent Discovery

Oricli-Alpha makes it easy to find and list all available agents (both built-in and custom).

### List via OpenAI-Compatible API
`GET /v1/models`
Returns all agents and modules. Custom factory agents are identified by `"owned_by": "oricli-factory"`.

### List via Native Agents API
`GET /v1/agents`
Returns the full detailed profile for every agent in the factory.

### List via Ollama Alias
`GET /api/tags`
Returns a list of models in the format expected by tools like **Continue** or **LlamaIndex**.

---

## 3. Using the Python Client

The `OricliAlphaClient` includes an `agents` namespace for the factory.

```python
from oricli_core.client import OricliAlphaClient

client = OricliAlphaClient(base_url="https://oricli.thynaptic.com", api_key="test_key")

# 1. Craft a new agent in the factory
client.agents.create({
    "name": "DataWizard",
    "description": "Expert at cleaning and plotting data",
    "allowed_modules": ["code_execution"],
    "skill_overlays": ["data_scientist"],
    "system_instructions": "Prioritize beautiful Matplotlib charts."
})

# 2. Deploy the agent in a Swarm session
response = client.chat.completions.create(
    model="DataWizard", # The model name matches our new agent's name
    messages=[{"role": "user", "content": "Analyze this CSV and plot the trends."}]
)
```

## 3. The Assembly Model
When you create an agent via the factory:
1. **Modules:** Defines the "body" (what tools it can touch).
2. **Skills:** Defines the "mind" (the `.ori` files that shape its persona and instructions).
3. **Rules:** Defines the "conscience" (global rules like `global_safety` that it must obey).

Custom agents are persisted in `oricli_core/data/custom_profiles.json` and are instantly recognized by the **Swarm Broker** during the bidding process.
