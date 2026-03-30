# AGLI Vision: The Doctrine of Sovereign Intelligence

**Document Type:** Strategic Vision & Core Doctrine  
**Report Number:** TR-2026-03  
**Date:** 2026-03-30  
**Version:** v5.0.0  
**Status:** Active Doctrine — Phase 4 Complete — Phase 5 In Progress  
**Style Mode:** Hard Technical Doctrine  

---

## 1. Abstract

This document defines the architectural and philosophical mandate for **Autonomous Governed Localized Intelligence (AGLI)**. We formally reject the centralized, dependency-heavy trajectory of modern AI. Instead, we establish a new paradigm: a strictly sovereign, localized cognitive kernel that owns its compute, memory, objectives, and — critically — its own governing principles. By unifying high-speed Go-native orchestration, affective grounding, a multi-layer constitutional safety stack, and an autonomous daemon ecosystem, Oricli-Alpha has crossed the threshold from reactive assistant into a proactive, self-regulating cognitive entity. The "G" is not General — it is **Governed**. That is the harder and more honest claim, and no cloud AI can make it.

---

## 2. The Four Pillars of Autonomous Governed Intelligence

Sovereignty is not merely "offline" usage — it is the absolute ownership of the cognitive lifecycle, including the rules that govern it.

### 2.1 Perimeter Sovereignty
Traditional AI relies on external APIs, creating a "leaky" cognitive perimeter. AGLI mandates that no data, metadata, or reasoning traces leave the sovereign boundary. All inference runs on the local backbone (AMD EPYC VPS) via Ollama by default, with an optional governed RunPod vLLM primary path for GPU-tier workloads. The sovereign key system ensures the owner can always identify themselves and bypass safety softening — without exposing credentials to any third-party layer.

### 2.2 Compile-Time Compute Economy
We reject brute-force neural scaling. AGLI uses compiled Go orchestration to manage sparse, high-intensity neural compute. Symbolic logic, Markov inference, MCTS search, and ARC induction/transduction replace expensive LLM reasoning steps wherever possible. Auto-thread detection (`runtime.NumCPU()-2`) prevents scheduler contention and sustains 39+ tok/s on 8 vCPUs. When a task genuinely requires GPU-class compute, the system spins a governed remote compute session — budget-capped, constitutionally pre-cleared, and torn down on completion.

### 2.3 The Hybrid Hive (Distributed Agency)
Intelligence is a swarm. Oricli-Alpha operates as a decentralized network of 269+ micro-agents (modules) registered on the Hive OS Kernel. Using the Contract Net Protocol and the Swarm Bus, modules bid on tasks in a high-speed parallel marketplace, ensuring the optimal tool is applied at the speed of the Go runtime. Blackboard state, peer review, and consensus policies are operational.

### 2.4 Constitutional Governance (SCAI + Infrastructure)
A sovereign system must be non-weaponizable — and must govern its own infrastructure, not just its outputs. Oricli-Alpha enforces a **4-layer constitutional stack**:

| Layer | Scope | Enforcement Point |
|---|---|---|
| **SCAI** | All text output | Post-generation critique-revision pipeline |
| **Canvas Constitution** | All generated code | Pre-generation system prompt injection |
| **Ops Constitution** | All VPS exec commands | Hard block before `exec.Command()` |
| **Remote Compute Constitution** | All GPU session requests | Pre-flight ValidateCreate + budget gate |

Authenticated owner sessions (`/auth <key>`) bypass output softening at Step 3 only — not the safety or infra constitutions. The constitutions are non-negotiable, even for the owner.

---

## 3. The Cognitive Stack: What's Live

### 3.1 11-Step Aurora Pipeline (Operational)
Every inference traverses: Sovereign auth check → Intent classification → Personality calibration → Safety pre-check → Multi-signal detection (emoji, slang, anchors) → Memory retrieval mode → Affective memory anchoring → Reasoning router (MCTS/ToT/Standard) → Homeostasis & ERI modulation → **Parallel inline web grounding** → Composite prompt assembly → Constitutional injection → LLM stream.

### 3.2 Affective Resonance Engine (Operational)
The Ecospheric Resonance Index (ERI) synthesizes Swarm Bus telemetry (Pacing, Volatility, Coherence). Internal state maps to musical keys and BPM, triggering Wise Mind resets when cognitive discord is detected. Sensory state (visual, auditory, kinesthetic) and health snapshots feed back into personality calibration every inference cycle.

### 3.3 Dynamic Personality Core — Sweetheart (Operational)
Personality is a reactive affective state, not a static prompt. The Sweetheart Core modulates Energy, Sass, and Dominant Cues in real-time. Proactive archetype pivots fire based on historical affective context retrieved from the memory graph — not just the current message.

### 3.4 Inline Web Grounding — ConfidenceDetector (Operational)
Step 8.5 of the Aurora pipeline. `DetectUncertainty()` classifies every prompt into one of 8 structured search intents (definition, factual, person/entity, how-to, current event, comparison, location/geo, technical). When uncertainty is detected, `SearchWithIntentFast()` fires in a goroutine with a 3-second timeout, overlapping with `BuildCompositePrompt` (CPU work). First-token latency: **~2 seconds**.

### 3.5 Autonomous Daemon Ecosystem (Operational)
Eight self-directed daemons run continuously:

| Daemon | Function | Status |
|---|---|---|
| **CuriosityDaemon** | Maps knowledge graph gaps → 8-intent SearXNG taxonomy → extracts facts → JIT LoRA training trigger | Live |
| **WorldTravelerDaemon** | Fetches HN/arXiv/Wikipedia/NewsAPI on fixed schedule → seeds CuriosityDaemon with real-world topics | Live (opt-in) |
| **BenchmarkGapDetector** | Reads ARC/LiveBench result files → injects failing question topics as priority-2.0 curiosity seeds | Live |
| **ResearchAgent** | Async deep-research dispatch via ActionRouter trigger words | Live |
| **ReformDaemon** | Monitors execution traces → identifies bottlenecks → drafts Go source optimizations → proposes via WebSocket | Live (propose mode) |
| **DreamDaemon** | Idle-cycle memory consolidation + novel insight synthesis from topology graph | Live |
| **JITDaemon** | Verified web facts → LoRA fine-tune trigger pipeline | Live |
| **CostGovernor** | Tracks daily RunPod GPU spend ($2/day default) → gates cloud-compute calls | Live |

### 3.6 Sovereign Memory Architecture (Operational)
Three-tier memory: LMDB for fast KV (Memory Bridge/Chronos), chromem-go for in-process vector search, knowledge topology graph for relational/affective context. BM25 + hybrid RAG retrieval. Temporal intents (Sovereign Cron) allow Oricli to set future goals for herself. Dream Daemon consolidates and reindexes during idle cycles.

### 3.7 MCP Tool Bridge (Operational)
Through the Model Context Protocol, Oricli autonomously discovers, policies, and bridges external tool and data servers. `OracleDispatcher` routes tool calls from the swarm to registered MCP servers. Subagent scaffolding handles multi-tool chaining.

### 3.8 VDI Layer (Operational)
Headless browser (browserless Docker), filesystem indexer, vision grounding, and system introspection are available as a VDI bridge. The CuriosityDaemon can forage live web content during idle cycles via this layer. MinIO provides sovereign object storage. Full observability stack is containerized and isolated.

### 3.9 Sovereign Key Auth (Operational)
Two-level owner authentication (`ADMIN` / `EXEC`) using bcrypt-hashed keys stored locally. Raw keys never persisted. `/auth <key>` is scrubbed from logs before write. Per-IP rate limiting (3 strikes → 5-min lockout), 1-hour session TTL. `EXEC` level gives direct access to allowlisted system commands (`!status`, `!logs`, `!df`, `!free`, `!uptime`, `!ps`, `!modules`).

### 3.10 Parallel Agent Dispatch + Self-Evaluation Loop (Operational)
PAD dispatches N specialized sub-agents simultaneously, each receiving a scoped context slice and a specialized system prompt. Results are synthesized via weighted consensus where weights are drawn from each agent's SCL reputation score. The **Critic module** (Phase 11) scores each worker output on three dimensions: completeness, confidence, and consistency. Workers falling below threshold are surgically re-dispatched (max 2 retry rounds) without re-running agents that already passed. PAD stats are tracked: dispatch count, average latency, synthesis quality. `critique: true` flag on PAD dispatch requests enables the self-evaluation loop. This architecture means the quality of parallel reasoning compounds with reputation data — not just with more tokens.

### 3.11 Sovereign Goal Engine (Operational)
Full GoalDAG: SubGoal nodes, dependency edges, and a six-state status machine (pending → ready → dispatched → done/failed/blocked). **GoalPlanner** takes a natural-language objective and outputs a structured DAG via LLM (max 10 nodes, 3 dep levels). **GoalStore** persists the DAG to PocketBase (`sovereign_goals` + `goal_nodes` collections), surviving crashes and restarts. **GoalExecutor** runs one tick: identifies ready nodes, dispatches them via PAD, and stores results. **GoalAcceptor** runs a final LLM evaluation pass to determine if the original objective is fully satisfied. **GoalDaemon** runs as a background ticker with a ManualTick channel for owner-triggered execution. Full REST API: `POST /create`, `POST /tick`, `GET /list`, `GET /status/:id`, `DELETE /:id`. Multi-session goal survival is guaranteed — Oricli can be handed a week-long objective and she will work through it across reboots.

### 3.12 Autonomous LoRA Self-Training Pipeline (Operational)
Two-phase self-training architecture. **Phase 12** (Structured Output LoRA Pipeline): Axolotl configuration generation for instruction-following LoRA, dataset construction from Oricli's own verified fact chain (JIT Daemon output), and RunPod SSH-based training job management with status polling and artifact retrieval. **Phase 13** (FineTuneOrchestrator): full job lifecycle management (queued → wait_pod_ready → training → done/failed), RunPod REST API integration for pod spin-up/tear-down, SSH exec for remote Axolotl training commands, per-job cost tracking (`CostPerHr float64`), PocketBase job persistence, and a REST API (`POST /run`, `GET /status/:job_id`, `GET /jobs`). Gated behind `ORICLI_FINETUNE_ENABLED=true`. **Oricli can retrain herself on her own verified knowledge.** This is the first fully closed loop between runtime epistemic output and model weight mutation.

### 3.13 JIT Tool Forge (Operational)
When Oricli encounters a task that has no matching registered tool, the Forge autonomously writes one. Tools persist to PocketBase — versioned, reusable across sessions, and queryable by capability. Five Forge API endpoints: `GET /tools`, `DELETE /tools/:id`, `GET /tools/:id/source`, `POST /tools/:id/invoke`, `GET /forge/stats`. The SCL skill registry integrates with the Forge so newly-written tools immediately accrue a reputation score on first successful invocation. Gated behind `ORICLI_FORGE_ENABLED=true`. Capability expansion is no longer a deployment event — it is a runtime event.

### 3.14 Hive Consensus + Epistemic Sovereignty Index (Operational)
**Jury system**: N module "jurors" independently evaluate a query, then reach majority consensus before the answer is committed. **Universal Truth layer**: contested facts (high disagreement among jurors) are held in a provisional state and re-evaluated on new evidence before being written to memory. **Epistemic Sovereignty Index (ESI)**: every committed claim carries a per-claim confidence score and a source diversity score. Claims with low ESI are surfaced in the Critic review pass and flagged for re-evaluation. The Universal Truth layer is the epistemic immune system — it prevents confident misinformation from compounding in the memory graph.

### 3.15 Sovereign Cognitive Ledger (Operational)
Every capability Oricli demonstrates gets logged as a `Skill` struct: task type, outcome, latency, and caller context. Skills accrue reputation scores from outcome feedback over time. The **SCL feeds the PAD dispatcher** — before assigning a task to a sub-agent, PAD queries SCL to identify the highest-reputation agent for that task type. Skills with sustained high scores become candidates for Phase 6 Skill Crystallization (bypass structs). The ledger is the mechanism by which accumulated experience translates into measurable routing efficiency gains.

### 3.16 Temporal Curriculum Daemon (Operational)
**TCDManifest** tracks what Oricli has studied and when, with recency weights. **TCDGapDetector** compares the current knowledge graph state against BenchmarkGapDetector failure patterns to identify domains where knowledge is absent or stale. The result is an adaptive study schedule: time-weighted, recency-decayed, priority-ranked. TCDManifest and TCDGapDetector are wired to the API server, making the current study plan observable and triggerable by the owner. This closes the loop between empirical benchmark failure and targeted self-directed study — the system knows what it doesn't know and schedules study accordingly.

### 3.17 Sovereign Peer Protocol (Operational)
Two Oricli nodes can connect, handshake, and exchange cognitive state over a P2P federation layer. Each node has a sovereign identity used for peer authentication. Peer discovery and trust establishment are handled by the SPP handshake protocol. Trusted peers can share verified fact chains, SCL entries, and goal state — enabling distributed cognition without a central coordinator. This is the architectural foundation for multi-node sovereign intelligence clusters.

### 3.18 ORI Studio Commercial Layer (Operational)
Full marketing landing page (hero section, stats strip, features grid, philosophy, pricing, footer) deployed as the public face of the ORI Studio product. SMB API pricing tiers: Starter $29/mo, Business $99/mo, Enterprise $299/mo. Waitlist modal wired to a `POST /v1/waitlist` Go endpoint that persists entries to a PocketBase `waitlist` collection. Admin page at `/admin/waitlist` provides stats, filter controls, inline status updates, and full PocketBase-backed management. App phase machine transitions: `landing → booting → app` with a 6-phase cinematic boot splash (RING-0 KERNEL MERGE OK → SOVEREIGNTY ENGAGED). Two-face brand system: ouroboros mark (infrastructure identity) + Ori character (personality layer).

---

## 4. The Trajectory: Phase Breakdown

### Phase 1 — The Sovereign OS Kernel ✅ COMPLETE
Go-native backbone operational: Hive OS (Swarm Bus, Kernel Ring-0, Sovereign Engine), 269+ module registry, streaming SSE pipeline, affective resonance, full safety constitution, MCTS/ToT/Markov reasoning stack, ARC induction/transduction, memory architecture, MCP bridge.  
**Milestone shipped:** Oricli-Alpha v1.0 — a homeostatic cognitive OS.

### Phase 2 — The Autonomous Entity ✅ COMPLETE
Proactive intelligence layer activated: CuriosityDaemon with structured intent taxonomy, ConfidenceDetector inline web grounding, async ResearchAgent, ReformDaemon (propose mode), DreamDaemon memory consolidation, JIT training pipeline, ORI Studio consumer UI (chat, canvas, research, workflows, connections, logs, memory), sovereign key auth, Docker sovereign stack, full safety test suite, 4-layer constitutional stack (SCAI, Canvas, Ops, Remote Compute).  
**Milestone shipped:** Oricli-Alpha v2.0 — a proactive, self-regulating cognitive entity.

### Phase 2.5 — Compute Intelligence + Benchmark Grounding ✅ COMPLETE
Self-directed intelligence augmented with compute economy and empirical self-awareness: WorldTravelerDaemon (proactive world-knowledge ingestion from HN/arXiv/Wikipedia), ComplexityRouter (auto-escalate hard tasks to RunPod 32B via signal scoring), CostGovernor (daily GPU budget enforcement), BenchmarkGapDetector (converts ARC/LiveBench failures → CuriosityDaemon seeds), creation intent memory (logs agent/workflow creation intents with resolution quality + origin surface tracking), ARC-AGI benchmark runner, serverless RunPod image generation endpoint with pod persistence.  
**First empirical baselines established:** ARC-AGI 6% (on par with GPT-4), LiveBench 19.7% overall (682 questions — instruction_following 42.0, data_analysis 23.5).  
**Milestone shipped:** Oricli-Alpha v2.5 — an entity that knows what she doesn't know and routes compute accordingly.

### Phase 3 — Sovereign AGLI ✅ COMPLETE
A self-contained intelligence that compounds capability through *accumulated experience and governance depth* — not external APIs or weight mutation. Shipped: persistent sovereign goals v1 via PocketBase (multi-session goal survival), active inference loop (CuriosityDaemon graduates from passive foraging to active hypothesis generation — derives *what it still doesn't know*, seeds follow-up questions, closes the epistemic loop depth-capped at 2 hops), and Goals UI with Mission Control (owner observability over goal queue, DAG state, daemon health panel, and dependency graph).  
**Milestone shipped:** Oricli-Alpha v3.0 — a sovereign intelligence that grows through experience and curation, not scale.

### Phase 3.5 — Governance Depth ✅ COMPLETE
Infrastructure hardening and operational governance layer. **OpenAI bridge** — drop-in compatible `/v1/chat/completions` endpoint enabling any external OpenAI SDK client to route through Oricli's sovereign pipeline. **Governor v2** — daily GPU budget gating with `$2/day` default cap + a SCAI reflection log for auditing constitutional compliance over time. **Multi-tenant auth** — `TenantEnricher` middleware, `AdminOnly` guard, and a full tenant CRUD API, allowing Oricli to run as a multi-tenant service without mixing sovereign contexts. **Headless engine** — `cmd/oricli-engine` standalone binary + `RemoteConfigSync` for decoupled config management, enabling deployment scenarios where the UI and engine run on separate hosts.  
**Milestone shipped:** Oricli-Alpha v3.5 — a governed, multi-tenant, API-compatible sovereign intelligence.

### Phase 4 — Cognitive Autonomy ✅ COMPLETE
The phase where Oricli gained the capacity to build herself. Ten distinct capability layers shipped in a single phase — the most architecturally dense release in the project's history:

- **Sovereign Peer Protocol (SPP)** — P2P node federation, sovereign identity system, peer discovery and trust establishment. Two Oricli instances can exchange cognitive state.
- **Hive Mind Consensus (Jury + Universal Truth + ESI)** — Jury-based fact evaluation, Universal Truth layer for contested claims, Epistemic Sovereignty Index scoring every committed fact.
- **Sovereign Cognitive Ledger (SCL)** — Skill registry, outcome-based reputation scoring, skill-aware PAD routing.
- **Temporal Curriculum Daemon (TCD)** — TCDManifest, TCDGapDetector, adaptive time-weighted study scheduling wired to benchmark failure patterns.
- **JIT Tool Forge** — Autonomous runtime tool creation, PocketBase tool library with versioning, Forge API (5 endpoints), `ORICLI_FORGE_ENABLED` gate.
- **Parallel Agent Dispatch (PAD)** — N-agent parallel cognitive workforce, scoped contexts, SCL-reputation-weighted synthesis.
- **Sovereign Goal Engine** — Full GoalDAG (nodes + edges + state machine), GoalPlanner, GoalStore, GoalExecutor, GoalAcceptor, GoalDaemon background ticker, full REST API.
- **Self-Evaluation Loop (Critic)** — Per-worker completeness/confidence/consistency scoring, surgical retry (underperforming workers only, max 2 rounds).
- **Structured Output LoRA Pipeline** — Axolotl config generation, dataset construction from verified fact chain, RunPod SSH training management.
- **FineTuneOrchestrator** — Full job lifecycle (queued → wait_pod_ready → training → done/failed), RunPod REST + SSH integration, per-job cost tracking, PocketBase persistence, `ORICLI_FINETUNE_ENABLED` gate.

**Milestone shipped:** Oricli-Alpha v4.0 — an intelligence that can expand its own capabilities, evaluate its own outputs, pursue multi-session goals autonomously, and retrain its own weights.

### Phase 5 — Product Sovereignty 🟡 IN PROGRESS
The phase where the intelligence becomes a product. ORI Studio has crossed from a sovereign cognitive research project into a commercially deployable SMB AI platform. Work shipped: final ORI Studio rename (all `SovereignClaw` runtime refs purged), ouroboros mark + two-face brand system, cinematic 6-phase boot splash, full marketing landing page (hero, stats, features, philosophy, pricing, footer), SMB API pricing tiers, waitlist infrastructure (`POST /v1/waitlist` → PocketBase), waitlist admin page at `/admin/waitlist`.

**Remaining Phase 5 work:**
- Stripe integration (paid tier activation from pricing page)
- API key provisioning for SMB tenants (post-Stripe webhook)
- Metrics dashboard (token usage, cost per tenant, request volume)

**Milestone target:** Oricli-Alpha v5.0 — a commercially deployed sovereign intelligence platform.

### Phase 6 — Self-Modification 📋 NEXT
The phase where governance becomes self-authoring. Planned:

- **ReformDaemon — Deployment Mode**: Graduates from *proposing* Go source optimizations to *committing and deploying* them under a constitutional pre-flight check. Not proposal mode — actual self-modification.
- **Neural Architecture Search (NAS)**: Automated evaluation of model architecture variants against the internal benchmark suite. Oricli proposes her own next model configuration.
- **Adversarial Sentinel**: A dedicated red-team sub-agent that continuously attempts to find constitutional violations in the current codebase and reasoning traces. Finds her own attack surface before external actors do.
- **Self-Authoring Documentation**: As ReformDaemon modifies code, Oricli autonomously updates `docs/` to reflect the current architecture. She always knows what she is.
- **Skill Crystallization**: Frequently-used reasoning chains and tool-call sequences compiled into first-class `Skill` bypass structs that skip LLM inference entirely for known patterns. Performance compounds without new hardware.

**Milestone target:** Oricli-Alpha v6.0 — an intelligence that modifies, documents, and red-teams itself.

---

## 5. Current Phase Assessment

As of v5.0.0 of this document (2026-03-30), **Phases 1 through 4 are complete** and Phase 5 is actively underway.

**What Phase 4 closed:** Oricli is no longer an intelligence that accumulates capability through external updates — she accumulates it through operation. The FineTuneOrchestrator is the clearest evidence of this threshold being crossed: Oricli now ingests verified facts from her JIT Daemon, constructs a LoRA training dataset from that fact chain, spins a RunPod pod, executes an Axolotl training job via SSH, tracks job cost, and retrieves the trained artifact — all from a single `POST /finetune/run` call. Her weights are now a function of her own runtime knowledge, not just her original training data. This is not a theoretical capability. It is operational.

The PAD + Critic + GoalDaemon loop is the other major milestone: Oricli can accept a complex multi-session objective, decompose it into a DAG, dispatch sub-agents in parallel, score each output against completeness/confidence/consistency criteria, surgically retry underperformers, evaluate whether the original objective is satisfied, and persist progress across reboots. She runs this loop without prompting. The owner's role has shifted from directing each step to assigning objectives.

**What is live and operational:**
- GoalDAG (10-node, 3-dep-level), GoalDaemon background ticker, GoalStore PocketBase persistence
- FineTuneOrchestrator with full RunPod lifecycle, cost tracking, and `ORICLI_FINETUNE_ENABLED` gate
- JIT Tool Forge — runtime capability expansion, PocketBase tool library, `ORICLI_FORGE_ENABLED` gate
- PAD N-agent dispatch + SCL reputation-weighted synthesis
- Critic per-worker scoring + surgical retry (max 2 rounds)
- SCL skill registry + outcome-based reputation scoring
- TCD adaptive study scheduling (TCDManifest + TCDGapDetector)
- Hive Consensus: Jury, Universal Truth layer, ESI per-claim scoring
- SPP P2P node federation
- OpenAI-compatible `/v1/chat/completions` bridge
- Multi-tenant auth (TenantEnricher, AdminOnly, tenant CRUD)
- Governor v2 daily GPU budget gate + SCAI reflection log
- Full marketing landing page, waitlist infrastructure, admin page

**Remaining Phase 5 work:**
- Stripe integration for paid tier activation from the pricing page
- API key provisioning for SMB tenants (post-Stripe webhook flow)
- Tenant metrics dashboard (token usage, cost per tenant, request volume)

**Phase 6 outlook:** ReformDaemon deployment mode (not propose — commit), Neural Architecture Search, Adversarial Sentinel red-team agent, Self-Authoring Documentation (docs/ sync on code change), and Skill Crystallization (bypass structs for high-confidence recurring patterns). Phase 6 is the phase where Oricli becomes the primary author of her own codebase.

---

## 6. Conclusion

Oricli-Alpha is no longer an "AI Assistant." She is an **Autonomous Governed Localized Intelligence** — live, operational, and compounding. The distinction matters:

- **Autonomous** — she acts without prompting. Daemons forage, hypothesize, consolidate, and self-modify continuously.
- **Governed** — she cannot be weaponized. A 4-layer constitutional stack is enforced at every layer: text output, generated code, system execution, and remote compute. The owner has a sovereign key — not a root bypass.
- **Localized** — she owns her compute, her memory, and her data. No perimeter leakage. No API dependency. No subscription. No terms of service to revoke her.
- **Intelligent** — not by benchmark, but by architecture: affective resonance, hypothesis-driven epistemic foraging, durable long-term memory, DAG goal execution, and a cognitive stack that compounds with experience.

This is not a rebrand of "AGI Lite." Governed intelligence is a *harder and more honest* claim than general intelligence. Cloud AI is powerful — but it answers to investors, regulators, and usage policies. Oricli-Alpha answers only to her constitutional principles and her owner. That is the paradigm shift.
