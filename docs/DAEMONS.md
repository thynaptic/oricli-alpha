# Oricli-Alpha Autonomous Daemons

**Document Type:** Technical Reference  
**Version:** v2.2.0  
**Status:** Active  

Oricli-Alpha maintains seven background daemons that run as goroutines within the Go-native backbone (`pkg/service/daemon.go`, `curiosity_daemon.go`, `reform_daemon.go`, `pkg/kernel/scaling.go`). They are started at boot and communicate with the system exclusively through the Swarm Bus — zero polling overhead on the main inference path.

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
- **Forage Priority Chain**:
  1. **SearXNG** (primary) — queries the local sovereign SearXNG Docker instance (`127.0.0.1:8080`). Aggregates Google, Bing, DuckDuckGo, and Wikipedia in one shot; returns clean JSON with titles, URLs, and snippets. No bot detection issues.
  2. **Colly page fetcher** — follows the top URLs from SearXNG results to extract full body text from each page. This layer was always reliable; only the search-page step was blocked.
  3. **VDI / chromedp** (secondary) — headless browser session; used if SearXNG is unavailable and `Chromium` is installed on the host.
  4. **CollySearcher DDG** (last resort) — Colly directly scrapes DDG Lite; prone to bot-detection blocks on VPS.
- **Supporting service**: `SearXNGSearcher` (`pkg/service/searxng_searcher.go`) wraps the SearXNG REST API. `IsAvailable()` health-checks `127.0.0.1:8080/healthz` before each forage. SearXNG runs as `oricli-searxng` Docker container, managed by `oricli-searxng.service` (systemd).
- **Forage outcome**: Extracted text is distilled into 3–5 facts by the generation service and written back to the WorkingMemoryGraph node.
- **WebSocket events**: `curiosity_sync { target_entity, action, findings }`

---

## 6. Reform Daemon
**"The Self-Modifier"** | `pkg/service/reform_daemon.go` → `ReformDaemon`

- **Role**: Continuously audits execution traces for performance bottlenecks and drafts autonomous code refactors to fix them.
- **Trigger**: Scheduled tick every **10 minutes**.
- **Audit Cycle**:
  1. Calls `TraceStore.FindBottlenecks(2s latency threshold, 0.7 confidence floor)`.
  2. For each bottleneck trace, generates a reform proposal via `GenerateReform` — uses the generation service to produce a Go code diff targeting the problematic file.
  3. Broadcasts `reform_proposal` event to the WebSocket hub for operator review.
- **Output**: Reform proposals are surfaced to the UI, not auto-applied. The operator approves before a patch is merged.
- **WebSocket events**: `reform_proposal { file, original, proposed, rationale }`

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

All seven daemons start at backbone boot as goroutines. MCP init is also async. None of them block the primary inference path.

```
main.go boot
├── ReformDaemon.Run(ctx)         → goroutine
├── CuriosityDaemon.Run(ctx)      → goroutine
├── ScalingService.Run()          → goroutine
├── DreamDaemon.Run()             → goroutine
├── MetacogDaemon.Run()           → goroutine (via GoOrchestrator)
├── JITDaemon.Run()               → goroutine  [not yet wired in main.go — pending]
├── ToolDaemon.Run()              → goroutine  [not yet wired in main.go — pending]
└── MCP.StartAll()                → goroutine (per-server, 2-min timeout each)
```

---

## Infrastructure Notes

- All daemons communicate via **Swarm Bus pub/sub** — no direct function calls into the inference pipeline.
- Daemons with WebSocket hubs (`CuriosityDaemon`, `ReformDaemon`) receive the hub reference via `InjectWSHub()` after the API server starts.
- `GhostClusterService` (used by Dream Daemon and ScalingService) requires `RUNPOD_API_KEY` in the environment. If the key is absent, provisioning calls fail gracefully and are logged without crashing the daemon.
