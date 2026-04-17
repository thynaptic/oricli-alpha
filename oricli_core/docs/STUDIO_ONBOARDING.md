# ORI Studio — Developer Onboarding

> For engineers, agents, and collaborators dropping into `oricli_core/`.

---

## What Is This Directory?

`oricli_core/` is the **Flask UI layer and email system** for ORI Studio. It is *not* the Go backbone — that lives in `pkg/` and `cmd/`. This is:

- The UI proxy server (`ui_app.py`) that serves the React frontend and bridges to the Go backbone
- The complete email command system (two-way email interface for SMB clients)
- Runtime configuration: skills, rules, profiles, MCP servers

The React frontend (`ui_sovereignclaw/`) builds to `ui_static/` and is served statically by this Flask app.

---

## Directory Structure

```
oricli_core/
├── ui_app.py             # The entire Flask server (~7000 lines)
├── oricli_core/
│   └── profiles/         # Agent profile definitions
├── skills/               # Skill persona files (.ori)
├── rules/                # Routing and safety rules (.ori)
├── Branding/             # Brand assets
├── examples/             # Usage examples
├── mcp_config.json       # MCP server configurations
├── docs/                 # You are here
│   ├── API.md            # Full Flask route reference
│   ├── EMAIL.md          # Email command system reference
│   └── ONBOARDING.md     # This file
└── pb_ins.md             # PocketBase API notes
```

The Flask app also creates `.oricli/` at runtime for all persistent state:
```
.oricli/
├── workflows.json
├── workflow_runs.json
├── email_clients.json
├── email_threads.json
├── notes.json
├── subscriptions.json
└── reminders.json
```

---

## Prerequisites

| Tool | Version | Role |
|------|---------|------|
| Python | 3.11+ | Flask runtime |
| Node.js | 18+ | Frontend build |
| Go backbone | running on :8089 | API backend |
| Ollama | running on :11434 | Local LLM (summaries, titling, email Q&A) |
| Resend account | — | Email send/receive |

---

## Environment Setup

Copy or create `.env` in `/home/mike/Mavaia/`:

```bash
# Go backbone
MAVAIA_API_BASE=http://localhost:8089
MAVAIA_API_KEY=glm.8eHruhzb...   # from .oricli/api_key

# Flask server
MAVAIA_UI_PORT=5001
MAVAIA_UI_HOST=0.0.0.0

# Ollama
MAVAIA_OLLAMA_BASE=http://localhost:11434

# Email (Resend)
RESEND_API_KEY=re_...
EMAIL_FROM=ORI Studio <ori@thynaptic.com>
RESEND_WEBHOOK_SECRET=whsec_...
```

---

## Starting the Server

**Always use the startup script** — it sources `.env` before exec so Resend keys are available:

```bash
nohup /home/mike/Mavaia/scripts/start_ui.sh >> /tmp/oristudio_ui.log 2>&1 &
```

> ⚠️ Do NOT use `python3 ui_app.py` directly in a nohup chain — the grandchild process won't inherit env vars set with `export $(...)`.

**Verify it's running:**
```bash
pgrep -f "ui_app.py"
curl localhost:5001/health
```

**Check logs:**
```bash
tail -f /tmp/oristudio_ui.log
```

**Restart (kill old PID first):**
```bash
pgrep -f "ui_app.py" | xargs kill
sleep 2
nohup /home/mike/Mavaia/scripts/start_ui.sh >> /tmp/oristudio_ui.log 2>&1 &
```

---

## Building the Frontend

The React app lives at `/home/mike/Mavaia/ui_sovereignclaw/` and builds to `ui_static/`:

```bash
cd /home/mike/Mavaia/ui_sovereignclaw
npm run build
```

No Flask restart needed after a frontend build — static files are served directly.

**Development (hot reload):**
```bash
npm run dev   # Vite dev server on :5173
```

---

## Key Areas of `ui_app.py`

`ui_app.py` is large (~7000 lines). Here's a map of the important sections:

| Line range | What's there |
|------------|-------------|
| ~1–160 | Imports, env config, HTTP client setup |
| ~160–270 | `/health`, `/api/eri`, `/models`, `/modules` |
| ~270–1140 | Chat, embeddings, images, agents, skills, rules, search, research |
| ~1137–1250 | `/chat` proxy to Go backbone |
| ~1250–1345 | MCP server management routes |
| ~1345–1395 | Email thread store helpers |
| ~1395–1485 | `_ori_action_footer()`, `_body_to_html()`, `_send_email()` |
| ~1485–1600 | `/v1/email/send`, `/api/board` |
| ~1515–1520 | Notes + subscription store declarations |
| ~1520–1660 | Subscription store + helpers (`_schedule_subscription`, `_fire_subscription`, `_boot_subscriptions`) |
| ~1660–1715 | Notes API routes |
| ~1715–1855 | Email client management routes + `/v1/email/register` |
| ~1855–2010 | `/v1/email/inbound` — reply threading + command dispatch |
| ~2010–2450 | All email command handlers (RUN, LIST, STATUS, STOP, NOTE, ASK, BRIEF, REMIND, REPORT, HELP, SUBSCRIBE, UNSUBSCRIBE, SUBSCRIPTIONS) |
| ~2450–3625 | Tasks, connections, integrations, Notion, RAG, OAuth |
| ~3625–3840 | Workflow scheduler helpers + `_load_workflows`, `_load_runs` |
| ~3840–4400 | `_run_workflow_job()` — the workflow execution engine |
| ~4400–7200 | Workflow CRUD, pipelines, projects, ORI DSL, memory, goals, documents, admin |

---

## Email System — Quick Reference

Full docs: [`EMAIL.md`](EMAIL.md)

**Add an authorized sender:**
```bash
curl -X POST localhost:5001/v1/email/clients \
  -H "Authorization: Bearer $MAVAIA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","name":"Mike"}'
```

**Trigger a briefing:**
```bash
curl -X POST localhost:5001/v1/email/briefing/user@example.com \
  -H "Authorization: Bearer $MAVAIA_API_KEY"
```

**Send a test email:**
```bash
curl -X POST localhost:5001/v1/email/send \
  -H "Authorization: Bearer $MAVAIA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"to":"you@example.com","subject":"Test","body":"Hello from ORI"}'
```

---

## Skills & Rules

Skills and rules are `.ori` files that define ORI's behavior per-context.

**Skills** (`skills/`) — persona and capability overlays:
```
api_designer.ori, go_engineer.ori, senior_python_dev.ori, ui_designer.ori, ...
```

**Rules** (`rules/`) — routing, safety, and response format:
```
global_routing.ori, global_safety.ori, response_format.ori, sanctuary_protocols.ori, ...
```

Save a skill via API:
```bash
curl -X POST localhost:5001/skills/save \
  -H "Authorization: Bearer $MAVAIA_API_KEY" \
  -d '{"name":"my_skill","content":"..."}'
```

---

## MCP Servers

MCP config is loaded from `mcp_config.json` and managed via `/mcp/servers` routes.

```bash
# List configured servers
curl localhost:5001/mcp/servers -H "Authorization: Bearer $MAVAIA_API_KEY"

# Reload after manual edits
curl -X POST localhost:5001/mcp/reload -H "Authorization: Bearer $MAVAIA_API_KEY"
```

---

## Workflows — Concepts

Workflows are JSON objects with a `steps` array. Each step has a `type`:

| Step type | Description |
|-----------|-------------|
| `fetch` | HTTP GET a URL and capture the response |
| `prompt` | Send output to Ollama/backbone for LLM processing |
| `code` | Run sandboxed Python |
| `notify` | Send email/Slack/Telegram notification |
| `condition` | Branch on a condition |
| `loop` | Iterate over items |

Variables use `{{double_braces}}` and are filled from `user_vars` at run time.

**Trigger a run:**
```bash
curl -X POST localhost:5001/workflows/<wf_id>/run \
  -H "Authorization: Bearer $MAVAIA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_vars":{"client":"Acme"}}'
```

---

## Common Gotchas

| Problem | Fix |
|---------|-----|
| Flask starts but RESEND not working | Use `start_ui.sh`, not `python3 ui_app.py` — env vars need sourcing |
| Port 5001 already in use | `pgrep -f ui_app.py` then kill the PID explicitly |
| Board shows "Workflow" for all titles | Old runs pre-date `wf_name` field. New runs store it at creation. |
| Reply emails not matching thread | Completion `_send_email()` must receive `wf_id=` and `run_id=` params |
| Ollama timeout on summaries | Default 30–45s. Falls back gracefully. Check `ollama ps`. |
| Subscriptions lost after restart | They're re-registered by `_boot_subscriptions()` at boot — check `.oricli/subscriptions.json` |
