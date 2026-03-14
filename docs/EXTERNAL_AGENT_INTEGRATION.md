# External Agent Integration: Oricli-Alpha Sovereign API

## Overview
Oricli-Alpha is a **Sovereign Agent OS**. While she can run as a local library, she is designed to be orchestrated externally via her **Native REST API**. This document instructs other AI agents and developers on how to integrate Oricli's cognitive capabilities into external applications.

## 1. Connection & Authentication

### Base URL
- **Local:** `http://localhost:8081` (Port 8081 is the default for Oricli-Alpha Native API).
- **Production/Remote:** `https://api.oricli.com` (or your specific VPS IP).

### Authentication
All requests must include an `Authorization` header if `MAVAIA_API_KEY` is configured.
```http
Authorization: Bearer <your_api_key>
```

---

## 2. Using the Python Client (Dual-Mode)

The `OricliAlphaClient` is the recommended way to interact with Oricli. It supports a **Remote Mode** that routes all calls to the REST API instead of local modules.

### Initialization
```python
from oricli_core.client import OricliAlphaClient

# Remote Mode: Orchestrate Oricli across the network
client = OricliAlphaClient(
    base_url="https://oricli.thynaptic.com",
    api_key="your_secure_key"
)
```

---

## 3. Sovereign OS Functions

### A. Sovereign Goals (Multi-Day Persistence)
Command Oricli to execute long-horizon objectives.

**Python:**
```python
goal_id = client.goals.create(
    goal="Refactor the entire auth module to use JWT",
    priority=1
)
status = client.goals.get_status(goal_id)
print(f"Goal {goal_id} is currently: {status['goal']['status']}")
```

**REST API:**
`POST /v1/goals`
```json
{
  "goal": "Build a benchmark suite for the new RAG layer",
  "priority": 2
}
```

### B. The Hive Swarm (Decentralized Intelligence)
Trigger a collaborative session where 269+ micro-agents bid to solve a query.

**Python:**
```python
# Model name 'oricli-swarm' or 'oricli-hive' activates the Swarm Bus
response = client.chat.completions.create(
    model="oricli-swarm",
    messages=[{"role": "user", "content": "Analyze the security of this codebase."}]
)
```

**REST API:**
`POST /v1/swarm/run`
```json
{
  "query": "Optimize the database schema for high-throughput writes",
  "max_rounds": 3,
  "consensus_policy": "weighted_vote"
}
```

### C. Knowledge Graph (Persistent Relationships)
Extract and query structured entities from unstructured data.

**Python:**
```python
# 1. Extract relationships
client.knowledge.extract(text="Oricli-Alpha was developed by Mavaia in 2025.")

# 2. Multi-hop query via Neo4j
result = client.knowledge.query(entity_id="Oricli-Alpha", depth=2)
```

### D. Knowledge Companion (Casual RAG)
Discuss ingested knowledge in a natural, conversational way without providing strict directives.

**Python:**
```python
# Use the 'knowledge_assistant' model for a conversational guide to your data
response = client.chat.completions.create(
    model="knowledge_assistant",
    messages=[{"role": "user", "content": "Hey, what was in that research paper I uploaded?"}]
)
```

**REST API:**
`POST /v1/chat/completions`
```json
{
  "model": "knowledge_assistant",
  "messages": [{"role": "user", "content": "Tell me more about the project we discussed."}]
}
```

---

## 4. Ollama Parity & Compatibility

Oricli-Alpha provides **Ollama-style aliases** to enable instant integration with tools like **Continue**, **OpenWebUI**, or **LlamaIndex** without code changes.

- `POST /api/generate` -> Maps to Oricli's internal `cognitive_generator`.
- `POST /api/chat` -> Maps to Oricli's `chat.completions`.
- `GET /api/tags` -> Returns Oricli's module/agent profile list.

### Example: Continue Config (`config.json`)
```json
{
  "models": [
    {
      "title": "Oricli Sovereign",
      "provider": "ollama",
      "model": "oricli-cognitive",
      "apiBase": "https://oricli.thynaptic.com"
    }
  ]
}
```

---

## 5. Best Practices for External Agents

1. **Ollama-First Strategy:** Oricli offloads prose to her internal Ollama instance (`frob/qwen3.5-instruct 4B`). When calling Oricli, rely on her for **orchestration, tool-use, and graph reasoning**, rather than just raw text generation.
2. **Handle Timeouts:** Sovereign operations (like Swarm deliberation) can take time. Ensure your HTTP client has a timeout of at least **300s**.
3. **Use the Subconscious:** All API calls influence Oricli's `subconscious_field`. Repeated interactions build a "tonal bias" that improves context-awareness over time.
4. **Agent Profiles:** Use the `model` field in chat completions to specify a profile (e.g., `code_agent_profile`, `security_agent_profile`, `knowledge_assistant`) to constrain the Hive's bidding process.
