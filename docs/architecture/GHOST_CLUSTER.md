# Ghost Cluster: Ephemeral GPU Orchestration

**Document Type:** Technical Reference  
**Version:** v2.1.0  
**Status:** Active  

---

## 1. Overview

The **Ghost Cluster** is Oricli-Alpha's autonomous compute provisioning layer. It orchestrates temporary GPU clusters on RunPod for training and consolidation workloads, then destroys them the moment the work is done — leaving no idle billing, no persistent attack surface, and no cloud footprint.

**"Provision → Use → Vanish."**

---

## 2. Why Ephemeral Clusters

Persistent GPU instances are expensive and idle most of the time. Oricli's training workloads (JIT LoRA absorption, Dream consolidation, Tool-Efficacy fine-tuning) are burst events — intense for minutes to hours, then unnecessary. Ghost Cluster provisions exactly the hardware needed, runs the job, and terminates immediately.

RunPod's native Cluster API is unstable. The Ghost Cluster implements its own async orchestration — multiple independent pods launched in parallel goroutines, coordinated by the `GhostClusterService`.

---

## 3. Architecture

**Implementation:** `pkg/service/ghost_cluster.go` → `GhostClusterService`  
**Connector:** `pkg/connectors/runpod` → `runpod.Client`  
**Required env:** `RUNPOD_API_KEY`

```
GhostClusterService
├── RunPodClient          → REST API client for RunPod
├── ActivePods            → map[podID]*Pod (thread-safe via sync.Mutex)
└── Provision / Vanish    → goroutine-per-pod lifecycle management
```

### GhostSession

A `GhostSession` represents a single cluster allocation:

```go
type GhostSession struct {
    PodIDs    []string   // All pod IDs in this session
    GPUType   string     // e.g. "NVIDIA RTX 5090"
    StartTime time.Time
}
```

---

## 4. Lifecycle

### 4.1 Provision

```go
session, err := ghost.Provision(ctx, "dream-consolidation", "NVIDIA RTX 5090", 2)
```

1. Launches `count` goroutines simultaneously — one pod per goroutine.
2. Each goroutine calls `RunPodClient.CreatePod(name, gpuType, image)` with the standard PyTorch image (`runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04`).
3. Successful pod IDs are appended to `session.PodIDs` thread-safely.
4. If any pod fails to create, `Vanish()` is called immediately on all successfully created pods before returning the error. No orphaned hardware.

### 4.2 Vanish

```go
ghost.Vanish(session)
```

1. Launches one goroutine per pod ID simultaneously.
2. Each goroutine calls `RunPodClient.TerminatePod(id)`.
3. On success: pod is removed from `ActivePods`.
4. On failure: logs the error but does not block other terminations.
5. Blocks until all goroutines complete (`wg.Wait()`).

**`defer ghost.Vanish(session)` is the standard usage pattern** — ensures hardware is always reclaimed even if the training step panics.

---

## 5. Current Callers

| Caller | Session Name | Hardware | Count |
|---|---|---|---|
| `DreamDaemon.ConsolidateExperience()` | `dream-consolidation` | NVIDIA RTX 5090 | 1 |
| `ScalingService.TriggerScaleOut()` | via Kernel `SysAllocGPU` syscall | NVIDIA RTX 5090 | 1 |
| `JITDaemon.triggerTraining()` | via `runpod_bridge.py --cluster-size 2` | ≥ 40GB VRAM | 2 |
| `ToolDaemon.triggerTraining()` | via `runpod_bridge.py --cluster-size 2` | ≥ 40GB VRAM | 2 |

Note: JIT and Tool daemons invoke `runpod_bridge.py` directly (Python bridge script with its own RunPod logic), while Dream and Scaling use `GhostClusterService` natively.

---

## 6. S3 Hybrid Strategy

Training jobs launched via `runpod_bridge.py` use an **S3 Hybrid Strategy** for data transport:

- **Local NVMe**: Hot data (recent RFAL lessons, active adapter weights) staged locally for speed.
- **S3**: Persistent state (trained adapter checkpoints, lesson archives) synced after each job.

The bridge passes `--upload-to-s3` to ensure all results are persisted before the pod terminates.

---

## 7. Failure Modes

| Failure | Behavior |
|---|---|
| `RUNPOD_API_KEY` missing/invalid | `CreatePod` returns error → `Provision` fails → daemon logs warning, skips cycle |
| Pod creation timeout | Goroutine returns error → partial rollback via `Vanish` |
| Training job failure | Logged by daemon; `Vanish` still called via `defer` |
| `TerminatePod` failure | Logged; other pods still terminated; **manual cleanup may be required** |

---

## 8. Adding New Workloads

To dispatch a new training job via Ghost Cluster:

```go
session, err := sovEngine.Ghost.Provision(ctx, "my-job-name", "NVIDIA RTX 5090", 1)
if err != nil {
    log.Printf("[MyDaemon] Provisioning failed: %v", err)
    return
}
defer sovEngine.Ghost.Vanish(session)

// ... do training work, interact with pod via SSH or HTTP ...

log.Println("[MyDaemon] Job complete.")
// Vanish() fires here automatically
```
