# Oracle Orchestration (Anthropic API)

The **Oracle** is ORI's primary reasoning lane. All LLM reasoning — chat, code, architecture, research, and vision — routes through Oracle. Local Ollama is retained only for embeddings (`all-minilm`, `nomic-embed-text`).

As of v11.12.0, the Oracle has migrated from the GitHub Copilot SDK to **Direct Anthropic API Integration** — HTTP/SSE streaming with no embedded daemon.

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
Oracle sends HTTP POST requests to the Anthropic API with SSE streaming — no daemon process, no port binding, no ACP protocol.
- **Location**: `pkg/oracle/oracle.go`
- **Endpoint**: `https://api.anthropic.com/v1/messages`
- **Auth**: `ANTHROPIC_API_KEY` environment variable
- **Streaming**: Server-Sent Events parsed via `bufio.Scanner`

### 2. Session Pool
Oracle maintains a lightweight session pool keyed by `tenantID:sessionID`.
- **Storage**: `sessionPool sync.Map` tracking `lastUsed` timestamps
- **TTL**: Sessions idle for 30 min are reaped by `sessionReaper()`
- **History**: Conversation history is passed by callers in the `messages` array — the Anthropic API receives full context natively, no system-prompt injection hack needed
- **Stateless mode**: Empty `sessionID` = one-shot, never pooled (used by Mise and similar surfaces)

---

## 🚀 Key Features

### Agent Personas (System Prompts)
Oracle loads agent personas from `.github/agents/*.agent.md` and injects them as system prompts.
- **Source**: `.github/agents/*.agent.md`
- **Loading**: YAML frontmatter parsed for `name`, `description`, `tools`; body becomes the system prompt
- **Cache**: 5-minute in-memory TTL via `cachedLoadCustomAgents()`
- **Selection**: ORI's router (`pkg/oracle/router.go`) selects the best agent — not the model

### Session Context
- **Pooled sessions**: Callers pass full message history; Oracle forwards to Anthropic natively
- **Stateless sessions**: One-shot with no persistent state — history is in the request
- **No `~/.copilot/` state** — all session management is ORI's responsibility

### Multi-Modal (Vision)
Oracle handles all image reasoning via Anthropic's vision API.
- **`POST /v1/vision/analyze`**: Routes through `oracleVisionAdapter` in `server_v2.go` → `AnalyzeImage()` → `https://api.anthropic.com/v1/messages` with base64 image content blocks
- **Model**: Defaults to `claude-sonnet-4-6`; override with `ORACLE_VISION_MODEL`

---

## 🛠️ Configuration & Development

### Environment Variables
- `ANTHROPIC_API_KEY`: **Required.** Direct API auth — Oracle returns an error string if unset.
- `ORACLE_COPILOT_MODEL_LIGHT`: Model for light chat (Default: `claude-haiku-4-5-20251001`)
- `ORACLE_COPILOT_MODEL_HEAVY`: Model for deep reasoning (Default: `claude-sonnet-4-6`)
- `ORACLE_COPILOT_MODEL_RESEARCH`: Model for research/dev (Default: `claude-sonnet-4-6`)
- `ORACLE_COPILOT_MODEL`: Global model override (all routes)
- `ORACLE_VISION_MODEL`: Vision-specific model override (Default: `claude-sonnet-4-6`)

### Adding Agent Personas
Create a Markdown file in `.github/agents/` with YAML frontmatter:
```markdown
---
name: my-new-agent
description: Expert at X, Y, and Z.
tools: [read, edit, execute]
---
Instructions for the agent as a system prompt...
```

### Debugging
Oracle logs are prefixed with `[Oracle]` or `[Oracle:Catalog]` in Oricli output.
- If requests fail, verify `ANTHROPIC_API_KEY` is set in the environment.
- Check `/tmp/oracle_model_cache.json` to see which models were selected at last startup.
- Vision errors log as `[Oracle:Vision]`.
