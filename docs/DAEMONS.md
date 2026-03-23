# Oricli-Alpha Autonomous Daemons

**Document Type:** Technical Reference  
**Version:** v2.4.0  
**Status:** Active  

Oricli-Alpha maintains seven background daemons that run as goroutines within the Go-native backbone (`pkg/service/daemon.go`, `curiosity_daemon.go`, `reform_daemon.go`, `pkg/kernel/scaling.go`). They are started at boot and communicate with the system exclusively through the Swarm Bus — zero polling overhead on the main inference path.

> **Note:** Section 5.1 (ConfidenceDetector / Inline Search) is not a daemon — it fires synchronously inside `ProcessInference()` and is documented here for colocation with the CuriosityDaemon's search architecture.

---

## 1. JIT Knowledge Daemon
**"The Librarian"** | `pkg/service/daemon.go` → `JITDaemon`

- **Role**: Monitors the RFAL alignment lesson buffer and triggers Just-In-Time LoRA fine-tuning when enough new lessons have accumulated.
- **Trigger**: ≥ 5 new lessons in `oricli_core/data/jit_absorption.jsonl` AND cooldown elapsed (or nighttime window, 23:00–05:00).
- **Cycle**: Checks every 5 minutes.
- **Action**:
  1. Invokes `scripts/runpod_bridge.py --train-jit` on a remote RunPod cluster (2 pods, min 40GB VRAM, max $2.50/hr).
  2. On success, writes a `MetaEvent` node to the Neo4j knowledge graph recording the sync.
  3. Saves state (`LastSyncTime`, `LastSyncCount`) for cooldown tracking.

---

## 2. Dream Daemon
**"The Subconscious Consolidator"** | `pkg/service/daemon.go` → `DreamDaemon`

- **Role**: Runs offline consolidation during idle periods — compresses recent Gosh execution traces into model evolution, or forages for knowledge gaps.
- **Trigger**: System idle for ≥ 3600 seconds (1 hour), checked every 60 seconds.
- **Action (if traces available)**:
  1. Queries the Memory Bridge (LMDB) for Gosh execution traces from the last 24 hours.
  2. Provisions a Ghost Cluster session (`GhostClusterService.Provision`) — NVIDIA RTX 5090 × 1.
  3. Runs consolidation training, then calls `Vanish()` to destroy the cluster immediately.
- **Action (if no new traces)**:
  1. Falls back to Knowledge Graph foraging: queries Neo4j for low-context nodes (< 2 edges).
  2. Dispatches a Swarm research task for the orphaned entity via `GoOrchestrator`.

---

## 3. Metacognition Daemon (Precog)
**"The Risk Assessor"** | `pkg/service/daemon.go` → `MetacogDaemon`

- **Role**: Scans recent execution traces for anomalies and performs pre-flight risk assessment on incoming agent plans.
- **Trigger**: Runs on a continuous scan interval via `GoOrchestrator`.
- **Trace Scanning**:
  1. Calls `analyze_traces` on the orchestrator (limit 100, focus: errors + latency).
  2. On `architecture_bottleneck`: triggers Neural Architecture Search (NAS) via `triggerNAS`.
  3. Otherwise: generates a reform proposal via `proposeReform`.
- **Plan Assessment (`AssessPlan`)**:
  1. Static analysis for malicious patterns (`while true`, `fork bomb`, etc.) → immediate 1.0 risk score.
  2. Sandbox pre-flight via Gosh: executes the plan in isolation, scores based on failure.
  3. Risk > 0.7 → Kernel Ring-0 rejects the plan before execution.

---

## 4. Tool-Efficacy Daemon
**"The Toolmaster"** | `pkg/service/daemon.go` → `ToolDaemon`

- **Role**: Monitors tool usage correction events and triggers targeted tool-calling fine-tuning.
- **Trigger**: ≥ 10 new correction events in the corrections buffer AND cooldown elapsed.
- **Cycle**: Checks every 10 minutes.
- **Action**: Invokes `scripts/runpod_bridge.py --train-tool-bench` on a remote RunPod cluster (same hardware spec as JIT Daemon).

---

## 5. Curiosity Daemon
**"The Epistemic Forager"** | `pkg/service/curiosity_daemon.go` → `CuriosityDaemon`

- **Role**: Proactively fills gaps in Oricli's knowledge graph via autonomous web research. Zero compute cost during active use — forages only during idle periods, mirroring biological memory consolidation.
- **Architecture**: Two-phase idle-burst (refactored from always-on ticker in commit `124af08`).

### Phase 1 — Passive Seed Accumulation (always-on, zero cost)

Every user message is scanned by `SeedFromMessage(msg)` — pure regex, <1ms, no inference, never blocks a response. Three extraction patterns:

- **Question subjects**: entities after "what is", "who is", "how does", etc.
- **Named entities**: multi-word capitalized phrases (e.g. "Sovereign Engine")
- **CamelCase / acronyms**: technical identifiers (e.g. `WorkingMemoryGraph`, `LMDB`)

Seeds are deduplicated into a persistent `seenKeys` map (never cleared — prevents re-researching known topics in the same session). Seeds from PocketBase `knowledge_fragments` are pre-loaded at each burst start to skip topics researched in prior sessions.

`NotifyActivity()` is called on every chat request to record the last active timestamp (atomic int64 UnixNano).

### Phase 2 — Idle-Burst Research (idle-only, interruptible)

A 60-second ticker checks whether the system has been idle for longer than `CURIOSITY_IDLE_MIN` (default: **20 minutes**). When the threshold is met:

1. **Pre-load**: Load known topics from PocketBase `knowledge_fragments` → add to `seenKeys` (skip already-researched)
2. **Phase A** — Seed queue: burn through conversation-derived seeds (high signal — directly relevant to what the user cares about)
3. **Phase B** — Graph gaps: score all `WorkingMemoryGraph` nodes by `Importance × Uncertainty`, forage highest-priority gaps

Any new chat request interrupts the burst immediately via a non-blocking channel signal. The daemon stops after the current `forageTopic()` call finishes — never mid-write.

```
Idle threshold reached
       │
       ▼
Pre-load known PB topics → mark as seenKeys
       │
       ▼
Phase A: Pop seeds from queue → forageTopic() × N
       │    (interrupt check on every iteration)
       ▼
Phase B: Graph gaps sorted by Importance×Uncertainty → forageTopic() × M
       │    (3s pause between gap fills, interrupt check each)
       ▼
Log burst complete (count, elapsed)
```

### forageTopic() Pipeline

Each topic goes through the same search-extract-commit pipeline:

1. `ClassifySearchIntent(topic)` → intent type (8 types, <1ms)
2. `SearXNG SearchWithURLs()` → structured results with real URLs
3. `VDI.NavigateAndExtract()` on top-2 URLs (parallel, 5s timeout) → rich article text
4. Fallback: `SearXNG SearchWithIntent()` → snippets; then Colly DDG as last resort
5. Intent-tailored extraction prompt → `GenerationService.Generate()` (90s deadline, `ministral-3:3b`)
6. Commit 3–5 extracted facts to `WorkingMemoryGraph.UpdateEntity()`
7. **`MemoryBank.WriteKnowledgeFragment(topic, intent, factSummary, 0.7)`** — persists finding to PocketBase under Oricli's analyst account (author=oricli)

### Gap Prioritization

```
score = entity.Importance × entity.Uncertainty
```

Highest-scoring entity forages first — critical unknowns resolved before low-importance gaps.

### Structured Search Intent

| Intent | Signal | Query Strategy | SearXNG Category |
|---|---|---|---|
| `DEFINITION` | Single abstract noun, "what is", "meaning of" | `define {term}` | general |
| `FACTUAL` | "when did", "who is", "how many" | Direct question form | general |
| `ENTITY` | Proper noun (CamelCase / title-case), org/person | `{name} Wikipedia` | general |
| `TOPIC` | Multi-word concept, no question prefix | Multi-pass broad search | general |
| `TECHNICAL` | Code keyword, framework name, `v\d+` version | `{term} documentation` | it |
| `CURRENT_EVENTS` | "latest", "recent", "news", year mention | time_range=week | news |
| `COMPARATIVE` | "vs", "difference between", "compare" | Dual-source lookup | general |
| `PROCEDURAL` | "how to", "steps to", "guide for" | `how to {topic} guide` | general |

### PocketBase Persistence & Novelty Cap

After each `forageTopic()` commit, findings are written to PocketBase `knowledge_fragments` under Oricli's analyst account:

```go
MemoryBank.WriteKnowledgeFragment(topic, intent, factSummary, 0.7)
// → author: "oricli", provenance: "synthetic_l1", lineage_depth: 1
// → topic_volatility: inferred from topic keywords (stable|current|ephemeral)
```

On the next burst start, these are pre-loaded and marked as `seenKeys` — Oricli never re-researches a topic she already knows across sessions.

**Novelty cap — anti-echo-chamber guard:** Before any web search begins, `forageTopic()` checks `MemoryBank.KnowledgeCount(ctx, topic)`. If the topic already has **≥3 knowledge fragments** stored in PocketBase, the forage is skipped entirely. This prevents Oricli from deepening synthetic knowledge wells about the same topics instead of exploring genuinely new territory. The cap is enforced across sessions.

```
forageTopic("quantum computing")
    KnowledgeCount("quantum computing") → 3
    → SKIP — novelty cap reached, pick next seed
```

→ Full rationale: **`docs/EPISTEMIC_HYGIENE.md`**

**Supporting service:** `SearXNGSearcher` (`pkg/service/searxng_searcher.go`). Health-checks `127.0.0.1:8080/healthz` with 30s TTL cache. SearXNG runs as `oricli-searxng` Docker container.

**WebSocket events:** `curiosity_sync { target_entity, action, findings, intent }`, `session_start`, `session_complete`

---

## 5.1 Inline Search — ConfidenceDetector
**"The Reflexive Lookup"** | `pkg/cognition/confidence.go` → `DetectUncertainty()`

Unlike the CuriosityDaemon (which forages during idle periods), the ConfidenceDetector fires **synchronously during live chat inference** — before Ollama is ever called.

- **Trigger**: A user prompt that contains knowledge-seeking signals ("what is", "what does", "who is", "when did", "how to", "explain", "define", etc.) with an extractable topic.
- **Speed**: Pure regex/keyword — zero LLM calls, <1ms. Never slows inference.
- **Exclusions**: Conversational messages, short greetings, and pure emotional/support prompts are fast-rejected by `isConversational()`.

### Pipeline position

```
USER MESSAGE
     │
     ▼
[Safety Pipeline — 8 gates]
     │
     ▼
[ConfidenceDetector]         ← fires here — classifies intent from FULL prompt
     │  if factual/entity/definition/technical/procedural need detected:
     ▼
[SearXNG SearchWithIntent]   ← fetches grounded web context (≤1200 chars)
     │
     ▼
[ProcessInference composite] ← context injected as ### WEB CONTEXT [...] block
     │
     ▼
[Ollama generation]          ← LLM now has real facts to draw from
```

### Intent classification

The intent is classified from the **original user prompt** (not the extracted topic), ensuring "how to set up nginx?" correctly maps to `PROCEDURAL` even though the extracted topic is "set up nginx".

### Context injection

Injected context is capped at **1200 chars** to avoid prompt bloat:

```
### WEB CONTEXT [TECHNICAL — "nginx reverse proxy"]
<snippet from SearXNG result>
### END WEB CONTEXT
```

This block is appended to the composite prompt before the SCAI constitution, then normal inference proceeds.

---

## 6. Reform Daemon
**"The Self-Modifier"** | `pkg/service/reform_daemon.go` → `ReformDaemon`

- **Role**: Continuously audits execution traces for performance bottlenecks and autonomously proposes — and for non-sensitive paths, deploys — code refactors through a multi-stage Code Constitution pipeline.
- **Trigger**: Scheduled tick every **10 minutes**.

### Code Constitution

Before any code is generated, the **Code Constitution** (`pkg/reform/constitution.go`) is injected as the LLM system prompt. It mirrors the `pkg/safety/constitution.go` pattern but enforces engineering mandates instead of safety principles:

| Principle | Mandate |
|---|---|
| **Complete Implementation Only** | No TODO, FIXME, stubs, `panic("not implemented")`, or empty function bodies |
| **Surgical Scope** | Only modify the specific function causing the traced bottleneck |
| **Compile-Clean Standard** | All imports used, no type mismatches, `go fmt` and `go vet` clean |
| **Perimeter Sovereignty** | No new external dependencies, no unauthorized network egress |
| **Safety Inviolability** | `pkg/safety/`, `pkg/sovereign/`, `pkg/kernel/` are read-only — hardcoded, always |
| **Benchmark Justification** | Proposal must include a concrete improvement claim in a comment |
| **Idiomatic Go** | Follows codebase style — explicit error returns, no goroutine leaks |

### 4-Stage Code Verifier

After generation, `CodeVerifier.Verify()` (`pkg/reform/verifier.go`) runs before the build system is touched:

1. **Forbidden pattern scan** — regex blocks `TODO/FIXME/HACK/XXX`, `panic("not implemented")`, empty function bodies, lone blank identifier stubs
2. **`gofmt -l`** — proposal must already be formatted
3. **`go vet`** — semantic checks in isolated temp dir
4. **`go build`** — full compile in isolated temp module with minimal `go.mod`

Any failure at any stage rejects the proposal. The rejection reason is logged and broadcast.

### Auto-Deploy Pipeline

```
TraceStore.FindBottlenecks()
→ GenerateReform()   [Code Constitution injected as system prompt]
→ CodeVerifier.Verify()   [4-stage gate — REJECT on any failure]
→ IsSensitive check   [kernel/safety/sovereign → propose-only, NEVER deploy]
→ go test ./pkg/...   [REJECT on any regression]
→ go build -o bin/oricli-go-v2.candidate ./cmd/backbone/
→ atomic rename candidate → bin/oricli-go-v2
→ systemctl restart oricli-backbone
→ 60s rollback watchdog   [restore backup binary if service not active]
```

- **`deployGate` constant**: set to `true` to enable auto-deploy. `false` reverts to propose-only globally.
- **Rollback**: if the service is not `active` 60 seconds after restart, the previous binary and source file are atomically restored and the service is restarted again. A `reform_rollback` WS event fires.

**WebSocket events:** `reform_proposal { file, old_code, new_code, benefit, benchmark_result, is_sensitive, auto_deployed }`, `reform_rollback { file, reason }`

---

## 6.1 DAG Goal Executor
**"The Autonomous Planner"** | `pkg/service/goal_executor.go` → `GoalExecutor`

- **Role**: Persistent execution loop for sovereign DAG objectives. Polls `GoalService` for pending objectives whose dependencies are resolved and dispatches them to `ActionRouter`.
- **Trigger**: Polls every **30 seconds**.
- **Restart Safety**: On backbone boot, any objective stuck in `active` (interrupted mid-execution) is automatically rehydrated to `pending` for re-queuing.
- **DAG Model**: Each `Objective` has `DependsOn []string` — a list of IDs that must reach `completed` status before this objective is eligible to run. `IsReady(all []Objective)` evaluates the dependency graph at dispatch time.
- **Dispatch**: Synthesizes a `DetectedAction` (defaults to `ActionResearch`) from the objective goal text and fires it into the `ActionRouter`. An `awaitCompletion` goroutine polls job status and updates the objective to `completed` or `failed`.
- **API**: `GET/POST/PUT/DELETE /v1/goals` — full CRUD for sovereign objectives.

---

## 7. Autonomic Scaling Service
**"The Growth Daemon"** | `pkg/kernel/scaling.go` → `ScalingService`

- **Role**: Monitors Swarm Bus latency in real-time and autonomously provisions additional GPU compute when the system is under pressure.
- **Trigger**: Swarm Bus average latency exceeds **500ms**, checked every 10 seconds.
- **Action**:
  1. Issues a `SysAllocGPU` syscall directly to Kernel Ring-0 (bypasses normal swarm routing).
  2. Requests NVIDIA RTX 5090 × 1 from the GhostCluster via RunPod.
  3. New worker node joins the swarm automatically.
- **Shutdown**: Responds to `stopCh` signal for clean shutdown with the rest of the backbone.

---

## Daemon Boot Sequence

All daemons start at backbone boot as goroutines. None block the primary inference path.

```
main.go boot
├── ReformDaemon.Run(ctx)          → goroutine (Code Constitution pipeline active)
├── CuriosityDaemon.Run(ctx)       → goroutine (VDI deep-forage enabled)
├── ScalingService.Run()           → goroutine
├── DreamDaemon.Run()              → goroutine
├── MetacogDaemon.Run()            → goroutine (via GoOrchestrator)
├── GoalExecutor.Start(ctx)        → goroutine (DAG autonomous execution)
├── JITDaemon.Run()                → goroutine  [not yet wired in main.go — pending]
├── ToolDaemon.Run()               → goroutine  [not yet wired in main.go — pending]
└── MCP.StartAll()                 → goroutine (per-server, 2-min timeout each)
```

---

## Infrastructure Notes

- All daemons communicate via **Swarm Bus pub/sub** — no direct function calls into the inference pipeline.
- Daemons with WebSocket hubs (`CuriosityDaemon`, `ReformDaemon`) receive the hub reference via `InjectWSHub()` after the API server starts.
- `GhostClusterService` (used by Dream Daemon and ScalingService) requires `RUNPOD_API_KEY` in the environment. If the key is absent, provisioning calls fail gracefully and are logged without crashing the daemon.
