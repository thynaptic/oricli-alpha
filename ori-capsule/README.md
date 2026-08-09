# ori-capsule

Working name for the **dockerized, BYOK** ORI runtime — a slim secondary surface extracted from the Mavaia / `oricli-alpha` monorepo.

| | Monorepo (`oricli-engine`) | **ori-capsule** |
|---|---|---|
| Deploy | Isolated VPS + systemd daemons | Single Docker container |
| Inference | Ollama + process-env Oracle keys | **BYOK** — OpenAI, Anthropic, OpenCode-compatible |
| Scope | Full Sovereign stack | Consumer ORI in one container |
| Daemons | Curiosity, Dream, WorldTraveler, Metacog, Swarm, VDI, … | **None** (not plausible in Docker) |

## Quick start

```bash
cd ori-capsule
cp .env.example .env
docker compose up --build
curl -s http://localhost:8089/v1/health
curl -s http://localhost:8089/v1/capabilities
curl -s http://localhost:8089/v1/ready
```

### BYOK chat (OpenAI-compatible)

```bash
curl -s http://localhost:8089/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "X-Provider: openai" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hello from ori-capsule"}]}'
```

### Anthropic

```bash
curl -s http://localhost:8089/v1/chat/completions \
  -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
  -H "X-Provider: anthropic" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-6","messages":[{"role":"user","content":"Hello"}]}'
```

### OpenCode / any OpenAI-compatible base URL

```bash
curl -s http://localhost:8089/v1/chat/completions \
  -H "Authorization: Bearer $OPENCODE_API_KEY" \
  -H "X-Provider: opencode" \
  -H "X-Base-URL: https://opencode.ai/zen/v1" \
  -H "Content-Type: application/json" \
  -d '{"model":"your-model","messages":[{"role":"user","content":"Hello"}]}'
```

Optional gateway lock: set `ORI_CAPSULE_KEY` so clients auth to the capsule with that Bearer, and pass the LLM key via `X-API-Key`.

Client disconnect cancels the upstream BYOK request (stream and non-stream).

## Persistence contract

| Kind | What | Where |
|---|---|---|
| **Durable** | Sessions, spaces, tasks DAG, BM25 RAG | `ORI_MEMORY_DIR` volume (`/data/memory` in compose) |
| **Mounted RO** | Skills (`.ori`), agents (`.agent.md`), GOSH workspace | Compose binds; override `ORI_*_HOST_PATH` |
| **Ephemeral** | Light JIT forge tools | Process memory + TTL (`ORI_FORGE_*`); lost on restart |

`GET /v1/ready` probes memory-dir writability and echoes this contract. `GET /v1/capabilities` lists flags, headers, and endpoints.

## Volumes (compose)

```
ori-capsule-memory  →  /data/memory          # durable
ORI_GOSH_HOST_PATH  →  /workspace (ro)       # GOSH overlay
ORI_SKILLS_HOST_PATH → /skills (ro)
ORI_AGENTS_HOST_PATH → /agents (ro)
```

Optional: `ORI_CORS_ORIGINS=*` or comma-separated origins for browser clients.

## What's in / out

**In:** health / ready / capabilities, BYOK chat + models passthrough, structural safety, consumer memory + tasks DAG, GOSH (+ forge static gate + ActionTracker lessons), BM25 RAG (JSON + multipart file ingest), reasoning pack, reform constitutions, skills + agent profiles, tools allowlist + BYOK `tool_calls`, light in-memory JIT forge.

Docs: `MEMORY.md`, `TASKS.md`, `GOSH.md`, `RAG.md`, `REASONING.md`, `REFORM.md`, `SKILLS.md`, `AGENT_PROFILES.md`, `TOOLS.md`, `FORGE.md`, `SAFETY_SIDE.md`, `MODULE_CUT.md`.

**Out (leave on VPS / other surfaces):** Curiosity/Dream/WorldTraveler/Metacog/Ghost/VDI/Swarm daemons, RunPod, Neo4j, PocketBase MemoryBank / chromem embeds, therapy/clinical kits, multi-tenant auth, connectors, MCP bridge, bias injectors, CoT/ToT/MCTS multi-gen on default chat, Studio UI proxy, enterprise RAG.

## Promote to its own GitHub repo

```bash
# from monorepo root, after this tree is stable:
git subtree split -P ori-capsule -b ori-capsule-split
# create github.com/thynaptic/ori-capsule, then:
git push git@github.com:thynaptic/ori-capsule.git ori-capsule-split:main
```
