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

- **Role**: Proactively identifies gaps in Oricli's knowledge graph and fills them via autonomous web research — no user prompt required.
- **Trigger**: Scheduled tick every **15 minutes** (context-aware: only forages when no active inference is running).

### Gap Prioritization

Gaps are no longer selected arbitrarily. The daemon scores every knowledge gap by:

```
score = entity.Importance × entity.Uncertainty
```

The highest-scoring entity is selected for foraging first — ensuring the most critical unknowns are resolved before low-importance gaps.

### Structured Search Intent

Before querying, the daemon classifies the knowledge gap into one of **8 intent types** using `ClassifySearchIntent()` (pure heuristic, <1ms):

| Intent | Signal | Query Strategy | SearXNG Category |
|---|---|---|---|
| `DEFINITION` | Single abstract noun, "what is", "meaning of" | `define {term}` | general |
| `FACTUAL` | "when did", "who is", "how many", specific question | Direct question form | general |
| `ENTITY` | Proper noun (CamelCase / title-case), org/person name | `{name} Wikipedia` | general |
| `TOPIC` | Multi-word concept, no question prefix | Multi-pass broad search | general |
| `TECHNICAL` | Code keyword, framework name, `v\d+` version | `{term} documentation` | it |
| `CURRENT_EVENTS` | "latest", "recent", "news", year mention | time_range=week | news |
| `COMPARATIVE` | "vs", "difference between", "compare" | Dual-source lookup | general |
| `PROCEDURAL` | "how to", "steps to", "guide for" | `how to {topic} guide` | general |

Each intent maps to tailored SearXNG parameters (`categories`, `time_range`) and source hints (Wikipedia for definitions/facts, official docs/GitHub/StackOverflow for technical).

### Intent-Tailored Extraction Prompts

After fetching raw content, the distillation prompt is customized per intent:

- **DEFINITION** → asks for etymology, core meaning, usage examples
- **FACTUAL** → asks for dates, numbers, named entities, verifiable facts
- **ENTITY** → asks for origin, what it does, why it matters
- **TECHNICAL** → asks for API surface, typical use case, version notes
- **PROCEDURAL** → asks for numbered steps with prerequisites
- **CURRENT_EVENTS** → asks for key parties, timeline, current status

### Search Stack

1. **SearXNG `SearchWithURLs()`** (primary) — returns structured `[]WebSearchResult` with real article URLs, titles, and snippets. Intent-aware categories + time_range applied. Source-hinted results (e.g. `wikipedia.org` for DEFINITION) are front-promoted.
2. **VDI Deep-Forage** (parallel, primary tier 2) — takes top-2 URLs from SearXNG, fires `VDI.NavigateAndExtract()` in parallel goroutines (5-second timeout each). Navigates actual article pages, applies semantic content selector fallback chain (`article` → `main` → `[role=main]` → `.content` → `body`), strips nav/cookie/ad boilerplate, merges text up to 5000 chars. Yields far richer factual text than snippets alone.
3. **SearXNG `SearchWithIntent()`** (snippet fallback) — used if VDI is unavailable or returns empty. Colly page-fetcher follows top URLs for body text.
4. **CollySearcher DDG** (last resort) — Colly directly scrapes DDG Lite. Prone to bot-detection on VPS.

**Supporting service:** `SearXNGSearcher` (`pkg/service/searxng_searcher.go`). `IsAvailable()` health-checks `127.0.0.1:8080/healthz` before each forage with a 30-second cache TTL (no ping-per-inference). SearXNG runs as `oricli-searxng` Docker container, managed by `oricli-searxng.service`.

**Forage outcome:** Extracted text is distilled into 3–5 facts by the generation service and written back to the WorkingMemoryGraph node.

**WebSocket events:** `curiosity_sync { target_entity, action, findings, intent }`

---

## 5.1 Inline Search — ConfidenceDetector
**"The Reflexive Lookup"** | `pkg/cognition/confidence.go` → `DetectUncertainty()`

Unlike the CuriosityDaemon (which forages proactively on a 15-minute timer), the ConfidenceDetector fires **synchronously during live chat inference** — before Ollama is ever called.

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
