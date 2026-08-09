# Module cut — monorepo → ori-capsule

Decision log for what moves from `oricli-alpha` into the dockerized capsule.
**Rule:** VPS-era daemons stay out. BYOK chat is the MVP. Everything else is module-by-module.

## Status legend

| Status | Meaning |
|---|---|
| **IN (v0)** | Shipped in ori-capsule now |
| **CANDIDATE** | Plausible in Docker — evaluate next |
| **VPS-ONLY** | Relied on long-lived host / sidecars — do not port |
| **DEFER** | Product value unclear for capsule; revisit later |
| **SIDE** | Present as stub / optional — discuss before enabling |

## IN (v0)

| Capability | Notes |
|---|---|
| HTTP `/v1/health` | Capsule readiness |
| HTTP `/v1/chat/completions` | OpenAI-shaped; stream + non-stream |
| HTTP `/v1/models` | Stub list — real models come from BYOK upstream |
| BYOK OpenAI | Bearer key → `api.openai.com/v1/chat/completions` |
| BYOK Anthropic | Bearer/`X-API-Key` → Messages API, response mapped to OpenAI shape |
| BYOK OpenCode-compatible | `X-Provider: opencode` + `X-Base-URL` (OpenAI chat completions dialect) |
| Docker image | Distroless static binary |
| **Safety stack** | `internal/safety` — full structural gates + SCAI contracts (see `SAFETY_SIDE.md`) |
| **Consumer memory** | `internal/memory` — bbolt warm bridge, session turns (`X-Session-ID`), belief, clock, chronos observe, in-mem working graph, L1 cache, spaces, tasks (see `MEMORY.md`) |
| **GOSH sandbox** | `internal/gosh` — docker-friendly mem/overlay shell; `GET /v1/gosh`, `POST /v1/gosh/run` (see `GOSH.md`) |
| **Local BM25 RAG** | `internal/rag` — sectioning, manifests, BM25 store; `GET/POST /v1/rag/*`; opt-in chat via `X-Ori-RAG: bm25` (see `RAG.md`) |

## VPS-ONLY (do not port)

| Module / daemon | Monorepo path | Why |
|---|---|---|
| CuriosityDaemon | `pkg/service/curiosity_daemon.go` | Long-lived forage + SearXNG |
| DreamDaemon | `pkg/service/daemon.go` | Nightly consolidation on host |
| MetacogDaemon | `pkg/metacog/`, `pkg/service/daemon.go` | Host WS anomaly loop |
| WorldTraveler | `pkg/service/world_traveler.go` | Periodic host forage |
| ReformDaemon | `pkg/service/reform_daemon.go` | Trace→constitution on host |
| TCD | `pkg/tcd/` | Temporal curriculum daemon |
| GhostCluster | (removed / backbone) | RunPod fleet |
| VDI / Browserless | `pkg/vdi/`, browser modules | Sidecar CDP on host network |
| Swarm / SPP | `pkg/swarm/` | Multi-node peer protocol |
| Swarm Jury / TG webhooks / LLM Critique | former `pkg/safety` extras | Dropped — see `SAFETY_SIDE.md` |
| MemoryBank / PB sync RAG (≤8s chat path) | monorepo retrieval | Stays on VPS — capsule uses BM25 only |
| Spaces chromem + Ollama query embeds | monorepo spaces knowledge | Sync embed lag — not for capsule chat |
| RunPod escalation | generation remnants | Burst GPU VPS path |
| Backbone Studio proxy | `cmd/backbone/` | Full host stack |
| systemd units | `*.service` | Not applicable in container |

## CANDIDATE (evaluate next)

| Module | Monorepo path | Docker fit |
|---|---|---|
| Auth / tenant API keys | `pkg/core/auth` | Optional capsule gateway key already exists; multi-tenant later |
| Skills / `.ori` overlays | `pkg/oracle/skills.go`, `oricli_core/skills` | Bake or mount read-only |
| Agent profiles | `.github/agents` | Mount as config |
| Epistemics loop | `pkg/epistemics` | Pure compute if BYOK-backed |
| Lightweight cognition | selected `pkg/cognition/*` | Per-module review — no daemon loops |
| Tools (allowlisted) | `pkg/tools`, forge subset | No free-form host shell |

## DEFER

| Module | Notes |
|---|---|
| PocketBase cold memory | External SaaS; capsule stays local-first |
| Neo4j graph | Heavy sidecar; optional compose profile later |
| PAD / Goals | Operator surfaces — out of consumer capsule |
| chromem / embed RAG | Sync Ollama embeds add reply lag — revisit with budgeted BYOK embed (BM25 is IN) |
| Enterprise RAG / twins | Consumer capsule — not in scope |
| Therapy / clinical modules | Product-specific |
| ORI Studio UI | Separate frontend image later |

## BYOK contract (stable)

| Header | Role |
|---|---|
| `Authorization: Bearer …` | Capsule key **or** provider key (see `ORI_CAPSULE_KEY`) |
| `X-API-Key` | Provider key when capsule gateway lock is on |
| `X-Provider` | `openai` \| `anthropic` \| `opencode` |
| `X-Base-URL` | Override upstream base (required-ish for opencode) |
| `X-Session-ID` | Session turn memory + belief/clock/graph scope |
| `X-Ori-RAG` | Set to `bm25` to inject local BM25 context into chat (default: off) |

Not an OpenAI-forwarding-only gateway: Anthropic is first-class; OpenCode is any OpenAI-compatible endpoint.
