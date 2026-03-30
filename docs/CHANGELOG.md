# Changelog

All notable changes to **ORI Studio / ORI Studio** are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versions track `VERSION` file. Commits listed for traceability.

---

## [Unreleased]

---

## [3.0.0] — 2026-03-30

### Added

#### Phase 3.5 — Governance Depth (`9a61c28`, `dbb51df`, `7173282`, `a5a033d`)

- **OpenAI bridge** — Drop-in compatible `/v1/chat/completions` endpoint. Any external OpenAI SDK client (Python, Node, curl) can route through Oricli's sovereign pipeline without modification. (`9a61c28`)
- **Governor v2** — Daily GPU budget gating (`$2/day` default cap). Every RunPod compute call is blocked when the daily budget is exhausted. SCAI reflection log persists constitutional compliance records for audit. (`dbb51df`)
- **Multi-tenant auth** — `TenantEnricher` middleware attaches tenant context to every request. `AdminOnly` guard restricts management endpoints. Full tenant CRUD API (create, read, update, delete tenant records in PocketBase). Sovereign contexts cannot bleed across tenants. (`7173282`)
- **Headless engine** — `cmd/oricli-engine` standalone binary decouples the cognitive engine from the UI process. `RemoteConfigSync` enables live config updates without engine restart, supporting deployments where UI and engine run on separate hosts. (`a5a033d`)

#### Phase 4 (internal) — Sovereign Peer Protocol (`a5a033d`, `2ce7b87`)

- **P2P node federation** — Two Oricli nodes can connect, complete an authenticated handshake, and exchange cognitive state (verified fact chains, SCL entries, goal state) over the Sovereign Peer Protocol. (`2ce7b87`)
- **Sovereign node identity** — Each node holds a sovereign identity used for peer authentication. Peer discovery and trust establishment are handled by the SPP handshake protocol without a central coordinator.

#### Phase 5 (internal) — Hive Mind Consensus (`2e8f542`)

- **Jury system** — N module "jurors" evaluate a query independently; majority consensus is required before an answer is committed. Disagreement surfaces as a first-class signal, not a silent average. (`2e8f542`)
- **Universal Truth layer** — Contested facts (high juror disagreement) are held provisional and re-evaluated on new evidence before being written to memory. Prevents confident misinformation from compounding in the knowledge graph.
- **Epistemic Sovereignty Index (ESI)** — Every committed claim carries a per-claim confidence score and a source diversity score. Low-ESI claims are surfaced in Critic review passes and flagged for re-evaluation. (`2e8f542`)

#### Phase 6 (internal) — Sovereign Cognitive Ledger (`2e8f542`, `6c8458d`)

- **Skill registry** — Every capability Oricli demonstrates is logged as a `Skill` struct: task type, outcome, latency, caller context. (`6c8458d`)
- **Reputation scoring** — Skills accrue confidence scores from outcome feedback over successive invocations. The ledger is the mechanism by which accumulated experience translates into measurable routing efficiency.
- **Skill-aware PAD routing** — Before assigning a task, PAD dispatcher queries the SCL to identify the highest-reputation agent for that task type. (`6c8458d`)

#### Phase 7 (internal) — Temporal Curriculum Daemon (`c4e74a0`, `e24d8ef`)

- **TCDManifest** — Tracks what Oricli has studied and when, with recency decay weights applied per topic. (`c4e74a0`)
- **TCDGapDetector** — Compares the current knowledge graph state against BenchmarkGapDetector failure patterns to identify absent or stale knowledge domains. (`c4e74a0`)
- **Adaptive curriculum scheduling** — Time-weighted, recency-decayed, priority-ranked study schedule generated from gap analysis. (`c4e74a0`)
- **API wiring** — `TCDManifest` and `TCDGapDetector` wired to the API server — the current study plan is observable and owner-triggerable. (`e24d8ef`)

#### Phase 8 (internal) — JIT Tool Forge (`16a3c31`)

- **Autonomous tool creation** — When Oricli encounters a task with no matching registered tool, the Forge writes one at runtime. Capability expansion is a runtime event, not a deployment event. (`16a3c31`)
- **PocketBase tool library** — Tools persist with versioning and are reusable across sessions and agent contexts.
- **Forge API** — 5 endpoints: `GET /tools`, `DELETE /tools/:id`, `GET /tools/:id/source`, `POST /tools/:id/invoke`, `GET /forge/stats`. (`16a3c31`)
- **`ORICLI_FORGE_ENABLED` env gate** — Feature gating for the Forge subsystem.

#### Phase 9 (internal) — Parallel Agent Dispatch (`757a7d7`)

- **N-agent parallel cognitive workforce** — PAD dispatches N specialized sub-agents simultaneously, each with a scoped context slice and a specialized system prompt. (`757a7d7`)
- **SCL reputation-weighted synthesis** — PAD result synthesis weights each agent's contribution by its current SCL reputation score, not by position or recency.
- **PAD observability** — Dispatch count, average latency, and synthesis quality tracked and exposed via stats endpoint.

#### Phase 10 (internal) — Sovereign Goal Engine (`a58e402`)

- **GoalDAG** — Full directed acyclic graph: SubGoal nodes, dependency edges, six-state status machine (pending → ready → dispatched → done/failed/blocked). (`a58e402`)
- **GoalPlanner** — LLM-driven structured DAG generation from a natural-language objective (max 10 nodes, 3 dep levels).
- **GoalStore** — PocketBase persistence for all DAG state (`sovereign_goals` + `goal_nodes` collections). Goal progress survives crashes and restarts.
- **GoalExecutor** — One tick: identifies ready nodes, dispatches via PAD, stores results.
- **GoalAcceptor** — Final LLM evaluation pass to determine if the original objective is fully satisfied.
- **GoalDaemon** — Background ticker with a `ManualTick` channel for owner-triggered execution. Multi-session goal survival guaranteed.
- **Goal REST API** — `POST /create`, `POST /tick`, `GET /list`, `GET /status/:id`, `DELETE /:id`. (`a58e402`)

#### Phase 11 (internal) — Self-Evaluation Loop (`d27d903`)

- **Critic module** — Scores each PAD worker output independently on three dimensions: completeness, confidence, and consistency. Per-worker scoring, not just aggregate synthesis quality. (`d27d903`)
- **Surgical retry** — Only underperforming workers are re-dispatched (max 2 retry rounds). Workers that passed evaluation are not re-run.
- **`critique: true` flag** — PAD dispatch requests opt into the self-evaluation loop per-request.

#### Phase 12 — Structured Output LoRA Pipeline (`66e7e40`)

- **Axolotl config generation** — Automated generation of Axolotl YAML configs for instruction-following LoRA training from Oricli's own verified fact chain. (`66e7e40`)
- **Dataset construction** — Training dataset assembled from JIT Daemon verified output — Oricli's own knowledge becomes her training data.
- **RunPod SSH training management** — Job submission, status polling, and artifact retrieval via SSH exec to remote Axolotl training pods.

#### Phase 13 — FineTuneOrchestrator (`4c1de38`)

- **Full job lifecycle management** — State machine: queued → wait_pod_ready → training → done/failed. (`4c1de38`)
- **RunPod REST API integration** — Pod spin-up and tear-down via RunPod REST API, not just SSH. Full pod lifecycle owned by the orchestrator.
- **SSH exec for training commands** — Remote Axolotl training commands dispatched via SSH with live status polling.
- **Per-job cost tracking** — `CostPerHr float64` field on every job record. Total training cost observable per-run.
- **PocketBase job persistence** — All job state persisted to PocketBase. Orchestrator restarts without losing in-flight job state.
- **FineTune REST API** — `POST /finetune/run`, `GET /finetune/status/:job_id`, `GET /finetune/jobs`. (`4c1de38`)
- **`ORICLI_FINETUNE_ENABLED` env gate** — Feature gating for the FineTuneOrchestrator.

#### Branding — ORI Studio (`94c4467`, `010aed0`, `e8c3af0`, `2016a94`)

- **ORI Studio final rename** — All `SovereignClaw` runtime references purged from the codebase. (`010aed0`, `94c4467`)
- **Ouroboros mark** — Two-face brand system: ouroboros (infrastructure identity) + Ori character (personality layer). Integrated across ORI Studio UI. (`e8c3af0`)
- **Cinematic boot splash** — 6-phase animated boot sequence displayed on app load: RING-0 KERNEL MERGE OK → SOVEREIGNTY ENGAGED. App phase machine: `landing → booting → app`. (`2016a94`)

#### Product — Marketing, Pricing & Waitlist (`99f53e1`, `262a9ef`, `e4be259`, `841b910`)

- **Marketing landing page** — Hero section, stats strip, features grid, philosophy section, pricing section, footer. Deployed as the public face of ORI Studio. (`262a9ef`)
- **SMB API pricing tiers** — Starter $29/mo, Business $99/mo, Enterprise $299/mo displayed on the pricing section. (`99f53e1`)
- **Waitlist modal** — Pricing CTAs open a waitlist modal wired to `POST /v1/waitlist` Go endpoint. (`99f53e1`)
- **`POST /v1/waitlist` endpoint** — Go handler persists waitlist entries to PocketBase `waitlist` collection. PocketBase collection live and deployed. (`e4be259`)
- **Waitlist admin page** — `/admin/waitlist` provides submission stats, filter controls, inline status updates, and full PocketBase-backed entry management. (`841b910`)

### Changed

- **Enterprise Knowledge Layer** — P-LMv1 packages pulled into backbone; enterprise connector wiring + async learn + job polling operational. (`b27da93`, `06670f8`, `ae68a93`)
- **DreamDaemon** — Age decay sweep added to idle-cycle memory consolidation. (`98d93e6`)
- **ConfidenceDetector** — `ComputeDynamicCertainty` formula updated; `MemFrag` extensions added; Aletheia noise gate applied. (`f370216`)
- **Aurora pipeline** — Balanced prompting added (restricted to open reasoning modes only); compute scaling and cross-domain bridge wired. (`d0365d2`, `7a9ad01`)

---

## [2.1.0] — 2026-03-24

### Added
- **ORI Studio AI error-awareness** — Vibe Mode AI now recognizes compiler diagnostics (`E[xxx]`/`W[xxx]`). Auto-detects fix intent via regex; shows `⚡ Fix N errors/warnings` quick-action chip when diagnostics exist. All AI modes now receive diagnostics as context. (`f6da9cc`)
- **`GET /v1/modules` endpoint** — Go backbone now exposes live `AgentSkill` objects from `SkillManager`. Returns 18 real skills. Flask `/modules` proxies to this endpoint. (`ed62d22`)
- **Improved Ollama error reporting** — `generation.go` now reads and surfaces Ollama error body on 4xx instead of silently dropping it. (`e0c316b`)
- **ERI live UI theming** — ERI swarm resonance state dynamically adjusts UI shade/tone in real time. (`b45f727`)

### Fixed
- **Canvas 400 error** — `/models` endpoint now filters embedding-only models (`all-minilm`, `nomic-embed-text`, `mxbai-embed-large`, etc.) from the chat model list. Backbone default (`qwen3:1.7b` via `OLLAMA_MODEL`) is sorted first so the UI picks a valid chat model on load. (`e0c316b`)
- **Editor overlay vertical offset** — ORI Studio syntax-highlight `<pre>` overlay was rendering ~3 lines below cursor. Fixed by replacing `<pre>` with `<div>`, setting `overflow: scroll` with CSS-hidden scrollbar (`scrollbar-width: none` + `::-webkit-scrollbar { display: none }`). (`c65c1f3`)
- **`/modules` 502** — Previously proxied to dead Python API on `:8081`. Now proxies to Go backbone `/v1/modules`. (`ed62d22`, `ea5b9b1`)
- **WebSocket 502** — Caddy `/v1/ws` block was missing `flush_interval -1`, preventing WS upgrade handshake. (`ea5b9b1`)
- **Dead `PYTHON_API_BASE` removed** — `/models` and `/health` were still proxying to the dead Python service on `:8081`. Rewired: `/models` pulls from Ollama `/api/tags`; `/health` checks backbone + Ollama. (`c06469e`)

### Changed
- **`/models`** — Now returns only chat-capable models from Ollama (embedding models excluded). Pattern filter: `embed`, `minilm`, `nomic`, `mxbai`, `bge-`, `e5-`, `gte-`.
- **`/health`** — Now reports `{ backbone: bool, ollama: bool }` against real services.
- **AI system prompt** — Updated branding from "ORI Studio" → "ORI Studio".
- **Flask proxy** — `PYTHON_API_BASE` fully removed; replaced with `OLLAMA_BASE` (`localhost:11434`).

---

## [2.0.0] — 2026-03 (approx)

### Added
- **ORI Studio IDE** — Full in-browser DSL IDE with syntax highlighting, compiler-style error output, autocomplete dropdown, and AI Vibe Coding panel. (`0dc0463`, `ff23103`, `381cd6f`)
- **ORI syntax docs** — `docs/ORI_SYNTAX.md` covering full `.ori` DSL spec.
- **Workflow template variables** — Built-in and user-defined run-time params. (`6195770`)
- **Workflow project folders** — Folder grouping with chain graph + Run Project. (`3408458`)
- **Step presets** — 8 ready-made output templates. (`a21318d`)
- **Stop / pause / resume workflows** — State persists across refresh. (`27ef1e3`)
- **Workflow branching + canvas** — Visual connections, branching logic. (`030`)
- **RAG store + doc ingest** — Document ingestion pipeline. (`029`)
- **OAuth2** — Workflow chaining + auto-index scheduler. (`028`)
- **MCP connections** — Agent switcher, Tasks pane, MCP backend. (`004`)
- **Research page** — Canvas fixes. (`003`)

### Changed
- **Rebrand: ORI Studio → ORI Studio** — UI, docs, service names, system prompts. (`0db0469`, `07fd93c`)
- **ORI crimson color system** — New design language replacing electric sci-fi palette.

### Fixed
- **Workflow cancel/pause** no longer reverts to `'running'`. (`2ea8b5e`)
- **Todoist API** — Migrated from v2 (`/rest/v2/tasks` — 410 Gone) to v1. (`5aeaab3`, `2f6d1b8`)

---

## [1.x] — Pre-2026

Initial ORI Studio consumer UI, Canvas, Agent Creators, deployment on `sovereignclaw.thynaptic.com` → migrated to `oristudio.thynaptic.com`. See earlier session checkpoints for history.

---

*Maintained by the ORI Studio team. Update this file with every doc-touching commit.*
