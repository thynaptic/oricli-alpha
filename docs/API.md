# Oricli-Alpha API Reference

**Version:** 2.10.0 — Sovereign Extensions & MCP  
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

---

## Endpoints

### `POST /v1/chat/completions`
OpenAI-compatible chat endpoint with Sovereign extensions.

**Request:**
```json
{
  "model": "oricli-cognitive",
  "profile": "research_lead",
  "messages": [
    { "role": "user", "content": "Analyze the impact of MCP on agentic autonomy." }
  ],
  "stream": false
}
```

**Parameters:**

| Field | Type | Description |
|---|---|---|
| `model` | string | Standard model selector (e.g. `oricli-cognitive`, `oricli-swarm`) |
| `profile` | string | **New:** Hot-swap a sovereign profile (`.ori`) for this turn |
| `messages` | array | Chat history |

**Models / personas available via `model` field:**

| model | behaviour |
|---|---|
| `oricli-cognitive` | Default — full sovereign reasoning |
| `oricli-swarm` / `oricli-hive` | Routes query through the distributed Hive Swarm |
| `knowledge_assistant` | Conversational RAG over ingested knowledge |
| Any agent name | Activates a named agent profile from the factory |

---

### `POST /v1/swarm/run`
Routes a task directly to the Hive Swarm.

**Operations:**

#### `list_tools` — List all registered capabilities
Returns native tools and bridged MCP tools.
```bash
curl -s -X POST https://oricli.thynaptic.com/v1/swarm/run \
  -H "Authorization: Bearer $(cat /home/mike/Mavaia/.oricli/api_key)" \
  -H "Content-Type: application/json" \
  -d '{"operation": "list_tools"}'
```

#### `reason` — General logic & analysis
Utilizes MCTS/ToT based on query complexity.

---

## Autonomous Capabilities (MCP)

Oricli-Alpha autonomously bridges tools from external **Model Context Protocol (MCP)** servers. Discovered tools are automatically prefixed with the server name (e.g., `github_search_repos`) and injected into the system prompt.

**Configuring MCP Servers:**
MCP servers are defined in `oricli_core/mcp_config.json`. The backbone spawns these processes at boot and manages their lifecycle via JSON-RPC 2.0 over stdio.

---

## Sovereign Profiles (.ori)

Profiles are hot-swappable manifests that define the system's soul, rules, and instructions for a specific session.

**Location:** `oricli_core/profiles/*.ori`

**Usage via API:**
Pass the `profile` name (filename without extension) in the `/chat/completions` request to instantly reconfigure the engine.

---

## Response Metadata (Sovereign Trace)

Every response includes `usage` metadata containing real-time affective and cognitive metrics:

```json
"usage": {
  "resonance": 0.85,
  "mode": "E Major",
  "sensory": {
    "active_tone": "Deep Focus",
    "primary_color": "#3399FF",
    "secondary_color": "#994CFF",
    "opacity": "0.85",
    "pulse_rate": "1.00"
  }
}
```

---

*Oricli-Alpha — Sovereign Intelligence, Orchestrated at Scale.*  
*Source: `pkg/api/server_v2.go`, Caddy config `/etc/caddy/Caddyfile`*
