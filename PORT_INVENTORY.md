# Port inventory — monorepo → ori-capsule

**Audience:** human decision list outside the capsule tree.  
**Target:** `ori-capsule/` — dockerized, BYOK, consumer runtime (`CGO_ENABLED=0`, distroless).  
**Rule:** VPS daemons, sync-embed chat lag, enterprise, and clinical product stay out. Everything else is module-by-module.

Companion cut-log (status of what’s already shipped): `ori-capsule/MODULE_CUT.md`.

---

## Legend

| Tag | Meaning |
|---|---|
| **IN** | Already shipped in `ori-capsule` |
| **CAN** | Portable as-is or with light reshape (no extra LLM on default chat) |
| **OPT** | Valuable if opt-in / adapted (header, offline API, mount) |
| **NO** | Do not port into the consumer capsule |

---

## Already IN (capsule)

| Capsule path | From (monorepo) | Notes |
|---|---|---|
| `internal/byok` | — (new) | OpenAI / Anthropic / OpenCode-compatible |
| `internal/api` | `pkg/api` subset | health, chat, models, spaces/tasks, gosh, rag, reasoning |
| `internal/safety` | `pkg/safety` | Structural gates + SCAI; no Jury / TG / LLM Critique |
| `internal/memory` | `pkg/memory` + bridge ideas | bbolt, sessions, belief, clock, chronos observe, L1, spaces, tasks |
| `internal/gosh` | `pkg/gosh` | Mem/overlay sandbox; no Dream/Metacog/Reform wiring |
| `internal/rag` | `pkg/rag` helpers + BM25 | Local BM25; opt-in chat `X-Ori-RAG: bm25` |
| `internal/reasoning` | `precompute`, `trapcheck`, `cogload`, dualprocess classify, planning/resources/filter, reframe injects | Zero-extra-LLM pack |
| `cmd/ori-capsule` + Dockerfile | — | Distroless static binary |

---

## CANNOT port (or should not)

### Daemons / long-lived host loops

| Path | What | Why |
|---|---|---|
| `pkg/service/curiosity_daemon.go` | Forage + SearXNG loop | Daemon |
| `pkg/service/daemon.go` | Dream / JIT / metacog host loops | Daemon |
| `pkg/service/world_traveler.go` | Periodic forage | Daemon |
| `pkg/service/reform_daemon.go` | Trace→constitution on host | Daemon |
| `pkg/service/goal_daemon.go` | GoalDAG scheduler | Daemon |
| `pkg/service/tcd_daemon.go` | TCD live runner | Daemon |
| `pkg/metacog/` | MetacogDaemon + WS alerts | Daemon |
| `pkg/tcd/` | Temporal Curriculum Daemon | Daemon |
| `pkg/science/` | ScienceDaemon / Active Science | Daemon |
| `pkg/curator/` | Ollama curator/benchmark loop | Daemon |
| `pkg/audit/daemon.go` | Self-audit → scan/PR | Daemon |
| `pkg/scl/` | Sovereign Cognitive Ledger / crystals | Daemon / host ledger |
| `*.service` | systemd units | Not a container |
| `cmd/backbone/` | Full backbone + Studio proxy + daemons | Host stack |

### Sidecars / fleet / host network

| Path | What | Why |
|---|---|---|
| `pkg/vdi/`, `browserd/`, `docker/browserless/` | Browser / CDP | Sidecar |
| `docker/searxng/`, `pkg/service/searxng_searcher.go` | Search | Sidecar |
| `docker/minio/`, `docker/observability/` | Object store / o11y | Sidecar |
| `pkg/voice/` | Piper TTS | Sidecar |
| `pkg/rpc/`, `protos/` | gRPC → Python brain sidecars | Sidecar |
| `pkg/swarm/`, `pkg/bus/`, `pkg/node/` | Multi-node SPP | Fleet |
| `pkg/kernel/`, `cmd/kernel*` | MicroKernel / GhostCluster research OS | Host |
| RunPod / GhostCluster scripts | Burst GPU | Fleet |
| `pkg/engine/` RemoteConfigSync | Pull from Thynaptic | Host network coupling |

### Clinical / therapy product

| Path | What | Why |
|---|---|---|
| `pkg/therapy/` | Therapeutic cognition core | Clinical |
| `pkg/mct/`, `pkg/mbt/`, `pkg/mbct/`, `pkg/schema/` | MCT / MBT / MBCT / Schema+TFP | Clinical |
| `pkg/logotherapy/`, `pkg/up/`, `pkg/cbasp/` | Frankl / Unified Protocol / CBASP | Clinical |
| `pkg/ilm/`, `pkg/ipsrt/`, `pkg/iut/` | Inhibitory learning / IPSRT / IU | Clinical |
| `pkg/phaseoriented/`, `pkg/polyvagal/` | ISSTD trauma / polyvagal | Clinical |
| `pkg/pseudoidentity/`, `pkg/thoughtreform/` | High-demand / Lifton | Clinical |
| `pkg/apathy/`, `pkg/dmn/`, `pkg/interoception/` | Apathy / DMN / somatic clinical | Clinical |
| `pkg/hopecircuit/`, `pkg/socialdefeat/` | Therapy-tied agency / defeat recovery | Clinical |
| Therapy docs under `docs/api/THERAPY_*`, `docs/theory/THERAPEUTIC_*` | Product docs | Clinical |

### Enterprise / operator-only

| Path | What | Why |
|---|---|---|
| `pkg/enterprise/` | Studio SMB knowledge / RAG twins | Enterprise |
| `pkg/auth/` (tenant CognitivePolicy / quota) | Tenant enrichment | Enterprise |
| `pkg/sovereign/` ADMIN/EXEC host exec | Owner host keys | Enterprise / host |
| `pkg/pad/`, `pkg/goal/` as product surfaces | Operator PAD / Goals | Out of consumer scope |

### Sync embeds / heavy memory infra (chat lag)

| Path | What | Why |
|---|---|---|
| `pkg/connectors/pocketbase/`, `pkg/core/store/pocketbase/` | PocketBase | External cold DB |
| `pkg/service/memory_bank.go` | Hot chromem / warm LMDB / cold PB | Sync RAG ≤8s |
| `pkg/service/graph.go`, Neo4j scripts | Graph DB | Sidecar |
| `pkg/cache/` L2 chromem | Semantic cache | Needs embeds |
| `pkg/service/embedder.go`, `embedding_engine.go`, `code_embeddings.go` | Sync embeds | Chat lag |
| `pkg/rag/hybrid.go`, `remote.go` | Embed/hybrid RAG | Chat lag |
| `pkg/training/`, `cmd/gen_dataset/`, trainer service | Fine-tune pipeline | Training infra |

### Multi-gen / multi-LLM on default chat

| Path | What | Why |
|---|---|---|
| `pkg/cognition` engines (`mcts*`, `tot`, `reasoning_engines`, `self_discover`, `deliberation`, `adaptive_engine`, …) | CoT/ToT/MCTS/ARE/Debate/ReAct | N× generation |
| `pkg/service/generation.go` retry paths | Metacog / therapy / dualprocess regenerate | 2×+ TTFT |
| `pkg/epistemics/` on default chat | Conjecture→criticism→synthesis | 3–6 LLM calls |
| `pkg/pad/` critic loops on chat | Parallel agents | Multi-LLM |
| Dualprocess **retry/RunPod escalate** | S2 mismatch → regen | Latency (classify-only is OK / IN) |
| LLM Critique/Revise (dropped from safety) | Extra BYOK round-trip | Latency |

### Other product surfaces (not this image)

| Path | What | Why |
|---|---|---|
| `ui_sovereignclaw/`, `ui_app.py`, `ui_static/`, `oricli_ui/` | Studio / Flutter / Flask shells | Separate frontends |
| `cmd/oricli-cli/`, `pkg/cli/` | TUI against backbone | Separate client (optional later) |
| `dev-portal/` | glm.thynaptic.com agent manifests | VPS API portal |
| External Thynaptic apps (ori-home, ori-web, mise, …) | Other repos | Out of tree |

### Binaries that stay VPS / demos

| Binary | Stay |
|---|---|
| `cmd/oricli-engine` | VPS production API |
| `cmd/backbone` | VPS full stack |
| `cmd/oricli-cli` | VPS client (reshape later → capsule) |
| `cmd/kernel*`, `cmd/gen_dataset`, `cmd/bench`, `cmd/*_demo` | VPS / research / demos |
| `ori-capsule/cmd/ori-capsule` | **Capsule** |

---

## CAN port (next / reshape)

### Pure Go / heuristic — good next slices

| Path | What | Notes |
|---|---|---|
| `pkg/envload/` | `.env` autoload | Utility |
| `pkg/searchintent/` | Search-intent classify | No SearXNG required |
| `pkg/state/` | Tool/action mismatch tracking | Pair with GOSH |
| `pkg/reform/` constitutions (not daemon) | Canvas/code constitutions | Inject on surface |
| `pkg/forge/` verifier / CodeConstitution | Static script rules | With GOSH only |
| `pkg/tasks/` | Task DAG | Deepen existing `/v1/tasks` |
| `pkg/cognition/home_logistics_intelligence.go` | Active Pin extraction | App-neutral API |
| `pkg/cognition/confidence.go` | Web-lookup need detector | Heuristic |
| `pkg/mindset/` | Growth-language reframe | Single inject pattern |
| `pkg/arousal/`, `pkg/coalition/`, `pkg/conformity/`, `pkg/statusbias/`, `pkg/ideocapture/`, `pkg/interference/` | Bias / load injectors | Optional single-line; watch tone/noise |
| `pkg/chronos` observe-only | Temporal snapshot | Observe already IN; no seeder |

### Opt-in reshape (adaptation required)

| Path | What | Rule |
|---|---|---|
| `pkg/core/auth` + memory store | API keys / tenants | Gateway key exists; multi-tenant later; no PB |
| `pkg/epistemics/` | Multi-pass explanation | **Opt-in only**; never default chat |
| `pkg/tools/` + MCP bridge subset | Tool registry | Allowlist + GOSH; no host admin plugins |
| `pkg/forge/` generator | Dynamic tools | Constitution → GOSH only |
| `pkg/connectors/*` except PocketBase | GitHub/Notion/Google/… fetch | Ingest → BM25; no sync embeds on chat |
| `pkg/llm/` | HTTP LLM helper | Prefer capsule BYOK; or thin wrapper |
| Oracle **patterns** (skills, tool format) — not wholesale `pkg/oracle` | Skill overlays / tool_calls | Reimplement on BYOK |
| `pkg/api` remaining handlers | documents, MCP, ingest, … | One endpoint at a time; strip PB/enterprise/swarm |
| `pkg/service` non-daemon helpers | ingest, classifier, budget, metrics | Extract pure helpers only |
| `pkg/goal/` / `pkg/pad/` libraries | Goal DAG / parallel workers | Opt-in batch APIs if ever; not default chat |
| `pkg/sentinel/` without daemon | Plan critique | Opt-in; costs an LLM call |
| Affect stack (`arte`, `aeci`, `drift`, `temporal`, `tonetrack`, `flow*`) | Ambient tone/climate | Pure Go possible; product fit unclear |

### Mount-only (config / prompts)

| Path | What |
|---|---|
| `oricli_core/skills/*.ori` | Skill library |
| `oricli_core/profiles/`, `rules/`, `examples/` | Profiles / rules |
| `.github/agents/*.agent.md` | Agent system prompts |
| `.github/skills/` | Extra overlays |
| `constitution.example.ori` | Sample constitution |

---

## Quick scoreboard

| Bucket | Count (approx) | Action |
|---|---|---|
| **IN** | Safety, memory, GOSH, BM25 RAG, reasoning pack, BYOK API | Maintain |
| **NO — daemons/sidecars/fleet** | Curiosity/Dream/Metacog/TCD/Science/Curator/SCL, VDI, swarm, RunPod, systemd | Leave on VPS |
| **NO — clinical** | Entire therapy modality set (~20 pkgs) | Leave on VPS |
| **NO — enterprise / Studio** | enterprise, sovereign exec, PAD/Goals product, Studio UI | Other surfaces |
| **NO — sync RAG / heavy DB** | PB, Neo4j, chromem, MemoryBank chat retrieve | BM25 only in capsule |
| **NO — multi-gen chat** | MCTS/ToT/ARE/Debate, GenService retries, default epistemics | Oracle/BYOK model choice instead |
| **CAN / OPT next** | skills mount, tools+GOSH, connectors→BM25, home logistics API, bias injectors, core/auth | Pick deliberately |

---

## Decision shortcuts

1. **Daemon or sidecar?** → NO  
2. **Clinical brand / diagnosis-adjacent?** → NO  
3. **Adds an LLM round-trip or full regen on default chat?** → NO (OPT only if header-gated)  
4. **Needs PB / Neo4j / chromem / Ollama embeds?** → NO for chat path  
5. **Enterprise / Studio / PAD / Goals?** → NO for consumer capsule  
6. **Pure heuristic or local store under `ORI_MEMORY_DIR`?** → CAN  
7. **Prompt/skill file only?** → mount  

When in doubt: keep it off the default chat path.
