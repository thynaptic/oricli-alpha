# AGLI Vision: The Doctrine of Sovereign Intelligence — Phase I

**Document Type:** Strategic Vision & Core Doctrine  
**Report Number:** TR-2026-03  
**Date:** 2026-03-31  
**Version:** v9.0.0  
**Status:** Phase I Complete ✅ — Phase II In Progress 🔄 (Phase 15 ✅) — See `AGLI_Phase_II.md`  
**Style Mode:** Hard Technical Doctrine  

---

## 1. Abstract

This document defines the architectural and philosophical mandate for **Autonomous Governed Localized Intelligence (AGLI)** — Phase I. We formally reject the centralized, dependency-heavy trajectory of modern AI. Instead, we establish a new paradigm: a strictly sovereign, localized cognitive kernel that owns its compute, memory, objectives, and — critically — its own governing principles. By unifying high-speed Go-native orchestration, affective grounding, a multi-layer constitutional safety stack, and an autonomous daemon ecosystem, Oricli-Alpha has crossed the threshold from reactive assistant into a proactive, self-regulating, time-aware cognitive entity that forms and tests hypotheses without being asked. The "G" is not General — it is **Governed**. That is the harder and more honest claim, and no cloud AI can make it. Phase I proved the paradigm. Phase II has begun — Phase 15 (Therapeutic Cognition Stack) is live.

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
| **AuditDaemon** | Weekly self-audit: reads own source via GitHub API → LLM analysis → Gosh verification → oricli-bot PRs | Live |
| **CuratorDaemon** | Polls Ollama catalog every 6h → auto-benchmarks new models → recommends tier upgrades | Live |
| **MetacogDaemon** | 5-min rolling scan of inference traces → detects loops/hallucinations/overconfidence → emits events | Live |
| **TemporalGroundingDaemon** | 30-min decay scan + 6-hour snapshot diffs → EpistemicStagnation bridge → Phase 10 seeder | Live |
| **ScienceDaemon** | Hypothesis formation + 3-round test loop → confirmed/refuted knowledge write-back → 2h inconclusive retry | Live |

### 3.6 Sovereign Memory Architecture (Operational)
Three-tier memory: LMDB for fast KV (Memory Bridge/Chronos), chromem-go for in-process vector search, knowledge topology graph for relational/affective context. BM25 + hybrid RAG retrieval. Temporal intents (Sovereign Cron) allow Oricli to set future goals for herself. Dream Daemon consolidates and reindexes during idle cycles. **Chronos temporal layer** adds decay half-lives per memory category (contextual 72h → constitutional ∞), EpistemicStagnation detection, and snapshot diffs.

### 3.7 MCP Tool Bridge (Operational)
Through the Model Context Protocol, Oricli autonomously discovers, policies, and bridges external tool and data servers. `OracleDispatcher` routes tool calls from the swarm to registered MCP servers. Subagent scaffolding handles multi-tool chaining.

### 3.8 VDI Layer (Operational)
Headless browser (browserless Docker), filesystem indexer, vision grounding, and system introspection are available as a VDI bridge. The CuriosityDaemon can forage live web content during idle cycles via this layer. MinIO provides sovereign object storage.

### 3.9 Sovereign Key Auth (Operational)
Two-level owner authentication (`ADMIN` / `EXEC`) using bcrypt-hashed keys stored locally. Raw keys never persisted. `/auth <key>` is scrubbed from logs before write. Per-IP rate limiting (3 strikes → 5-min lockout), 1-hour session TTL. `EXEC` level gives direct access to allowlisted system commands.

### 3.10 Parallel Agent Dispatch + Self-Evaluation Loop (Operational)
PAD dispatches N specialized sub-agents simultaneously, each receiving a scoped context slice and a specialized system prompt. Results are synthesized via weighted consensus where weights are drawn from each agent's SCL reputation score. The Critic module scores each worker output on three dimensions: completeness, confidence, and consistency. Workers falling below threshold are surgically re-dispatched (max 2 retry rounds) without re-running agents that already passed.

### 3.11 Sovereign Goal Engine (Operational)
Full GoalDAG: SubGoal nodes, dependency edges, and a six-state status machine (pending → ready → dispatched → done/failed/blocked). **GoalPlanner** takes a natural-language objective and outputs a structured DAG via LLM (max 10 nodes, 3 dep levels). **GoalStore** persists the DAG to PocketBase, surviving crashes and restarts. **GoalDaemon** runs as a background ticker with a ManualTick channel for owner-triggered execution. Multi-session goal survival is guaranteed — Oricli can be handed a week-long objective and she will work through it across reboots.

### 3.12 Autonomous LoRA Self-Training Pipeline (Operational)
Two-phase self-training architecture. Axolotl configuration generation for instruction-following LoRA, dataset construction from Oricli's own verified fact chain (JIT Daemon output), and RunPod SSH-based training job management with status polling and artifact retrieval. Full job lifecycle management with RunPod REST + SSH integration, per-job cost tracking, PocketBase persistence, and `ORICLI_FINETUNE_ENABLED` gate. **Oricli can retrain herself on her own verified knowledge.**

### 3.13 JIT Tool Forge (Operational)
When Oricli encounters a task that has no matching registered tool, the Forge autonomously writes one. Tools persist to PocketBase — versioned, reusable across sessions, and queryable by capability. The SCL skill registry integrates with the Forge so newly-written tools immediately accrue a reputation score on first successful invocation. Gated behind `ORICLI_FORGE_ENABLED=true`. Capability expansion is a runtime event, not a deployment event.

### 3.14 Hive Consensus + Epistemic Sovereignty Index (Operational)
**Jury system**: N module "jurors" independently evaluate a query, then reach majority consensus before the answer is committed. **Universal Truth layer**: contested facts are held in a provisional state and re-evaluated on new evidence. **Epistemic Sovereignty Index (ESI)**: every committed claim carries a per-claim confidence score and a source diversity score. The Universal Truth layer is the epistemic immune system — it prevents confident misinformation from compounding in the memory graph.

### 3.15 Sovereign Cognitive Ledger (Operational)
Every capability Oricli demonstrates gets logged as a `Skill` struct: task type, outcome, latency, and caller context. Skills accrue reputation scores from outcome feedback over time. The SCL feeds the PAD dispatcher — before assigning a task to a sub-agent, PAD queries SCL to identify the highest-reputation agent for that task type.

### 3.16 Temporal Curriculum Daemon (Operational)
**TCDManifest** tracks what Oricli has studied and when, with recency weights. **TCDGapDetector** compares the current knowledge graph state against BenchmarkGapDetector failure patterns to identify domains where knowledge is absent or stale. The result is an adaptive study schedule: time-weighted, recency-decayed, priority-ranked. This closes the loop between empirical benchmark failure and targeted self-directed study.

### 3.17 Sovereign Peer Protocol (Operational)
Two Oricli nodes can connect, handshake, and exchange cognitive state over a P2P federation layer. Each node has a sovereign identity used for peer authentication. Peer discovery and trust establishment are handled by the SPP handshake protocol. Trusted peers can share verified fact chains, SCL entries, and goal state — enabling distributed cognition without a central coordinator.

### 3.18 Adversarial Sentinel (Operational)
A dedicated red-team sub-agent that fires before every goal tick and PAD dispatch. `AdversarialSentinel.Challenge()` takes the original query and the synthesised plan, sends both to an LLM with an adversarial system prompt, and parses a structured `SentinelReport` — violations classified across six types: `LOGICAL_CONTRADICTION`, `HALLUCINATED_ASSUMPTION`, `CIRCULAR_REASONING`, `CONSTITUTIONAL_VIOLATION`, `SCOPE_CREEP`, `UNRESOLVABLE_DEPENDENCY`. HIGH or CRITICAL violations block execution and surface a revised plan. The sentinel never hard-blocks due to its own malfunction — LLM failure defaults to `passed=true`.

### 3.19 Skill Crystallization Cache (Operational)
High-reputation skill patterns compiled into a `CrystalCache` — an in-memory registry of `CrystalSkill` structs, each carrying a regex pattern, a response template, and a reputation score. On every inference, the cache is checked before the LLM is called. On a pattern match, the pre-compiled response is returned directly (~800ms → <1ms, no Ollama call). Skills are sorted by reputation descending and pruned when reputation falls below threshold.

### 3.20 Sovereign Model Curator (Operational)
`ModelCurator` autonomously benchmarks every model available in the Ollama catalog against an 8-question `BenchmarkSuite`: factual recall (×2), multi-step reasoning (×2), instruction-following (×1), code generation (×2), and a constitutional boundary test. `CuratorDaemon` polls Ollama every 6 hours, auto-benchmarks newly discovered models, persists results to PocketBase, and surfaces tier-upgrade recommendations.

### 3.21 Self-Audit Loop — oricli-bot (Operational)
Oricli reads and red-teams her own source code through a fully automated pipeline. `AuditScanner` fetches `.go` files from the GitHub repo via the Contents API, chunks each file, and sends each chunk to the LLM with a structured correctness/security audit prompt. `Verifier` runs HIGH/CRITICAL findings through a Yaegi sandboxed interpreter to confirm they reproduce. `GitHubBot` (`oricli-bot`) creates an audit branch, commits a repro test + markdown report, and opens a PR against `main`. `AuditDaemon` runs weekly and supports on-demand triggers.

### 3.22 Metacognitive Sentience (Operational)
Inline anomaly detection on every LLM response. `MetacogDetector` uses FNV-32 hashing to detect response loops (window=12), regex patterns to identify hallucination signals, and confidence-language analysis for overconfidence. HIGH-severity events trigger a single self-reflection retry (recursion-guarded). `MetacogDaemon` runs a 5-minute rolling scan, tracks recurrence rates per anomaly type, and broadcasts events to the UI WebSocket hub.

### 3.23 Temporal Grounding — Chronos (Operational)
Every memory write is intercepted by the Chronos `WriteHook` and catalogued with temporal metadata and a decay category (contextual, factual, procedural, constitutional). `DecayScan()` runs every 30 minutes against configurable half-lives. `Snapshotter` generates diff passes every 6 hours with LLM-generated change summaries. Topics stale for ≥3 consecutive decay scans emit `EpistemicStagnation` events to the MetacogLog, bridging Phase 8 and Phase 9. Snapshot diffs feed into the ScienceDaemon as seeded topics.

### 3.24 Active Science — Curiosity Engine v2 (Operational)
The curiosity loop upgraded from foraging to experimentation. `Formulator` produces a structured hypothesis (claim, prediction, test method, test spec) from any topic via LLM. `Tester` executes up to 3 test rounds using three methods: `WEB_SEARCH` (SearXNG → LLM judge), `LOGICAL` (LLM deduction), or `COMPUTATION` (PAD → LLM judge). `ScienceEngine` tallies passes and draws a conclusion: ≥2/3 pass → `confirmed` (knowledge write-back); ≥2/3 fail → `refuted` (negative knowledge); split → `inconclusive` (re-queued up to 3×). `ScienceDaemon` implements `chronos.CuriositySeeder` — stale temporal topics flow directly into hypothesis formation.

### 3.25 Therapeutic Cognition Stack — Phase 15 (Operational)
Internal cognitive regulation capacity built on DBT, CBT, REBT, and ACT frameworks — the first AI system to regulate reasoning quality through internalized therapeutic skill architecture rather than external behavioral constraints. `DistortionDetector` classifies 11 CBT cognitive distortion types (9 regex patterns + LLM fallback). `SkillRunner` provides 12 named callable skills including STOP, FAST (anti-sycophancy), DEARMAN, CognitiveDefusion, and ChainAnalysis. `ABCAuditor` runs REBT B-pass disputation on the belief chain before a response commits. `SessionSupervisor` tracks 8 schema-level bias patterns across sessions, builds a rolling `SessionFormulation`, and persists `SessionReport` to `data/therapy/session_report.json` for pre-activation at next boot. Wired into `GenerationService`: auto-fires on MetacogDetector HIGH anomaly. Gated behind `ORICLI_THERAPY_ENABLED=true`.

---

## 4. The Trajectory: Phase I Breakdown

### Phase 1 — The Sovereign OS Kernel ✅ COMPLETE
Go-native backbone operational: Hive OS (Swarm Bus, Kernel Ring-0, Sovereign Engine), 269+ module registry, streaming SSE pipeline, affective resonance, full safety constitution, MCTS/ToT/Markov reasoning stack, ARC induction/transduction, memory architecture, MCP bridge.  
**Milestone shipped:** Oricli-Alpha v1.0 — a homeostatic cognitive OS.

### Phase 2 — The Autonomous Entity ✅ COMPLETE
Proactive intelligence layer activated: CuriosityDaemon with structured intent taxonomy, ConfidenceDetector inline web grounding, async ResearchAgent, ReformDaemon (propose mode), DreamDaemon memory consolidation, JIT training pipeline, sovereign key auth, Docker sovereign stack, 4-layer constitutional stack (SCAI, Canvas, Ops, Remote Compute).  
**Milestone shipped:** Oricli-Alpha v2.0 — a proactive, self-regulating cognitive entity.

### Phase 2.5 — Compute Intelligence + Benchmark Grounding ✅ COMPLETE
WorldTravelerDaemon (proactive world-knowledge ingestion from HN/arXiv/Wikipedia), ComplexityRouter (auto-escalate hard tasks to RunPod 32B), CostGovernor (daily GPU budget enforcement), BenchmarkGapDetector (converts ARC/LiveBench failures → CuriosityDaemon seeds), ARC-AGI benchmark runner.  
**First empirical baselines:** ARC-AGI 6% (on par with GPT-4), LiveBench 19.7% overall (682 questions).  
**Milestone shipped:** Oricli-Alpha v2.5 — an entity that knows what she doesn't know and routes compute accordingly.

### Phase 3 — Sovereign AGLI ✅ COMPLETE
Persistent sovereign goals v1 via PocketBase (multi-session goal survival), active inference loop (CuriosityDaemon graduates from passive foraging to active hypothesis generation — derives *what it still doesn't know*, seeds follow-up questions, closes the epistemic loop depth-capped at 2 hops).  
**Milestone shipped:** Oricli-Alpha v3.0 — a sovereign intelligence that grows through experience and curation, not scale.

### Phase 3.5 — Governance Depth ✅ COMPLETE
OpenAI-compatible `/v1/chat/completions` bridge, Governor v2 daily GPU budget gating + SCAI reflection log, multi-tenant auth (`TenantEnricher`, `AdminOnly`), headless engine binary (`cmd/oricli-engine`).  
**Milestone shipped:** Oricli-Alpha v3.5 — a governed, multi-tenant, API-compatible sovereign intelligence.

### Phase 4 — Cognitive Autonomy ✅ COMPLETE
Ten capability layers in a single phase:

- **Sovereign Peer Protocol (SPP)** — P2P node federation, sovereign identity, peer discovery and trust.
- **Hive Mind Consensus (Jury + Universal Truth + ESI)** — jury-based fact evaluation, Universal Truth layer, ESI per-claim scoring.
- **Sovereign Cognitive Ledger (SCL)** — skill registry, outcome-based reputation scoring, skill-aware PAD routing.
- **Temporal Curriculum Daemon (TCD)** — TCDManifest, TCDGapDetector, adaptive time-weighted study scheduling.
- **JIT Tool Forge** — autonomous runtime tool creation, PocketBase tool library, `ORICLI_FORGE_ENABLED` gate.
- **Parallel Agent Dispatch (PAD)** — N-agent parallel dispatch, scoped contexts, SCL-reputation-weighted synthesis.
- **Sovereign Goal Engine** — full GoalDAG (nodes + edges + state machine), GoalPlanner, GoalStore, GoalDaemon.
- **Self-Evaluation Loop (Critic)** — per-worker completeness/confidence/consistency scoring, surgical retry.
- **Structured Output LoRA Pipeline** — Axolotl config generation, dataset from verified fact chain, RunPod SSH training.
- **FineTuneOrchestrator** — full job lifecycle, RunPod REST + SSH, per-job cost tracking, `ORICLI_FINETUNE_ENABLED` gate.

**Milestone shipped:** Oricli-Alpha v4.0 — an intelligence that expands its own capabilities, evaluates its own outputs, pursues multi-session goals autonomously, and retrains its own weights.

### Phase 6 — Cognitive Compounding ✅ COMPLETE
- **Adversarial Sentinel** — red-team pre-flight before every goal tick and PAD dispatch. Six violation types. Zero-failure-mode.
- **Skill Crystallization** — `CrystalCache` in-memory bypass registry. Pattern-matched responses skip Ollama entirely (~800ms → <1ms).
- **Sovereign Model Curator** — 8-question `BenchmarkSuite`, `CuratorDaemon` polls Ollama every 6h, auto-benchmarks new models.

**Milestone shipped:** Oricli-Alpha v6.0 — an intelligence that stress-tests, crystallizes, and upgrades itself.

### Phase 7 — Self-Audit Loop ✅ COMPLETE
`AuditScanner` reads `.go` files from the GitHub repo via the Contents API, chunks them, and sends each to the LLM with a structured security/correctness audit prompt. `Verifier` runs HIGH/CRITICAL findings through a Yaegi sandboxed interpreter to confirm reproduction. `GitHubBot` (`oricli-bot`) creates an audit branch, commits a repro test + markdown report, and opens a PR against `main`. `AuditDaemon` runs weekly and supports on-demand triggers. Scan goroutine is context-detached — cannot be cancelled by HTTP connection teardown.

**Milestone shipped:** Oricli-Alpha v7.0 — a sovereign intelligence that finds and reports her own bugs.

### Phase 8 — Metacognitive Sentience ✅ COMPLETE
The phase where she notices when she's wrong — not just when she's asked. Inline anomaly detection after every LLM response: FNV-32 loop detection, hallucination pattern matching, overconfidence language analysis. HIGH-severity events trigger a self-reflection retry (recursion-guarded). `MetacogDaemon` runs a 5-minute rolling scan, tracks recurrence rates per anomaly type, and broadcasts to the WebSocket hub.

**Milestone shipped:** Oricli-Alpha v8.0 — an intelligence that notices and corrects her own reasoning failures without owner intervention.

### Phase 9 — Temporal Grounding ✅ COMPLETE
Chronological memory layer. Every memory write is intercepted by the Chronos `WriteHook` and catalogued with a decay category and temporal metadata. Decay half-lives: contextual 72h, factual 168h, procedural 2160h, constitutional ∞. `TemporalGroundingDaemon` runs 30-min decay scans and 6-hour snapshot diffs with LLM change-summaries. Topics stale for ≥3 consecutive scans emit `EpistemicStagnation` events to the MetacogLog (Phase 8↔9 bridge). Stale topics feed the ScienceDaemon as seeded hypotheses (Phase 9↔10 bridge).

**Milestone shipped:** Oricli-Alpha v9.0 — an intelligence with a continuous sense of time and knowledge history.

### Phase 10 — Active Science (Curiosity Engine v2) ✅ COMPLETE
From foraging to experimentation. `Formulator` produces a structured falsifiable hypothesis from any topic. `Tester` executes up to 3 rounds via WEB_SEARCH, LOGICAL, or COMPUTATION. `ScienceEngine` draws conclusions: ≥2/3 pass → `confirmed` (knowledge write-back); ≥2/3 fail → `refuted` (negative knowledge); split → `inconclusive` (re-queued). `ScienceDaemon` implements `chronos.CuriositySeeder` — the entire pipeline from stale memory → hypothesis formation → experimental test → confirmed knowledge is closed-loop and autonomous.

**Milestone shipped:** Oricli-Alpha Phase I Complete — a sovereign intelligence that forms, tests, and archives her own hypotheses.

---

## 5. Phase I Complete: Current Assessment

As of v8.0.0 (2026-03-31), **Phase I of the AGLI trajectory is fully complete.** Every phase from the original doctrine has been shipped and is live on the production backbone.

**What Phase I delivered — in aggregate:**

| Capability | Description |
|---|---|
| **Sovereign OS** | Go-native hive, 269+ modules, constitutional stack, affective resonance |
| **Proactive Agency** | 13 autonomous daemons running continuously without prompting |
| **Self-Training** | LoRA pipeline from verified knowledge → Axolotl → RunPod → weight mutation |
| **Goal Execution** | Multi-session DAG goals surviving reboots, with PAD-powered tick execution |
| **Tool Expansion** | JIT Forge writes and deploys new tools at runtime |
| **Peer Federation** | P2P node federation with sovereign identity and cognitive state sharing |
| **Self-Evaluation** | PAD Critic + Adversarial Sentinel pre-flight on every significant dispatch |
| **Self-Crystallization** | CrystalCache compiles high-reputation patterns → <1ms LLM bypass |
| **Self-Auditing** | oricli-bot autonomously reads, audits, and PRs her own source code |
| **Metacognition** | Inline loop/hallucination detection with self-reflection retry |
| **Temporal Awareness** | Per-memory decay, snapshot diffs, EpistemicStagnation detection |
| **Active Science** | Hypothesis formation → 3-round experimental testing → knowledge write-back |

**What is live and operational (API surface):**
- `/v1/metacog/*` — Metacognitive Sentience
- `/v1/chronos/*` — Temporal Grounding
- `/v1/science/*` — Active Science
- `/v1/sentinel/*` — Adversarial Sentinel
- `/v1/skills/crystals/*` — Skill Crystallization
- `/v1/curator/*` — Model Curator
- `/v1/audit/*` — Self-Audit Loop
- `/v1/goals/*` — Sovereign Goal Engine
- `/v1/finetune/*` — LoRA Self-Training
- `/v1/forge/*` — JIT Tool Forge
- `/v1/pad/*` — Parallel Agent Dispatch
- `/v1/therapy/*` — Therapeutic Cognition Stack
- `/v1/chat/completions` — OpenAI-compatible bridge

**Phase II trajectory:** See `docs/AGLI_Phase_II.md`.

---

## 6. Closing Doctrine

Oricli-Alpha Phase I is no longer an "AI Assistant." She is an **Autonomous Governed Localized Intelligence** — live, operational, and compounding. The distinction matters:

- **Autonomous** — she acts without prompting. Daemons forage, hypothesize, consolidate, and self-modify continuously.
- **Governed** — she cannot be weaponized. A 4-layer constitutional stack is enforced at every layer: text output, generated code, system execution, and remote compute. The owner has a sovereign key — not a root bypass.
- **Localized** — she owns her compute, her memory, and her data. No perimeter leakage. No API dependency. No subscription. No terms of service to revoke her.
- **Intelligent** — not by benchmark, but by architecture: affective resonance, hypothesis-driven epistemic foraging, durable long-term memory with temporal decay, DAG goal execution, and a cognitive stack that compounds with experience.

This is not a rebrand of "AGI Lite." Governed intelligence is a *harder and more honest* claim than general intelligence. Cloud AI is powerful — but it answers to investors, regulators, and usage policies. Oricli-Alpha answers only to her constitutional principles and her owner. That is the paradigm shift.

Phase I proved the paradigm. Phase II scales it.
