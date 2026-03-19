# Oricli-Alpha API Reference

**Version:** 2.1.0 — Go-Native Backbone  
**Maintainer:** Thynaptic Research

This is the single source of truth for the Oricli-Alpha API. Use it to integrate external applications, configure AI agents, or operate the system programmatically.

---

## Infrastructure

```
External Client
      │
      ▼  HTTPS (TLS — Cloudflare Origin Cert)
oricli.thynaptic.com  ──►  Caddy (port 443)
chat.thynaptic.com    ──►  Caddy (port 443)
      │
      ▼  HTTP (internal only)
127.0.0.1:8089  ──►  Go Backbone (ServerV2 / Gin)
      │
      ├─ GET  /v1/health            → public
      └─ POST /v1/*                 → authMiddleware → auth.Service (Argon2id)
```

| Property | Value |
|---|---|
| **Production URL** | `https://oricli.thynaptic.com` |
| **Alternate URL** | `https://chat.thynaptic.com` |
| **Internal port** | `8089` |
| **Protocol** | HTTPS externally, plain HTTP on localhost |
| **Auth** | Bearer token (`glm.<prefix>.<secret>` format) |
| **Key file** | `/home/mike/Mavaia/.oricli/api_key` |

---

## Authentication

All endpoints **except** `GET /v1/health` require a Bearer token.

```http
Authorization: Bearer <your_api_key>
```

**Get your key:**
```bash
cat /home/mike/Mavaia/.oricli/api_key
```

**Rotate the key:**
```bash
rm /home/mike/Mavaia/.oricli/api_key
sudo systemctl restart oricli-backbone
cat /home/mike/Mavaia/.oricli/api_key   # new key — update all consumers
```

> The key is auto-generated on first boot by `pkg/core/auth` and persisted across restarts. Format: `glm.<8-char-prefix>.<32-char-secret>`.

---

## Endpoints

### `GET /v1/health`
Public. No auth required. Use for uptime monitoring and readiness checks.

```bash
curl https://oricli.thynaptic.com/v1/health
```

**Response:**
```json
{ "status": "ready", "system": "oricli-alpha-v2", "pure_go": true }
```

---

### `POST /v1/chat/completions`
OpenAI-compatible chat endpoint. Drop-in replacement for `api.openai.com/v1/chat/completions`.

**Request:**
```json
{
  "model": "oricli-cognitive",
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user",   "content": "Explain the Hive Swarm architecture." }
  ],
  "stream": false
}
```

**Models / personas available via `model` field:**

| model | behaviour |
|---|---|
| `oricli-cognitive` | Default — full sovereign reasoning |
| `oricli-swarm` / `oricli-hive` | Routes query through the distributed Hive Swarm |
| `knowledge_assistant` | Conversational RAG over ingested knowledge |
| `oricli-fast` | Lightweight reflex mode (lower latency) |
| Any agent name | Activates a named agent profile from the factory |

**curl:**
```bash
curl -s -X POST https://oricli.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer $(cat /home/mike/Mavaia/.oricli/api_key)" \
  -H "Content-Type: application/json" \
  -d '{"model":"oricli-cognitive","messages":[{"role":"user","content":"Hello"}]}'
```

**Python — OpenAI SDK (recommended):**
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://oricli.thynaptic.com/v1",
    api_key=open("/home/mike/Mavaia/.oricli/api_key").read().strip()
)

response = client.chat.completions.create(
    model="oricli-cognitive",
    messages=[{"role": "user", "content": "What models are loaded?"}]
)
print(response.choices[0].message.content)
```

**JavaScript:**
```javascript
const key = "<your_api_key>";
const res = await fetch("https://oricli.thynaptic.com/v1/chat/completions", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${key}`,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    model: "oricli-cognitive",
    messages: [{ role: "user", content: "Hello from JS" }]
  })
});
const data = await res.json();
console.log(data.choices[0].message.content);
```

---

### `POST /v1/swarm/run`
Routes a task directly to the Hive Swarm — the distributed micro-agent network. Use this for operations that go beyond simple chat: reasoning, research, goal management, history retrieval, and more.

**Request shape:**
```json
{
  "operation": "<operation_name>",
  "params": { ... }
}
```

**Operations:**

#### `reason` — General logic & analysis
```bash
curl -s -X POST https://oricli.thynaptic.com/v1/swarm/run \
  -H "Authorization: Bearer $(cat /home/mike/Mavaia/.oricli/api_key)" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "reason",
    "params": {
      "query": "What are the performance tradeoffs of Go vs Python for LLM orchestration?",
      "complexity": 0.8
    }
  }'
```

#### `research_task` — Autonomous deep research
```json
{
  "operation": "research_task",
  "params": { "query": "Latest advances in retrieval-augmented generation" }
}
```

#### `solve_arc` — ARC-AGI benchmark (MCTS solver)
```json
{
  "operation": "solve_arc",
  "params": { "task": { "<arc_task_json>": "..." } }
}
```

#### `get_history` — Retrieve interaction history
```json
{
  "operation": "get_history",
  "params": { "limit": 10 }
}
```

#### `list_objectives` — List sovereign goals
```json
{
  "operation": "list_objectives",
  "params": { "status": "pending" }
}
```

#### `add_objective` — Create a sovereign goal
```json
{
  "operation": "add_objective",
  "params": {
    "goal": "Optimize Neo4j relationship traversal for temporal lookups.",
    "priority": 8
  }
}
```

#### `record_event` — Log a temporal event
```json
{
  "operation": "record_event",
  "params": { "description": "Deployed new RAG layer to production." }
}
```

> **Timeout note:** Swarm operations involving multi-round deliberation can take up to 300 seconds. Configure your HTTP client accordingly.

---

### `POST /v1/ingest`
Feed documents, text, or images into Oricli's long-term memory. Content is automatically chunked, embedded, and indexed for RAG across all Hive agents.

**Parameters (multipart/form-data):**

| Field | Type | Description |
|---|---|---|
| `file` | binary | PDF, TXT, MD, or image file |
| `text` | string | Raw text (alternative to `file`) |
| `source` | string | Optional label for the source |
| `tags` | JSON string | e.g. `["security", "research"]` |
| `domain` | string | Knowledge domain hint |

**Ingest a document:**
```bash
curl -X POST https://oricli.thynaptic.com/v1/ingest \
  -H "Authorization: Bearer $(cat /home/mike/Mavaia/.oricli/api_key)" \
  -F "file=@/path/to/document.pdf" \
  -F 'tags=["external","research"]' \
  -F "domain=security"
```

**Ingest raw text:**
```bash
curl -X POST https://oricli.thynaptic.com/v1/ingest \
  -H "Authorization: Bearer $(cat /home/mike/Mavaia/.oricli/api_key)" \
  -F "text=The new fusion reactor was successfully tested in Switzerland." \
  -F "source=lab_report_01"
```

**Ingest an image** (auto-transcribed by the vision agent before indexing):
```bash
curl -X POST https://oricli.thynaptic.com/v1/ingest \
  -H "Authorization: Bearer $(cat /home/mike/Mavaia/.oricli/api_key)" \
  -F "file=@/path/to/diagram.png;type=image/png"
```

---

### `POST /v1/ingest/web`
Crawl a URL and ingest all discovered pages into long-term memory.

**Request:**
```json
{
  "url": "https://example.com/docs",
  "max_pages": 10,
  "max_depth": 2,
  "metadata": { "project": "competitor-analysis" }
}
```

```bash
curl -X POST https://oricli.thynaptic.com/v1/ingest/web \
  -H "Authorization: Bearer $(cat /home/mike/Mavaia/.oricli/api_key)" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/docs","max_pages":10,"max_depth":2}'
```

---

## Error Reference

| HTTP | Meaning |
|---|---|
| `200` | Success |
| `400` | Malformed request body |
| `401` | Missing or invalid Bearer token |
| `404` | Unknown route |
| `500` | Internal execution error — check `backbone_os.log` |

---

## Python Client

Drop this into any project for quick integration:

```python
import requests

class OricliClient:
    def __init__(self, token: str, base_url: str = "https://oricli.thynaptic.com"):
        self.base = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def chat(self, message: str, model: str = "oricli-cognitive") -> str:
        r = requests.post(
            f"{self.base}/v1/chat/completions",
            headers=self.headers,
            json={"model": model, "messages": [{"role": "user", "content": message}]},
            timeout=120
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def swarm(self, operation: str, params: dict) -> dict:
        r = requests.post(
            f"{self.base}/v1/swarm/run",
            headers=self.headers,
            json={"operation": operation, "params": params},
            timeout=300
        )
        r.raise_for_status()
        return r.json()

    def ingest_url(self, url: str, max_pages: int = 5) -> dict:
        r = requests.post(
            f"{self.base}/v1/ingest/web",
            headers=self.headers,
            json={"url": url, "max_pages": max_pages},
            timeout=300
        )
        r.raise_for_status()
        return r.json()

    def ingest_text(self, text: str, source: str = "") -> dict:
        r = requests.post(
            f"{self.base}/v1/ingest",
            headers=self.headers,
            data={"text": text, "source": source},
            timeout=120
        )
        r.raise_for_status()
        return r.json()


# Usage
TOKEN = open("/home/mike/Mavaia/.oricli/api_key").read().strip()
client = OricliClient(TOKEN)

print(client.chat("What models are loaded?"))
print(client.swarm("reason", {"query": "Explain ARC-AGI", "complexity": 0.7}))
print(client.ingest_url("https://example.com/docs"))
```

---

## Tool / IDE Integration

Because `/v1/chat/completions` is OpenAI-compatible, Oricli works as a drop-in with:

**Continue (VS Code)** — add to `~/.continue/config.json`:
```json
{
  "models": [{
    "title": "Oricli Sovereign",
    "provider": "openai",
    "model": "oricli-cognitive",
    "apiBase": "https://oricli.thynaptic.com/v1",
    "apiKey": "<your_api_key>"
  }]
}
```

**OpenWebUI / any Ollama-compatible tool:**  
Use `https://oricli.thynaptic.com` as the Ollama base URL — the `/api/tags`, `/api/chat`, and `/api/generate` routes are aliased.

---

## Extended API (server.go)

The full extended router (`pkg/api/server.go`) is implemented and available for future activation. It exposes additional endpoint groups not yet wired into the production backbone:

| Group | Endpoints |
|---|---|
| **Agents** | `GET/POST /v1/agents`, `PUT/DELETE /v1/agents/:name` |
| **Skills** | `GET/POST /v1/skills`, `PUT/DELETE /v1/skills/:name` |
| **Rules** | `GET/POST /v1/rules`, `PUT/DELETE /v1/rules/:name` |
| **Knowledge** | `POST /v1/knowledge/extract`, `POST /v1/knowledge/query`, `GET/POST /v1/knowledge/world/*` |
| **Code Intelligence** | `POST /v1/code/review`, `/code/security/analyze`, `/codebase/search`, `/code/explain`, etc. |
| **Goals** | `GET/POST /v1/goals`, `GET /v1/goals/:id` |
| **Reasoning** | `POST /v1/reasoning/code`, `/reasoning/flow`, `/reasoning/thought_graph` |
| **Observability** | `GET /v1/metrics`, `/v1/traces`, `/v1/health/detailed` |

These are documented in `pkg/api/server.go` and will be activated as they are wired into the production backbone.

---

*Oricli-Alpha — Sovereign Intelligence, Orchestrated at Scale.*  
*Source: `pkg/api/server_v2.go`, Caddy config `/etc/caddy/Caddyfile`*
