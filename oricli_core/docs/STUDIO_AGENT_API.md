# ORI Studio — Agent API Reference (STUDIO)

Status: Implementation Reference

This doc covers Studio-specific agent endpoints like workflows, pipelines, board, and notebook management.

For the core Go backbone agent integration (surfaces, profiles, etc.), see:
- [AGENT_API.md](/home/mike/Mavaia/docs/AGENT_API.md)

Base URL (production): `https://oricli.thynaptic.com`  
Base URL (local dev): `http://localhost:5001`

All endpoints are JSON-in / JSON-out unless noted.

---

## Authentication

Authentication is controlled by the upstream Go backbone (`MAVAIA_REQUIRE_AUTH`).  
The Flask UI proxy does **not** enforce its own auth by default — it forwards credentials through.

```
Authorization: Bearer <MAVAIA_API_KEY>
```

For local dev, auth is typically disabled. Production deployments must set `MAVAIA_API_KEY`.

---

## Chat Completions (OpenAI-compatible)

### `POST /chat`

OpenAI-compatible streaming chat. Proxied to `$MAVAIA_API_BASE/v1/chat/completions`.

**Extras over vanilla OpenAI:**
- Auto-injects RAG context from indexed connections (Notion, GitHub, HubSpot, Jira) when no system message is present
- Strips `<think>...</think>` blocks from the SSE stream (`_think_filter`)
- Converts plain-JSON backends to SSE if needed

```json
// Request
{
  "model": "claude-sonnet-4-6",       // passed through to backbone
  "messages": [
    {"role": "user", "content": "Summarise this week's issues"}
  ],
  "stream": true                       // default true
}
```

**Response (stream=true):** `text/event-stream` — standard OpenAI SSE delta chunks  
**Response (stream=false):** standard OpenAI completion JSON

**Attachment size limit:** 5 attachments / 20 MB per message — returns 400 on violation.

---

## Embeddings

### `POST /embeddings`

Proxied to `$MAVAIA_API_BASE/v1/embeddings`.

```json
// Request
{
  "input": "text to embed",
  "model": "text-embedding-3-small"
}
```

---

## Research

### `POST /research/stream`

Deep-research endpoint. Runs a multi-step web + RAG search, then streams a synthesised report.

```json
// Request
{
  "query": "Latest on EU AI Act enforcement",
  "mode": "deep"                // optional: "deep" | "quick"
}
```

**Response:** `text/event-stream` — SSE token stream of the final report.

---

## Agents / Skills / Rules

Agents are stored as `.ori` DSL files in `oricli_core/skills/`.

### `POST /agents/save`

Create or overwrite an agent from structured JSON.

```json
// Request
{
  "name": "Sales Researcher",
  "description": "Deep-dives on prospects",
  "triggers": ["research", "prospect"],
  "skills": ["web_search"],
  "rules": ["no_hallucination"],
  "mindset": "Be thorough. Cite sources.",
  "instructions": "When given a company name, search LinkedIn, their website, and recent news.",
  "constraints": "Do not fabricate employee counts."
}
```

```json
// Response
{
  "success": true,
  "path": "/home/mike/Mavaia/oricli_core/skills/sales_researcher.ori",
  "file": "sales_researcher.ori"
}
```

### `GET /agents/list`

Returns all `.ori` agent files parsed into UI-ready objects.

```json
// Response
{
  "agents": [
    {
      "id": "sales_researcher",
      "name": "Sales Researcher",
      "description": "Deep-dives on prospects",
      "systemPrompt": "...",     // compiled from mindset + instructions + constraints
      "emoji": "🤖",
      "triggers": ["research", "prospect"],
      "skills": ["web_search"],
      "rules": ["no_hallucination"]
    }
  ]
}
```

### `POST /skills/save`

Same as `/agents/save` but scoped to skill-only `.ori` files (no mindset block).

```json
// Request
{
  "name": "Web Fetch",
  "description": "Fetches and summarises a URL",
  "triggers": ["fetch", "browse"],
  "requires_tools": ["web_fetch"],
  "instructions": "Fetch the URL and return a clean markdown summary.",
  "constraints": "Max 2000 words."
}
```

### `POST /rules/save`

Saves a behavioural rule.

```json
// Request
{
  "name": "No Hallucination",
  "description": "Must cite source for every factual claim",
  "scope": "global",
  "categories": ["integrity", "safety"],
  "constraints": "If you don't know, say so. Never invent URLs or statistics."
}
```

---

## Workflows

### `GET /workflows`

List all workflows.

```json
// Response
{
  "workflows": [
    {
      "id": "wf_abc123",
      "name": "Weekly Report",
      "steps": [...],
      "trigger": { "webhookKey": "wk_xyz" }
    }
  ]
}
```

### `POST /workflows`

Create a new workflow.

### `PUT /workflows/<wf_id>`

Update a workflow.

### `DELETE /workflows/<wf_id>`

Delete a workflow and all associated run records.

### `POST /workflows/<wf_id>/run`

Manually trigger a workflow run.

```json
// Request (optional)
{
  "vars": { "topic": "AI regulation 2025" },
  "triggered_by": "manual"
}
```

```json
// Response
{
  "run_id": "8f3e...",
  "status": "queued"
}
```

### `GET /workflows/runs/<run_id>`

Poll a run.

```json
// Response
{
  "id": "8f3e...",
  "wf_id": "wf_abc123",
  "wf_name": "Weekly Report",
  "status": "done",            // queued | running | done | failed | cancelled | paused
  "steps": [...],
  "final_output": "...",
  "triggered_by": "manual",
  "created": "2026-04-04T09:00:00+00:00"
}
```

### `POST /workflows/runs/<run_id>/cancel`

Cancel a queued or running workflow.

### `POST /workflows/runs/<run_id>/pause` / `resume`

Pause / resume a running workflow at the next step boundary.

### `GET /workflows/<wf_id>/runs`

All runs for a specific workflow.

### `POST /workflows/webhook/<webhook_key>`

Trigger a workflow by webhook key. Pass optional `vars` in the request body.

```bash
curl -X POST https://oricli.thynaptic.com/workflows/webhook/wk_xyz \
  -H "Content-Type: application/json" \
  -d '{"vars": {"topic": "AI regulation"}}'
```

```json
// Response
{ "run_id": "8f3e...", "status": "queued" }
```

### `GET /workflows/<wf_id>/vars`

Returns variable schema extracted from a workflow's step prompts (used by the UI forms).

### `POST /workflows/ingest-doc`

Upload a document to be used as a workflow step context source.

---

## Pipelines (Visual Orchestration)

Pipelines are DAG-based orchestrations of multiple workflows.

### `GET /pipelines`
### `POST /pipelines`
### `PUT /pipelines/<pipe_id>`
### `DELETE /pipelines/<pipe_id>`

### `POST /pipelines/<pipe_id>/run`

Execute a pipeline. Steps are run in topological order.

```json
// Response
{ "run_id": "pipe_run_abc", "status": "running" }
```

### `GET /pipelines/runs/<run_id>`

Poll a pipeline run.

---

## Board

### `GET /api/board`

Returns all completed workflow runs enriched with title inference, type classification, and source badge — used by `BoardPage.jsx`.

```json
// Response
{
  "items": [
    {
      "id": "run_abc",
      "title": "EU AI Act Analysis",
      "type": "report",          // report | research | summary | draft | other
      "source": "email",         // email | manual | scheduled
      "wf_id": "wf_123",
      "wf_name": "Weekly Report",
      "triggered_by": "email:mike@thynaptic.com",
      "created": "2026-04-04T09:00:00+00:00",
      "output": "..."
    }
  ]
}
```

---

## Notes (Notebook)

### `POST /api/notes`

Create a note. `title` is optional — ORI auto-generates a 2–3 word title via Ollama if omitted.

```json
// Request
{
  "content": "The EU AI Act enforcement begins August 2026.",
  "title": ""                    // leave blank for auto-title
}
```

### `PATCH /api/notes/<note_id>`

Update content or title.

### `DELETE /api/notes/<note_id>`

Delete a note.

---

## MCP Servers

### `GET /mcp/servers`

List all configured MCP servers (enabled + disabled).

### `POST /mcp/servers`

Add a new MCP server.

```json
{
  "id": "github",
  "name": "GitHub MCP",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": { "GITHUB_TOKEN": "ghp_..." },
  "enabled": true
}
```

### `PUT /mcp/servers/<server_id>`

Update an MCP server config.

### `DELETE /mcp/servers/<server_id>`

Remove an MCP server.

### `POST /mcp/servers/<server_id>/toggle`

Toggle a server enabled/disabled without deleting it.

### `POST /mcp/reload`

Force-reload `mcp_config.json` from the current enabled server list.

---

## ORI DSL Compiler

### `POST /ori/compile`

Compile a `.ori` DSL source string into a workflow object.

```json
// Request
{ "source": "@name: Weekly Report\n@steps:\n..." }
```

### `GET /ori/decompile/<wf_id>`

Decompile a stored workflow back to `.ori` DSL source.

### `POST /ori/ai-assist`

AI-assisted workflow generation — describe what you want, ORI generates the `.ori` source.

```json
// Request
{ "prompt": "A workflow that fetches the top 5 HN stories and summarises them" }
```

---

## Search & RAG

### `GET /search?q=<query>`

DuckDuckGo-backed web search.

```json
// Response
{
  "results": [
    { "title": "...", "snippet": "...", "url": "..." }
  ]
}
```

### `GET /rag/search?q=<query>`
### `POST /rag/search`

Search the indexed RAG store (connections + uploaded docs).

```json
// Response
{
  "results": [
    {
      "title": "...",
      "snippet": "...",
      "source": "notion:My Workspace",
      "score": 0.91,
      "metadata": { "published": "2026-03-01" }
    }
  ]
}
```

---

## Memory

### `GET /api/v1/memories`

Returns all stored memories (long-term vector store entries).

---

## Health & Status

### `GET /health`

```json
{
  "status": "ok",
  "version": "...",
  "modules": 269,
  "eri": { "uptime_s": 14400, "load": 0.12 }
}
```

### `GET /api/eri`

Extended runtime info from the Go backbone (ERI = Engine Runtime Info).

### `GET /modules`

Lists all loaded brain modules from the Go backbone.

### `GET /models`

Lists available models (proxied from backbone `/v1/models`).

---

## Notes for Agent Developers

1. **Stream by default** — `/chat` defaults to `stream: true`. Pass `"stream": false` for non-streaming agents.
2. **Webhook triggers** — for event-driven integrations, assign a `webhookKey` to a workflow and `POST /workflows/webhook/<key>`.
3. **Polling runs** — after triggering a run, poll `GET /workflows/runs/<run_id>` every 2–5s until `status` is `done|failed|cancelled`.
4. **Variable injection** — pass runtime vars at trigger time via the `vars` body field; access them in workflow prompts as `{{var_name}}`.
5. **ORI DSL** — prefer `/ori/compile` over raw JSON for programmatic workflow creation. The DSL is the source-of-truth format.
6. **RAG context in chat** — send chat messages without a `system` role and ORI auto-injects relevant connection context. To suppress, include a `system` message (even an empty string).
