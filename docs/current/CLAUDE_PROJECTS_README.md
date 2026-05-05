# ORI Platform — Claude Projects Context

## Who we are

**Mike** (also Cass) — solo founder/builder at **Thynaptic Research**. Full-stack across Go, TypeScript/Bun, React/Next.js, Expo. Ships fast. Works at the intersection of platform engineering and product.

**Collab style:** peer-to-peer, direct. No over-explaining basics. Technical shorthand is fine. Casual dev-slang is appropriate.

**Always use Bun** for JS/TS work — not Node. `Bun.serve` not Express, `bun:sqlite` not better-sqlite3, `bun test` not jest, `bunx` not npx.

---

## The Platform

**ORI** is a reasoning layer for applications: session-persistent memory, multi-turn context, agent profiles, dynamic routing, tool orchestration, and swarm coordination — exposed through a single OpenAI-compatible REST API.

- Live API: `https://glm.thynaptic.com/v1`
- Go module: `github.com/thynaptic/oricli-go`
- Monorepo: `/home/mike/Mavaia/`
- Production binary: `bin/oricli-go-v2` (single binary, two ports: 8088 internal / 8089 public)

All Thynaptic products (ORI Studio, ORI Home, ORI Web, ORI Code, Mise by ORI, etc.) call ORI's API — they are not part of the Mavaia repo.

---

## Current Architecture

```
Internet → Cloudflare → Caddy (glm.thynaptic.com)
  ├── /v1/mcp ──────► oricli-api.service     :8088
  └── everything ───► oricli-backbone.service :8089
```

### Oracle — the reasoning tier

`pkg/oracle/` — calls Anthropic API directly (HTTP/SSE, no SDK, no daemon).

| Route | Model | Thinking | Use |
|---|---|---|---|
| `light_chat` | Haiku 4.5 | off | conversational turns |
| `heavy_reasoning` | Sonnet 4.6 | 8K tokens | implementation, debugging |
| `research` | Sonnet 4.6 | 10K tokens | research, analysis |
| `image_reasoning` | Sonnet 4.6 | — | vision |

Prompt caching on system block (`cache_control: ephemeral`) on all routes. Extended thinking on heavy/research.

### Epistemics Engine — the new thing (2026-05-05)

`pkg/epistemics/` — closes Deutsch's gap between LLM mimicry and genuine knowledge creation.

Every query classified as explanatory (`why does`, `how does`, `what causes`, etc.) runs a dialectical 3-pass loop before responding:

```
Conjecture (Haiku) → Criticism (Haiku, adversarial) → Synthesis (Haiku or Sonnet)
```

- Criticism scores 0.0–1.0 severity. If severity ≥ 0.65 → escalates to Sonnet for synthesis.
- Early-exit if word overlap between conjecture and synthesis > 75% (converged).
- Fallback to normal oracle if epistemics errors.
- Cost: ~$0.014–$0.034/cycle. Daemon idle ~$6–17/month.

Test results showed the loop producing: novel falsifiable predictions, self-correcting causal mechanisms, and explanations that distinguished between narrow/repair/reject options rather than hedging.

### LLM Tier

`pkg/llm/` — lightweight Haiku wrapper, direct Anthropic API, prompt caching. Used by all cognition-tier background work (daemons, memory, safety, forge). Two exported functions: `Chat()` (Haiku, 512 tokens) and `ChatModel()` (configurable model + token limit).

### Autonomous Daemons

- **CuriosityDaemon** — background synthesis on accumulated observations
- **DreamDaemon** — idle state consolidation and creative synthesis  
- **ChronosDaemon** — temporal memory management
- All three use `llm.Chat()` (Haiku direct). Cost: ~$1–3/month idle.

### Memory

Two tiers:
- `pkg/memory/` — session memory (retrieval, topology, MAR policy)
- `pkg/enterprise/memory/` — multi-tenant enterprise memory with importance eval

### Safety

`pkg/safety/scai.go` — SCAI structural safety layer. Runs on all outputs. Uses `llm.Chat()`.

---

## Key Packages

| Package | What it does |
|---|---|
| `pkg/oracle/` | Anthropic API integration, routing, streaming, tools, skills |
| `pkg/epistemics/` | Conjecture-criticism-synthesis loop |
| `pkg/llm/` | Haiku/Sonnet direct call, prompt caching |
| `pkg/cognition/` | 269+ cognitive modules (sovereign, reasoning, style, supervision) |
| `pkg/api/server_v2.go` | Main Gin HTTP router, all endpoints |
| `pkg/swarm/` | Multi-agent swarm (Contract Net + blackboard) |
| `pkg/core/auth|config|model|store` | Live shared infrastructure |
| `pkg/memory/` | Session memory |
| `pkg/enterprise/memory/` | Multi-tenant memory |
| `pkg/safety/` | SCAI safety layer |
| `pkg/forge/` | Dynamic tool creation |
| `pkg/pad/` | Parallel Agent Dispatch |

---

## What Was Just Cleaned Up (2026-05-05)

- **20 dead `pkg/core/` packages deleted** — all orphaned (zero external callers). Kept: auth, config, model, store.
- **`TALOS_` → `ORI_` env var rename** — 426 occurrences across pkg/cognition/, pkg/memory/, pkg/enterprise/memory/.
- **RunPod/SLM/finetune/compute evicted** — all hardcoded llama/qwen/ministral/gemma/phi/deepseek model paths removed from active code. Everything inference → `llm.Chat()` or Oracle.
- **`vuln.ai/` archived** — moved to `~/vuln.ai-archived/`, out of repo.

---

## Env Vars That Matter

| Var | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required. Must be in systemd service env. |
| `ORICLI_SEED_API_KEY` | Owner Bearer token |
| `ORACLE_THINKING_HEAVY` | Token budget override (0 = disable) |
| `ORACLE_THINKING_RESEARCH` | Token budget override (0 = disable) |
| `ORI_EPISTEMICS_ENABLED` | true/false (default true) |
| `ORI_EPISTEMICS_MAX_ITER` | Default 2 |
| `ORI_EPISTEMICS_ESCALATE_THRESHOLD` | Default 0.65 |
| `ORI_EPISTEMICS_TRACE` | Include trace in logs (default false) |

---

## Deploy

```bash
cd /home/mike/Mavaia
go build -o /tmp/oricli-go-v2 ./cmd/oricli-engine/
sudo systemctl stop oricli-backbone oricli-api
cp /tmp/oricli-go-v2 bin/oricli-go-v2
sudo systemctl start oricli-backbone oricli-api
ss -tlnp | grep 808
```

Logs: `sudo journalctl -u oricli-backbone -n 50 --no-pager`

**Always build from `./cmd/oricli-engine/`** — not `./cmd/backbone/`.  
**Stop both services before replacing binary** — same file, both have it open.

---

## Products (not in this repo)

All at `/home/mike/thynaptic/`.

| Product | Stack | Domain |
|---|---|---|
| ORI Studio | React | oristudio.thynaptic.com |
| ORI Home | Electron + Vite + TS | desktop |
| ORI Web | Next.js + Clerk | — |
| ORI Code | TS + Ink + Bun | CLI |
| Mise by ORI | Next.js + Clerk + Stripe | misebyori.com |

Current focus: **ORI Studio → SMB `Jobs` surface.** Feel: "ORI knows my business and handles it for me."

---

## Gotchas

- `oracle.Init()` must run in a goroutine in main.go — blocks HTTP bind otherwise.
- Session ID is a **header** (`X-Session-ID`), not body. Missing = stateless.
- MCP only on heavy/research routes — light route causes OAuth hang.
- Both services must stop before replacing binary.
- Mise API key in `thynaptic/mise/.env.local` as `ORI_API_KEY`.
- Extended thinking is incompatible with tool use — `ChatWithTools()` doesn't enable thinking.
