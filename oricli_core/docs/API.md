# ORI Studio — Flask UI API Reference

**Base URL (local):** `http://localhost:5001`  
**Base URL (production):** `https://oristudio.thynaptic.com`  
**Source:** `ui_app.py`  
**Auth:** `Authorization: Bearer <MAVAIA_API_KEY>` (most routes — see per-route notes)

---

## Table of Contents

1. [System](#system)
2. [Chat & Inference](#chat--inference)
3. [Workflows](#workflows)
4. [Pipelines](#pipelines)
5. [Tasks](#tasks)
6. [Email System](#email-system)
7. [Board](#board)
8. [Notebook](#notebook)
9. [Connections & Integrations](#connections--integrations)
10. [MCP Servers](#mcp-servers)
11. [Memory & RAG](#memory--rag)
12. [Sovereign Goals](#sovereign-goals)
13. [Documents](#documents)
14. [Daemons](#daemons)
15. [Admin](#admin)

---

## System

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Liveness check. Returns `ok`, `backbone`, `ollama`, `api_base`. |
| `GET` | `/api/eri` | None | ERI status (Extended Runtime Interface). |
| `GET` | `/models` | None | Lists available models from backbone + Ollama. |
| `GET` | `/modules` | None | Lists registered brain modules. |

**Health response:**
```json
{
  "ok": true,
  "backbone": true,
  "ollama": true,
  "api_base": "http://localhost:8089",
  "ollama_base": "http://localhost:11434"
}
```

---

## Chat & Inference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/chat` | Bearer | OpenAI-compatible chat completions proxy to Go backbone. |
| `POST` | `/embeddings` | Bearer | Text embedding proxy. |
| `POST` | `/images/generations` | Bearer | Image generation (async job). |
| `GET` | `/images/status/<job_id>` | Bearer | Poll image job status. |
| `GET` | `/search` | Bearer | RAG search. Query: `?q=text&limit=10` |
| `POST` | `/research/stream` | Bearer | Streaming deep research. SSE response. |

**Chat request:**
```json
{
  "model": "oricli-cognitive",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}
```

---

## Workflows

Workflows are named, multi-step pipelines. Steps can be `fetch`, `prompt`, `code`, `notify`, `condition`, `loop`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/workflows` | Bearer | List all workflows. |
| `POST` | `/workflows` | Bearer | Create workflow. |
| `PUT` | `/workflows/<wf_id>` | Bearer | Update workflow. |
| `DELETE` | `/workflows/<wf_id>` | Bearer | Delete workflow. |
| `POST` | `/workflows/<wf_id>/run` | Bearer | Trigger a run. |
| `GET` | `/workflows/<wf_id>/runs` | Bearer | List runs for a workflow. |
| `GET` | `/workflows/<wf_id>/vars` | Bearer | Get workflow variable definitions. |
| `GET` | `/workflows/runs/<run_id>` | Bearer | Get a specific run. |
| `POST` | `/workflows/runs/<run_id>/cancel` | Bearer | Cancel a run. |
| `POST` | `/workflows/runs/<run_id>/pause` | Bearer | Pause a running workflow. |
| `POST` | `/workflows/runs/<run_id>/resume` | Bearer | Resume a paused workflow. |
| `POST` | `/workflows/webhook/<webhook_key>` | None | Webhook trigger (key in URL). |
| `POST` | `/workflows/ingest-doc` | Bearer | Ingest a document into a workflow run. |
| `POST` | `/ori/compile` | Bearer | Compile `.ori` DSL to workflow JSON. |
| `GET` | `/ori/decompile/<wf_id>` | Bearer | Decompile workflow back to `.ori` DSL. |
| `POST` | `/ori/ai-assist` | Bearer | AI auto-complete for `.ori` editor. |

**Run trigger body:**
```json
{
  "user_vars": {"client": "Acme", "amount": "$4,200"},
  "doc_text": "",
  "triggered_by": "manual"
}
```

**Run record shape:**
```json
{
  "id": "uuid",
  "wf_id": "uuid",
  "wf_name": "Claude Overview",
  "status": "queued | running | done | error | cancelled",
  "steps": [...],
  "created": "ISO8601",
  "started": "ISO8601",
  "finished": "ISO8601",
  "final_output": "...",
  "triggered_by": "manual | email:user@example.com | schedule:..."
}
```

---

## Pipelines

Lightweight sequential pipelines (simpler than workflows).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/pipelines` | Bearer | List pipelines. |
| `POST` | `/pipelines` | Bearer | Create pipeline. |
| `PUT` | `/pipelines/<pipe_id>` | Bearer | Update pipeline. |
| `DELETE` | `/pipelines/<pipe_id>` | Bearer | Delete pipeline. |
| `POST` | `/pipelines/<pipe_id>/run` | Bearer | Run a pipeline. |
| `GET` | `/pipelines/runs/<run_id>` | Bearer | Get pipeline run. |

---

## Tasks

Scheduled or one-shot tasks.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/tasks` | Bearer | List tasks. |
| `POST` | `/tasks` | Bearer | Create task. |
| `DELETE` | `/tasks/<task_id>` | Bearer | Delete task. |
| `POST` | `/tasks/<task_id>/run` | Bearer | Run task immediately. |

---

## Email System

Full reference: [`EMAIL.md`](EMAIL.md)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/v1/email/send` | Bearer | Send a transactional email via Resend. |
| `GET` | `/v1/email/clients` | Bearer | List authorized inbound clients. |
| `POST` | `/v1/email/clients` | Bearer | Register an authorized sender. |
| `DELETE` | `/v1/email/clients/<email>` | Bearer | Remove an authorized sender. |
| `POST` | `/v1/email/register` | None | Auto-register on signup (called by frontend). |
| `POST` | `/v1/email/briefing/<email>` | Bearer | Trigger a briefing email immediately. |
| `POST` | `/v1/email/inbound` | Svix | Resend inbound webhook. |

---

## Board

The Board shows completed workflow runs with their output. Auto-populates from any run with `final_output`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/board` | None | Returns all `done` runs with output, title, type, source. |

**Response:**
```json
{
  "items": [
    {
      "id": "run-uuid",
      "wf_id": "wf-uuid",
      "wf_name": "Claude Overview",
      "type": "research",
      "source": "email",
      "snippet": "First 200 chars of output...",
      "output": "Full output up to 8000 chars...",
      "created": "ISO8601",
      "finished": "ISO8601"
    }
  ]
}
```

**Type values:** `report`, `research`, `summary`, `draft`, `other`  
**Source values:** `email`, `manual`, `scheduled`

---

## Notebook

Server-side notes store. Persisted to `.oricli/notes.json`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/notes` | None | List all notes. |
| `POST` | `/api/notes` | None | Create a note. Body: `{title, content}` |
| `PATCH` | `/api/notes/<note_id>` | None | Update a note. Body: `{title?, content?}` |
| `DELETE` | `/api/notes/<note_id>` | None | Delete a note. |

Note IDs are millisecond timestamps as strings (matches `Date.now().toString()` from the frontend).

---

## Connections & Integrations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/connections` | Bearer | List all connections. |
| `PUT` | `/api/connections/<conn_id>` | Bearer | Create/update a connection. |
| `DELETE` | `/api/connections/<conn_id>` | Bearer | Delete a connection. |
| `POST` | `/api/connections/<conn_id>/test` | Bearer | Test a connection's credentials. |
| `POST` | `/api/connections/<conn_id>/index` | Bearer | Trigger indexing (e.g. Notion, Drive). |
| `GET` | `/api/connections/index/status` | Bearer | Get indexing status across all connections. |
| `GET` | `/api/connections/oauth/authorize/google` | Bearer | Start Google OAuth flow. |
| `GET` | `/api/connections/oauth/callback/google` | None | OAuth callback (redirect). |
| `POST` | `/api/connections/telegram/webhook` | None | Telegram bot webhook receiver. |
| `GET` | `/api/slack-integrations` | Bearer | List Slack integration configs. |
| `GET` | `/api/teams-integrations` | Bearer | List Teams integration configs. |
| `GET` | `/api/notion/templates` | Bearer | List available Notion templates. |
| `POST` | `/api/notion/build` | Bearer | Build a Notion page from a template. |

---

## MCP Servers

Model Context Protocol server management.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/mcp/servers` | Bearer | List configured MCP servers. |
| `POST` | `/mcp/servers` | Bearer | Add an MCP server. |
| `PUT` | `/mcp/servers/<server_id>` | Bearer | Update an MCP server. |
| `DELETE` | `/mcp/servers/<server_id>` | Bearer | Remove an MCP server. |
| `POST` | `/mcp/servers/<server_id>/toggle` | Bearer | Enable/disable a server. |
| `POST` | `/mcp/reload` | Bearer | Reload all MCP server configs. |

---

## Memory & RAG

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET/POST` | `/rag/search` | Bearer | Vector search over indexed content. |
| `GET` | `/api/v1/memories` | Bearer | List memory entries. |
| `GET` | `/api/v1/memories/knowledge` | Bearer | List knowledge base entries. |
| `POST` | `/api/v1/documents/upload` | Bearer | Upload a document for ingestion. |
| `GET` | `/api/v1/documents` | Bearer | List ingested documents. |

---

## Sovereign Goals

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/goals` | Bearer | List goals (proxy to backbone). |
| `POST` | `/api/v1/goals` | Bearer | Create a goal. |
| `PUT` | `/api/v1/goals/<goal_id>` | Bearer | Update a goal. |
| `DELETE` | `/api/v1/goals/<goal_id>` | Bearer | Delete a goal. |
| `GET` | `/api/v1/sovereign/goals` | Bearer | List sovereign (long-running) goals. |
| `POST` | `/api/v1/sovereign/goals` | Bearer | Create a sovereign goal. |
| `GET` | `/api/v1/sovereign/goals/<goal_id>` | Bearer | Get a sovereign goal. |
| `DELETE` | `/api/v1/sovereign/goals/<goal_id>` | Bearer | Delete a sovereign goal. |
| `GET` | `/api/v1/sovereign/identity` | Bearer | Get ORI's sovereign identity config. |
| `PUT` | `/api/v1/sovereign/identity` | Bearer | Update sovereign identity. |

---

## Daemons

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/daemons` | Bearer | List daemon status (proxy to backbone). |

---

## Agents, Skills & Rules

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/agents/save` | Bearer | Save an agent definition. |
| `GET` | `/agents/list` | Bearer | List saved agents. |
| `POST` | `/skills/save` | Bearer | Save a skill `.ori` file. |
| `POST` | `/rules/save` | Bearer | Save a rule `.ori` file. |

---

## Logging & Traces

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/logs/traces` | Bearer | Structured trace log. |
| `GET` | `/logs/raw` | Bearer | Raw log tail. |

---

## Admin

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/admin/waitlist` | Session | Waitlist admin UI page. |
| `POST` | `/admin/waitlist/auth` | None | Admin login (password-based). |
| `GET` | `/admin/waitlist/data` | Session | Get waitlist data as JSON. |
| `POST` | `/admin/waitlist/update` | Session | Update waitlist record. |
| `POST` | `/api/waitlist` | None | Public waitlist signup. |
| `POST` | `/api/v1/feedback` | None | Submit feedback. |
| `GET` | `/api/v1/shares` | Bearer | List shared items. |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAVAIA_API_BASE` | `http://localhost:8089` | Go backbone URL |
| `MAVAIA_API_KEY` | — | Bearer token for backbone auth |
| `MAVAIA_OLLAMA_BASE` | `http://localhost:11434` | Ollama base URL |
| `MAVAIA_UI_HOST` | `0.0.0.0` | Flask bind host |
| `MAVAIA_UI_PORT` | `5000` | Flask bind port (override to `5001` in practice) |
| `RESEND_API_KEY` | — | Resend API key (email sending) |
| `RESEND_WEBHOOK_SECRET` | — | Svix signing secret for inbound webhook |
| `EMAIL_FROM` | `ORI Studio <ori@thynaptic.com>` | From address for outbound email |
| `EMAIL_REPLY_TO` | `ori@inbound.thynaptic.com` | Reply-To for all outbound email |

---

## Data Files

All runtime state lives in `.oricli/` relative to `ui_app.py`:

| File | Contents |
|------|----------|
| `workflows.json` | Workflow definitions |
| `workflow_runs.json` | All run records |
| `email_clients.json` | Authorized inbound senders |
| `email_threads.json` | Sent message-ID → run mapping (for reply matching) |
| `notes.json` | Notebook entries |
| `subscriptions.json` | Active email subscriptions |
| `reminders.json` | REMIND command jobs |
| `board_items.json` | (legacy — Board now reads from runs directly) |
