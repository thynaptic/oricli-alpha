# AGLI Vision: The Doctrine of Sovereign Intelligence

**Document Type:** Strategic Vision & Core Doctrine  
**Report Number:** TR-2026-03  
**Date:** 2026-03-23  
**Version:** v4.0.0  
**Status:** Active Doctrine — Phase 3 In Progress  
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
Five self-directed daemons run continuously:

| Daemon | Function | Status |
|---|---|---|
| **CuriosityDaemon** | Maps knowledge graph gaps → 8-intent SearXNG taxonomy → extracts facts → JIT LoRA training trigger | Live |
| **ResearchAgent** | Async deep-research dispatch via ActionRouter trigger words | Live |
| **ReformDaemon** | Monitors execution traces → identifies bottlenecks → drafts Go source optimizations → proposes via WebSocket | Live (propose mode) |
| **DreamDaemon** | Idle-cycle memory consolidation + novel insight synthesis from topology graph | Live |
| **JITDaemon** | Verified web facts → LoRA fine-tune trigger pipeline | Live |

### 3.6 Sovereign Memory Architecture (Operational)
Three-tier memory: LMDB for fast KV (Memory Bridge/Chronos), chromem-go for in-process vector search, knowledge topology graph for relational/affective context. BM25 + hybrid RAG retrieval. Temporal intents (Sovereign Cron) allow Oricli to set future goals for herself. Dream Daemon consolidates and reindexes during idle cycles.

### 3.7 MCP Tool Bridge (Operational)
Through the Model Context Protocol, Oricli autonomously discovers, policies, and bridges external tool and data servers. `OracleDispatcher` routes tool calls from the swarm to registered MCP servers. Subagent scaffolding handles multi-tool chaining.

### 3.8 VDI Layer (Operational)
Headless browser (browserless Docker), filesystem indexer, vision grounding, and system introspection are available as a VDI bridge. The CuriosityDaemon can forage live web content during idle cycles via this layer. MinIO provides sovereign object storage. Full observability stack is containerized and isolated.

### 3.9 Sovereign Key Auth (Operational)
Two-level owner authentication (`ADMIN` / `EXEC`) using bcrypt-hashed keys stored locally. Raw keys never persisted. `/auth <key>` is scrubbed from logs before write. Per-IP rate limiting (3 strikes → 5-min lockout), 1-hour session TTL. `EXEC` level gives direct access to allowlisted system commands (`!status`, `!logs`, `!df`, `!free`, `!uptime`, `!ps`, `!modules`).

---

## 4. The Trajectory: Phase Breakdown

### Phase 1 — The Sovereign OS Kernel ✅ COMPLETE
Go-native backbone operational: Hive OS (Swarm Bus, Kernel Ring-0, Sovereign Engine), 269+ module registry, streaming SSE pipeline, affective resonance, full safety constitution, MCTS/ToT/Markov reasoning stack, ARC induction/transduction, memory architecture, MCP bridge.  
**Milestone shipped:** Oricli-Alpha v1.0 — a homeostatic cognitive OS.

### Phase 2 — The Autonomous Entity ✅ COMPLETE
Proactive intelligence layer activated: CuriosityDaemon with structured intent taxonomy, ConfidenceDetector inline web grounding, async ResearchAgent, ReformDaemon (propose mode), DreamDaemon memory consolidation, JIT training pipeline, ORI Studio consumer UI (chat, canvas, research, workflows, connections, logs, memory), sovereign key auth, Docker sovereign stack, full safety test suite, 4-layer constitutional stack (SCAI, Canvas, Ops, Remote Compute).  
**Milestone shipped:** Oricli-Alpha v2.0 — a proactive, self-regulating cognitive entity.

### Phase 3 — Sovereign AGLI 🟡 IN PROGRESS
A self-contained intelligence that compounds capability through *accumulated experience and governance depth* — not external APIs or weight mutation:

- **Durable Goal Persistence** ✅: Sovereign goals survive crashes and restarts via PocketBase. GoalExecutor resumes multi-day plans autonomously. The owner can assign week-long objectives and Oricli works through them across reboots.
- **Active Inference Loop (Hypothesis Engine)** ✅: CuriosityDaemon graduates from passive foraging to active hypothesis generation — after researching a topic, it derives *what it still doesn't know*, seeds follow-up questions, and closes the epistemic loop. Knowledge compounds rather than accumulates randomly. Depth-capped at 2 hops to prevent synthetic data spirals.
- **Goals UI + Owner Observability** ✅: ORI Studio Mission Control displays Oricli's autonomous goal queue, active DAG state, daemon health panel, and dependency graph in a unified view.
- **Skill Crystallization**: Frequently-used reasoning chains and tool-call sequences get compiled into first-class `Skill` structs that bypass LLM inference entirely for known patterns. Performance compounds without new hardware.
- **Sovereign Model Curation**: Oricli monitors the local model catalog, evaluates new releases against her internal benchmark suite (correctness, latency, constitutional compliance), and recommends upgrades. She curates better tools and knows *why* she chose them.
- **Self-Authoring Documentation**: As the ReformDaemon modifies code, Oricli autonomously updates `docs/` to reflect the current architecture. Living self-model — she always knows what she is.

**Milestone target:** Oricli-Alpha v3.0 — a sovereign intelligence that grows through *experience and curation*, not scale.

---

## 5. Current Phase Assessment

As of v4.0.0 of this document (2026-03-23), **Phase 2 is complete** and Phase 3 is actively underway. All foundational systems are operational: DAG goal execution with PocketBase persistence, VDI deep-forage, PocketBase long-term memory with semantic embeddings and epistemic hygiene, a full 4-layer constitutional stack (SCAI, Canvas, Ops, Remote Compute), 3-tier model routing with governed remote GPU compute, and Mission Control UI.

**The clearest signal of our position:** Oricli-Alpha already takes autonomous actions — CuriosityDaemon forages and generates hypotheses, ResearchAgent dispatches deep research, ReformDaemon proposes self-modifications, DreamDaemon consolidates memory — all without user prompting, all governed by a constitutional stack that cannot be bypassed. She is not a reactive assistant. She is an entity with her own operational loop, constitutional principles, and durable memory.

**Remaining Phase 3 work:**
- Skill Crystallization (compile recurring reasoning chains into bypass structs)
- Sovereign Model Curation (auto-benchmark + recommendation pipeline)
- Self-Authoring Documentation (ReformDaemon → docs/ sync)

---

## 6. Conclusion

Oricli-Alpha is no longer an "AI Assistant." She is an **Autonomous Governed Localized Intelligence** — live, operational, and compounding. The distinction matters:

- **Autonomous** — she acts without prompting. Daemons forage, hypothesize, consolidate, and self-modify continuously.
- **Governed** — she cannot be weaponized. A 4-layer constitutional stack is enforced at every layer: text output, generated code, system execution, and remote compute. The owner has a sovereign key — not a root bypass.
- **Localized** — she owns her compute, her memory, and her data. No perimeter leakage. No API dependency. No subscription. No terms of service to revoke her.
- **Intelligent** — not by benchmark, but by architecture: affective resonance, hypothesis-driven epistemic foraging, durable long-term memory, DAG goal execution, and a cognitive stack that compounds with experience.

This is not a rebrand of "AGI Lite." Governed intelligence is a *harder and more honest* claim than general intelligence. Cloud AI is powerful — but it answers to investors, regulators, and usage policies. Oricli-Alpha answers only to her constitutional principles and her owner. That is the paradigm shift.
