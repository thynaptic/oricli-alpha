# Mavaia / ORI — Claude Code Context

## What this repo is

This is **Mavaia** — the monorepo for the ORI platform, built and maintained by Mike (Thynaptic).

ORI is a reasoning layer for applications: session-persistent memory, multi-turn context, agent profiles, dynamic routing, tool orchestration, and swarm coordination — exposed through a single OpenAI-compatible REST API at `https://glm.thynaptic.com/v1`.

Go module: `github.com/thynaptic/oricli-go`

---

## Repository layout

```
cmd/
  oricli-engine/     — primary production binary (headless API server, no PB dependency)
  backbone/          — full backbone with Studio UI proxy, VDI, DreamDaemon, etc.
  oricli-cli/        — TUI/CLI client
pkg/
  api/               — Gin HTTP server (server_v2.go is the main router)
  oracle/            — Anthropic API direct integration, routing, tools, batch, skills
  service/           — generation pipeline (generation.go)
  cognition/         — 269+ cognitive modules
  sovereign/         — Sovereign Engine (identity, resonance, ARTE, flow)
  swarm/             — multi-agent swarm with Contract Net + blackboard
  engine/            — core engine bootstrap
  auth/              — tenant auth, API key validation
  pad/               — Parallel Agent Dispatch
  goal/              — Goals and Sovereign Goals
  safety/            — disclosure / safety layer
  rag/               — retrieval-augmented generation
  memory/            — memory store
  scl/               — Sovereign Cognitive Log
  tcd/               — Temporal Cognitive Drift tracker
  forge/             — tool forge (dynamic tool creation)
  ...
oricli_core/
  skills/            — .ori skill files (builtin skill library)
.github/
  agents/            — .agent.md persona files (system prompts for Anthropic API calls)
dev-portal/          — machine-readable agent manifests (llms.txt, agent.json, openapi.json, etc.)
docs/                — human-facing documentation
bin/                 — compiled binaries (oricli-go-v2 is the live production binary)
```

---

## The running stack (production VPS)

| Service | Binary / Process | Port | Notes |
|---|---|---|---|
| ORI Engine (primary) | `bin/oricli-go-v2` | 8089 | Public API gateway, auth enforced |
| ORI Backbone (internal) | `bin/oricli-go-v2` | 8088 | Internal cognitive backbone |
| oricli-teams | systemd: `oricli-teams.service` | 3979 | Teams bot, now at `thynaptic/integrations/oricli-teams/` |

Live API: `https://glm.thynaptic.com/v1`
Dev portal (human docs): `https://docs.thynaptic.com`
Agent/machine portal: `https://dev.thynaptic.com`

To rebuild and restart:
```bash
go build -o bin/oricli-go-v2 ./cmd/oricli-engine
sudo systemctl restart oricli-engine  # or kill + relaunch manually
```

---

## Oracle — the reasoning tier

Oracle (`pkg/oracle/`) calls the Anthropic API directly via HTTP/SSE — no daemon, no SDK.

**Files:**
- `oracle.go` — session pool, `ChatStreamWithDecision`, streaming SSE parser, vision, agent loader
- `router.go` — `Decide()` function, route classification, `ThinkingBudget` per route
- `model_catalog.go` — model selection (env → defaults), `thinkingBudgetForRoute()`
- `tools.go` — `ChatWithTools()`, OpenAI↔Anthropic format conversion, `ToolDef/ToolCall/ToolResult`
- `batch.go` — `SubmitBatch()`, `GetBatch()`, `FetchResults()`, `PollUntilDone()`
- `skills.go` — `.ori` skill overlay loader, trigger-based system prompt injection

**Routes:**
- `RouteLightChat` → `claude-haiku-4-5-20251001` (no thinking)
- `RouteHeavyReasoning` → `claude-sonnet-4-6` + 8K thinking budget
- `RouteResearch` → `claude-sonnet-4-6` + 10K thinking budget
- `RouteImageReasoning` → vision via `AnalyzeImage()` → `claude-sonnet-4-6`

**Session pooling:** `sessionPool sync.Map` keyed by `tenantID:sessionID`. Tracks `lastUsed` for 30-min TTL reaping. Callers pass full message history — Anthropic API receives it natively, no injection hack needed.

**Stateless sessions:** Empty `sessionID` = one-shot, never pooled. Used by Mise and similar surfaces.

**Prompt caching:** System prompt sent as a cached content block (`cache_control: ephemeral`). Saves ~10x on repeated turns in the same session.

**Extended thinking:** Enabled automatically on heavy/research routes. Thinking blocks consumed silently — only text reaches the caller. Disable with `ORACLE_THINKING_HEAVY=0` / `ORACLE_THINKING_RESEARCH=0`.

**Tool use:** `ChatWithTools()` handles one non-streaming round — returns text OR `[]ToolCall`. Server_v2 returns OpenAI-format `tool_calls`; callers execute and send `role:"tool"` results back. `reqMsgsToOracle()` preserves `tool_call_id` through the conversion.

**Env overrides:**
- `ANTHROPIC_API_KEY` — required, must be in systemd service env
- `ORACLE_COPILOT_MODEL_LIGHT/HEAVY/RESEARCH` — model overrides (names kept for compat)
- `ORACLE_COPILOT_MODEL` — global fallback
- `ORACLE_THINKING_HEAVY/RESEARCH` — thinking budget override (tokens, 0 = disable)
- `ORACLE_VISION_MODEL` — vision model override (default: `claude-sonnet-4-6`)

**Init:** `go oracle.Init(0)` in main.go — warms catalog + starts reaper. `Available()` checks `ANTHROPIC_API_KEY` at request time; falls back to Ollama if unset.

---

## API server

Entry point: `pkg/api/server_v2.go`

Key route groups:
- Public (no auth): `/v1/health`, `/v1/ws`, `/v1/metrics`, `/v1/eri`, `/v1/aeci`, `/v1/flow/*`, `/v1/waitlist`, `/v1/modules`
- Protected (`runtime:chat`): `/v1/chat/completions`, `/v1/goals`, `/v1/memories`, `/v1/workspaces/run`, `/v1/documents`, `/v1/ingest`, `/v1/spaces`, `/v1/pad/*`, `/v1/sovereign/*`, `/v1/mcp`, `/v1/browser/*`, `/v1/tools`, `/v1/enterprise/*`, `/v1/agents/vibe`, `/v1/vision/analyze`, `/v1/images/generations`, `/v1/swarm/run`
- Admin (internal): `/v1/admin/tenants`, `/v1/swarm/admin/*`, `/v1/scl/*`, `/v1/tcd/*`

Session ID comes from the **`X-Session-ID` HTTP header** — not the request body. If omitted, the request is stateless (no history written).

Spaces handler: `pkg/api/spaces.go`
MCP handler: `pkg/api/mcp_runtime.go` — JSON-RPC 2.0, methods: `tools/list`, `tools/call`

---

## Agent profiles

Agents are defined as `.agent.md` files in `.github/agents/`. Loaded and cached (5 min TTL) via `cachedLoadCustomAgents()` — injected as system prompts on Anthropic API calls.

Active agents:
- `ori-chat-fast` — light conversational turns
- `ori-reasoner` — heavy reasoning and code
- `ori-research` — research and analysis

Skills (`.ori` files) live in `oricli_core/skills/` and `.github/skills/`. Both directories are registered in every session config via `SkillDirectories`.

---

## Product ecosystem

All Thynaptic product surfaces live at `/home/mike/thynaptic/`. They call ORI's API — they are not part of this repo.

```
/home/mike/thynaptic/
  ori-home/          Electron desktop companion (Vite + TypeScript)
  ori-web/           Browser chat UI (Next.js + Clerk)
  ori-sous/          Mobile SaaS cooking platform (Expo + NestJS + Clerk)
  mise/              Web URL→recipe parser (Next.js + Stripe) — service: mise-ui.service
  ori-stone/         Hearthstone analyst (Power.log reader)
  ori-code/          Terminal coding agent (TypeScript + Ink + Bun)
  vuln-ai/           Security surface / red team (Next.js)
  g-lm/              Enterprise LLM gateway (Go, port 8081)
  web/               Thynaptic marketing site
  cms/               Thynaptic CMS (Next.js)
  ori-owui/          Open WebUI theme (parked, CSS + brand tokens — revisit)
  branding/          Brand assets and logos
  integrations/
    oricli-teams/    Teams bot — service: oricli-teams.service (port 3979)
    oricli-slack/    Slack bot
  registry.yaml      Canonical product catalog (name, path, service, port, agent profile)
```

---

## Key env vars (`.env` in repo root)

| Var | Purpose |
|---|---|
| `ORICLI_SEED_API_KEY` | Owner Bearer token for the API |
| `GITHUB_MODELS_TOKEN` | PAT for Oracle model catalog auto-selection |
| `PB_BASE_URL` / `PB_ADMIN_EMAIL` / `PB_ADMIN_PASSWORD` | PocketBase at `pocketbase.thynaptic.com` |
| `RESEND_API_KEY` / `EMAIL_FROM` | Transactional email via Resend |
| `SLACK_APP_TOKEN` / `SLACK_BOT_TOKEN` | Slack integration |
| `TEAMS_APP_ID` / `TEAMS_APP_PASSWORD` | Microsoft Teams bot |
| `SOVEREIGN_ADMIN_KEY` / `SOVEREIGN_EXEC_KEY` | Admin/exec scopes for internal services |
| `MAVAIA_API_KEY` | Internal service-to-service auth |
| `ORICLI_PAD_ENABLED` / `ORICLI_GOALS_ENABLED` / `ORICLI_FORGE_ENABLED` | Feature flags |
| `RUNPOD_ENABLED` | GPU burst via RunPod (currently disabled) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth |

---

## Dev portal

`dev-portal/` — machine-readable manifests for agents integrating ORI. Deployed at `https://dev.thynaptic.com` (agents/machines only). Human-facing docs are at `https://docs.thynaptic.com`.

- `llms.txt` — canonical agent integration guide (keep in sync with server_v2.go routes)
- `agent.json` — product manifest and surface map
- `openapi.json` — REST contract (may lag; runtime behavior wins)
- `tools.json` / `requests.json` — tool schemas and example requests

When adding or removing API routes, update `dev-portal/llms.txt` to match.

---

## Known gotchas

- **`oracle.Init()` must run in a goroutine** in main.go or it blocks the HTTP server from binding.
- **`ANTHROPIC_API_KEY` must be in the systemd service env** — add to `/etc/systemd/system/oricli-backbone.service` and `oricli-api.service`, then `daemon-reload` + restart. Without it, `Available()` returns false and all requests fall through to Ollama.
- **`tool_call_id` must be preserved** — tool result messages from ORI Code go through `reqMsgsToOracle()` in server_v2.go, not the standard `ConvertMsgs()`. That path preserves `ToolCallID` for Anthropic's `tool_result` content blocks.
- **Extended thinking is incompatible with tool use** — `ChatWithTools()` does not enable thinking. Only `ChatStreamWithDecision` routes (heavy/research) get thinking.
- **MCP only on heavy/research routes** — injecting it on light routes causes long OAuth discovery hangs.
- **Session ID is a header** (`X-Session-ID`), not a body field. Missing it = stateless request, no history.
- **Session pool key is `tenantID:sessionID`** — tenant prefix added in `server_v2.go` before oracle calls. Never pass raw `sessionID` to oracle.
- **Port 8088 is backbone-only** — keep it localhost-only behind the reverse proxy. Public gateway is 8089.
- **`bin/oricli-go-v2` is the live binary** — `oricli-go`, `oricli-go-pure`, etc. are older builds.
- **Both services must stop before replacing binary** — same file held open by both processes.
- **Mise API key** — stored in `/home/mike/thynaptic/mise/.env.local` as `ORI_API_KEY`. If ORI is restarted and key is rejected (401), issue a new one: `curl -X POST http://localhost:8089/v1/admin/tenants/mise/keys -H "Authorization: Bearer <ORICLI_SEED_API_KEY>" -d '{"scopes":["runtime:chat"]}'`
- **ORI Code key** — service uses `glm.Qbtofkny.*` seed key (in `/etc/systemd/system/oricli-backbone.service`), not the `.oricli/api_key` file key.
- The `ORI-Home` directory was removed from this repo and now lives at `/home/mike/thynaptic/ori-home/`.
