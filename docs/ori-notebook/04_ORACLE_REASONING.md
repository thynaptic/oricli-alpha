# Oracle Orchestration (Anthropic API)

The **Oracle** is ORI's primary reasoning lane. All LLM reasoning — chat, code, architecture, research, and vision — routes through Oracle. Local Ollama is retained only for embeddings (`all-minilm`, `nomic-embed-text`).

As of v11.12.0, Oracle migrated from the GitHub Copilot SDK to **Direct Anthropic API Integration** — HTTP/SSE streaming with no embedded daemon.

## 🏗️ Architecture

```
┌───────────────────────────┐
│      Oricli Engine        │
│  ┌─────────────────────┐  │
│  │   Oracle Router     │  │
│  │  (pkg/oracle/)      │  │
│  └─────────────────────┘  │
│             │             │
│             ▼             │
│  ┌─────────────────────┐  │
│  │  Direct HTTP/SSE    │──┼──► https://api.anthropic.com/v1/messages
│  │  (no daemon)        │  │
│  └─────────────────────┘  │
└───────────────────────────┘
    [Route Classification]
    [Agent System Prompts]
    [Session Pool (TTL reaping)]
    [Multi-Modal Vision]
```

### 1. Direct API Communication
Oracle sends HTTP POST to the Anthropic messages API with SSE streaming — no daemon, no port binding, no ACP protocol.
- **Location**: `pkg/oracle/oracle.go`
- **Endpoint**: `https://api.anthropic.com/v1/messages`
- **Auth**: `ANTHROPIC_API_KEY` environment variable
- **Streaming**: SSE parsed line-by-line via `bufio.Scanner`; `content_block_delta` events yield token strings

### 2. Route Classification
`pkg/oracle/router.go` classifies each request into one of four tiers:
- `RouteLightChat` — conversational, short turns → Haiku
- `RouteHeavyReasoning` — code, debug, architecture → Sonnet
- `RouteResearch` — deep investigation workflows → Sonnet
- `RouteImageReasoning` — visual input → vision-capable model

---

## 🚀 Key Features

### Agent Personas (System Prompts)
`.github/agents/*.agent.md` files are loaded and injected as system prompts per request.
- Agent is selected by ORI's router, not the model
- 5-minute disk-read cache via `cachedLoadCustomAgents()`

### Session Pool
Lightweight pool tracks `lastUsed` timestamps for TTL reaping (30 min idle).
- Callers pass full conversation history in the `messages` array — Anthropic receives it natively
- No `~/.copilot/session-state/` — state is ORI's responsibility
- Stateless mode (empty `sessionID`) = one-shot, never pooled

### Multi-Modal (Vision)
`AnalyzeImage()` posts base64 image content blocks to `https://api.anthropic.com/v1/messages`.
- Reachable via `POST /v1/vision/analyze`
- Model: `claude-sonnet-4-6` by default; override with `ORACLE_VISION_MODEL`

---

## 🛠️ Configuration

### Environment Variables
| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required.** Direct API auth |
| `ORACLE_COPILOT_MODEL_LIGHT` | `claude-haiku-4-5-20251001` | Light chat model |
| `ORACLE_COPILOT_MODEL_HEAVY` | `claude-sonnet-4-6` | Heavy reasoning model |
| `ORACLE_COPILOT_MODEL_RESEARCH` | `claude-sonnet-4-6` | Research model |
| `ORACLE_COPILOT_MODEL` | — | Global override (all routes) |
| `ORACLE_VISION_MODEL` | `claude-sonnet-4-6` | Vision-specific override |

### Debugging
- Logs prefixed `[Oracle]`, `[Oracle:Catalog]`, `[Oracle:Vision]`
- Verify `ANTHROPIC_API_KEY` is set if requests return `[Oracle: ANTHROPIC_API_KEY not configured]`
- Model selection cached to `/tmp/oracle_model_cache.json` (24h TTL)
