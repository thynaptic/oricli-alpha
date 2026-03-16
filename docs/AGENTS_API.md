# Oricli-Alpha External Agents API (Agent Factory)

## Overview
Oricli-Alpha allows you to dynamically craft specialized **Agents** by combining specific mindsets (**Skills**), guardrails (**Rules**), and tool access (**Modules**). This process is known as the **Agent Factory**.

With the **External Agents API**, you can create, update, list, and delete agent profiles. Once a profile is created, it is natively managed by the Go backbone and can be instantly deployed in the Hive Swarm.

## 1. Using the REST API

All operations are available via the Go-native Sovereign API on port `8089`.

### List Agents
`GET /v1/agents`
Returns a list of all active agent profiles (Go-native + Python sidecars).

### Create a New Agent (Factory)
`POST /v1/agents`
Define a new agent policy.

**Request:**
```json
{
  "name": "SecurityAuditor",
  "description": "Specialized agent for security analysis",
  "allowed_modules": ["web_fetch_service", "code_service", "shell_sandbox_service"],
  "skill_overlays": ["offensive_security", "technical_writer"],
  "system_instructions": "You are a strict security auditor. Focus on CVE detection.",
  "model_preference": "qwen2:1.5b"
}
```

### Update an Agent
`PUT /v1/agents/{agent_name}`
Modify an existing agent profile.

### Delete an Agent
`DELETE /v1/agents/{agent_name}`
Remove an agent profile from the factory.

---

## 2. Agent Discovery

Oricli-Alpha makes it easy to find and list all available agents through the Go backbone.

### List via OpenAI-Compatible API
`GET /v1/models`
Returns all agents and modules.

### List via Native Agents API
`GET /v1/agents`
Returns the full detailed profile for every agent in the factory.

### List via Ollama Alias
`GET /api/tags`
Returns a list of models in the format expected by tools like **Continue** or **LlamaIndex**.

---

## 3. Using the Python Client

The `OricliAlphaClient` proxies requests to the Go backbone.

```python
from oricli_core.client import OricliAlphaClient

client = OricliAlphaClient(base_url="http://localhost:8089", api_key="your_key")

# 1. Craft a new agent in the factory
client.agents.create({
    "name": "DataWizard",
    "description": "Expert at cleaning and plotting data",
    "allowed_modules": ["code_service"],
    "skill_overlays": ["data_scientist"],
    "system_instructions": "Prioritize beautiful Matplotlib charts."
})

# 2. Deploy the agent in a Swarm session
response = client.chat.completions.create(
    model="DataWizard", # The model name matches our new agent's name
    messages=[{"role": "user", "content": "Analyze this CSV and plot the trends."}]
)
```

## 4. Native Assembly Model
When you create an agent via the factory, the Go backbone natively orchestrates:
1. **Modules:** The "body" (routes to high-speed Go services or Python sidecars).
2. **Skills:** The "mind" (natively parsed `.ori` files shaping instructions).
3. **Rules:** The "conscience" (global Go-native safety rules).

Custom agents are persisted and instantly recognized by the **Go Swarm Broker** for high-speed parallel bidding.
