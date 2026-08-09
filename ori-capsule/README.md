# ori-capsule

Working name for the **dockerized, BYOK** ORI runtime — a slim secondary surface extracted from the Mavaia / `oricli-alpha` monorepo.

| | Monorepo (`oricli-engine`) | **ori-capsule** |
|---|---|---|
| Deploy | Isolated VPS + systemd daemons | Single Docker container |
| Inference | Ollama + process-env Oracle keys | **BYOK** — OpenAI, Anthropic, OpenCode-compatible |
| Scope | Full Sovereign stack | Chat API MVP; modules opt-in later |
| Daemons | Curiosity, Dream, WorldTraveler, Metacog, Swarm, VDI, … | **None** (not plausible in Docker) |

## Quick start

```bash
cd ori-capsule
cp .env.example .env
docker compose up --build
curl -s http://localhost:8089/v1/health
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

## What's in / out (v0)

**In:** `GET /v1/health`, `POST /v1/chat/completions` (stream + non-stream), `GET /v1/models`, BYOK providers, Docker image.

**Out (VPS-era — revisit module-by-module later):** CuriosityDaemon, DreamDaemon, WorldTraveler, MetacogDaemon, GhostCluster, VDI/Browserless, Swarm/SPP, RunPod, Neo4j, PocketBase cold memory, FineTune, Forge, PAD, TCD, SCL daemons, Studio UI proxy.

## Promote to its own GitHub repo

```bash
# from monorepo root, after this tree is stable:
git subtree split -P ori-capsule -b ori-capsule-split
# create github.com/thynaptic/ori-capsule, then:
git push git@github.com:thynaptic/ori-capsule.git ori-capsule-split:main
```
