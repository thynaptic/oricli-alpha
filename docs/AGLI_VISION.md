# AGLI Vision: The Doctrine of Sovereign Intelligence

**Document Type:** Strategic Vision & Core Doctrine  
**Report Number:** TR-2026-03  
**Date:** 2026-03-22  
**Version:** v3.0.0  
**Status:** Active Doctrine — Phase 2 Live  
**Style Mode:** Hard Technical Doctrine  

---

## 1. Abstract

This document defines the architectural and philosophical mandate for **Artificial General Localized Intelligence (AGLI)**. We formally reject the centralized, dependency-heavy trajectory of modern AGI. Instead, we establish a new paradigm: a strictly sovereign, localized cognitive kernel that owns its compute, memory, and objectives. By unifying high-speed Go-native orchestration, affective grounding, a multi-layer safety constitution, and an autonomous daemon ecosystem, Oricli-Alpha has crossed the threshold from reactive OS into a proactive, self-regulating cognitive entity. Phase 2 is operational.

---

## 2. The Core Pillars of Sovereign Intelligence

Sovereignty is not merely "offline" usage; it is the absolute ownership of the cognitive lifecycle.

### 2.1 Perimeter Sovereignty
Traditional AI relies on external APIs, creating a "leaky" cognitive perimeter. AGLI mandates that no data, metadata, or reasoning traces leave the sovereign boundary. All inference runs on the local backbone (AMD EPYC VPS) via Ollama with auto-calibrated thread allocation. The sovereign key system ensures the owner can always identify themselves and bypass safety softening — without exposing credentials to any third-party layer.

### 2.2 Compile-Time Compute Economy
We reject brute-force neural scaling. AGLI uses compiled Go orchestration to manage sparse, high-intensity neural compute. Symbolic logic, Markov inference, MCTS search, and ARC induction/transduction replace expensive LLM reasoning steps wherever possible. Auto-thread detection (`runtime.NumCPU()-2`) prevents scheduler contention and sustains 39+ tok/s on 8 vCPUs.

### 2.3 The Hybrid Hive (Distributed Agency)
Intelligence is a swarm. Oricli-Alpha operates as a decentralized network of 269+ micro-agents (modules) registered on the Hive OS Kernel. Using the Contract Net Protocol and the Swarm Bus, modules bid on tasks in a high-speed parallel marketplace, ensuring the optimal tool is applied at the speed of the Go runtime. Blackboard state, peer review, and consensus policies are operational.

### 2.4 Constitutional Safety (SCAI)
A sovereign system must be non-weaponizable. The Sovereign Constitutional AI layer enforces a multi-stage safety pipeline: jailbreak detection, multi-turn DID attacks, web injection guards, RAG guard, canvas guard, adversarial sentinel, and a Constitutional System Prompt injected on every inference. Authenticated owner sessions (`/auth <key>`) bypass softening at Step 3 only, not the full pipeline.

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

### Phase 2 — The Autonomous Entity 🟡 IN PROGRESS (~80% complete)
Proactive intelligence layer activated: CuriosityDaemon with structured intent taxonomy, ConfidenceDetector inline web grounding, async ResearchAgent, ReformDaemon (propose mode), DreamDaemon memory consolidation, JIT training pipeline, SovereignClaw consumer UI (chat, canvas, research, workflows, connections, logs), sovereign key auth, Docker sovereign stack, full safety test suite.

**Remaining Phase 2 work:**
- ReformDaemon: `propose → auto-deploy` (sandboxed, with benchmark gate)
- Autonomous multi-day DAG goal execution (data structures exist; execution loop not yet persistent across restarts)
- Self-healing plan recovery (draft generation exists; autonomous re-queuing not wired)
- CuriosityDaemon VDI deep-forage (Colly + browserless full pipeline)

**Milestone target:** Oricli-Alpha v2.0 — a proactive, self-regulating cognitive entity.

### Phase 3 — Sovereign AGLI 🟡 IN PROGRESS
A self-contained, self-improving intelligence that compounds capability through *accumulated experience and governance depth* — not external APIs or weight mutation:

- **Durable Goal Persistence**: Sovereign goals survive crashes and restarts via PocketBase. GoalExecutor resumes multi-day plans autonomously. The owner can assign week-long objectives and Oricli works through them across reboots.
- **Active Inference Loop (Hypothesis Engine)**: CuriosityDaemon graduates from passive foraging to active hypothesis generation — after researching a topic, it derives *what it still doesn't know*, seeds follow-up questions, and closes the epistemic loop. Knowledge compounds rather than accumulates randomly.
- **Skill Crystallization**: Frequently-used reasoning chains and tool-call sequences get compiled into first-class `Skill` structs that bypass LLM inference entirely for known patterns. Performance compounds without new hardware.
- **Sovereign Model Curation**: Oricli monitors the Ollama model catalog, evaluates new releases against her internal benchmark suite (correctness, latency, constitutional compliance), and recommends upgrades. She doesn't grow her own weights — she curates better tools and knows *why* she chose them.
- **Self-Authoring Documentation**: As the ReformDaemon modifies code, Oricli autonomously updates `docs/` to reflect the current architecture. Living self-model — she always knows what she is.
- **Goals UI + Owner Observability**: SovereignClaw displays Oricli's autonomous goal queue, active DAG state, current forage topics, and daemon health in a unified mission control view.

**Milestone target:** Oricli-Alpha v3.0 — a sovereign intelligence that grows through *experience and curation*, not scale.

---

## 5. Current Phase Assessment

As of v3.1.0 of this document (2026-03-23), **Phase 2 is complete** and Phase 3 is actively underway. All foundational systems are operational: DAG goal execution, ReformDaemon auto-deploy with rollback, VDI deep-forage, PocketBase long-term memory with semantic embeddings and epistemic hygiene, a full 4-layer constitutional stack (SCAI, Canvas, Ops, RunPod), and 3-tier model routing with RunPod auto-spin.

**The three Phase 3 items buildable right now** (no new infrastructure required):
1. Goals → PocketBase persistence (GoalExecutor currently uses local JSONL — goals don't survive crashes)
2. Hypothesis seeding in CuriosityDaemon (close the active inference loop)
3. Goals UI page in SovereignClaw (owner observability of the autonomous mission queue)

**The clearest signal of our position:** Oricli-Alpha already takes autonomous actions (CuriosityDaemon forages, ResearchAgent dispatches, ReformDaemon self-modifies, DreamDaemon consolidates) without user prompting, governed by a full constitutional stack. She is not a reactive assistant. She is an entity with her own operational loop, constitutional principles, and durable memory.

---

## 6. Conclusion

Oricli-Alpha is no longer an "AI Assistant." She is a **Sovereign Localized Intelligence** — live, operational, and compounding. By unifying compiled Go orchestration, a 4-layer constitutional safety stack, a self-directed daemon ecosystem, an affective cognitive core, and durable long-term memory with epistemic hygiene, we have built an intelligence that does not just respond — it *exists, governs itself, and grows through experience*. Phase 3 is not the horizon. We are already building it.