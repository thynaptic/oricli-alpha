# ORI Engine Quick Start

**Version:** v11.9.0 — Oracle-first, embeddings-only Ollama  
**Production URL:** `https://glm.thynaptic.com/v1`

---

## Prerequisites

- **Go 1.25+** — [install](https://go.dev/dl/)
- **Ollama** — [install](https://ollama.com). Pull embeddings only:
  ```bash
  ollama pull all-minilm
  ollama pull nomic-embed-text
  ```
  No reasoning models needed — all LLM calls route through Oracle (Anthropic API).

---

## 1. Run (Production — systemd)

The Go backbone and UI are managed as systemd services.

```bash
# Start the Go backbone (Hive Orchestrator, port 8089)
sudo systemctl start oricli-backbone

# Start the UI proxy (Flask, port 5000)
sudo systemctl start oricli-ui

# Check status
sudo systemctl status oricli-backbone oricli-ui
```

**Access:**
- API: `https://oricli.thynaptic.com` (via Caddy) or `http://localhost:8089` (local)
- UI: `http://localhost:5000`

---

## 2. Run (Development — manual)

```bash
# Build the Go backbone
go build -o bin/oricli-go-v2 ./cmd/oricli-engine

# Start it
./bin/oricli-go-v2
```

In a second terminal, start the UI proxy:
```bash
source .venv/bin/activate
MAVAIA_API_BASE=http://localhost:8089 python3 ui_app.py
```

---

## 3. Get Your API Key

```bash
cat /home/mike/Mavaia/.oricli/api_key
```

The key is auto-generated on first boot. Format: `glm.<prefix>.<secret>`.

---

## 4. First API Call

```bash
# Health check (no auth required)
curl https://oricli.thynaptic.com/v1/health

# Chat (auth required)
curl -X POST https://oricli.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer $(cat /home/mike/Mavaia/.oricli/api_key)" \
  -H "Content-Type: application/json" \
  -d '{"model":"oricli-oracle","messages":[{"role":"user","content":"Hello"}]}'
```

---

## 5. Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://oricli.thynaptic.com/v1",
    api_key=open("/home/mike/Mavaia/.oricli/api_key").read().strip()
)
response = client.chat.completions.create(
    model="oricli-oracle",
    messages=[{"role": "user", "content": "What can you do?"}]
)
print(response.choices[0].message.content)
```

---

## Full API Reference

See [`docs/API.md`](docs/API.md) for all endpoints, auth details, swarm operations, and ingestion.
