# Oricli-Alpha Hive OS: Kernel Handbook (v2.1.0)

**Document Type:** API Reference & System Architecture Manual  
**Report Number:** TR-2026-04  
**Date:** 2026-03-20  
**Status:** Active Doctrine  
**Style Mode:** Hard Technical Doctrine  

---

## 1. Abstract

Oricli-Alpha is a compiled, high-performance, Go-native Operating System designed for autonomous agent orchestration. This handbook defines the programmatic interface for interacting with the Ring-0 Micro-Kernel, the Sovereign Engine, and the Distributed Swarm Bus. Developers and integrated LLM agents must utilize formal Syscalls and the Contract Net Protocol (CNP) to access hardware resources, memory graphs, and task allocation marketplaces.

---

## 2. System Architecture

The Hive OS operates through concentric rings of trust, isolating high-intensity neural compute from the deterministic core logic.

### Ring 0: The Micro-Kernel
The Micro-Kernel serves as the master arbiter for the system. It manages process lifecycles (AgentProcess), enforces financial hard-caps via the Safety Framework, and schedules tasks through the Precog Scheduler to prevent denial-of-service loops.

### Ring 1: The Sovereign Engine
The Sovereign Engine manages affective homeostasis and executive strategy. It unifies the Resonance Layer (ERI/ERS calculation), the Sweetheart Core (Personality Calibration), and the Long-Horizon Planner (Strategic DAGs). It provides the "modulated instruction trace" that shapes all downstream inference.

### Ring 2: The Substrate & Capability Layer
Manages the system's relationship with its substrate and external capabilities.
*   **Substrate Awareness**: Automatically detects hardware constraints (CPU/RAM) and scales reasoning tiers accordingly.
*   **MCP Integration**: Manages external Model Context Protocol servers, autonomously bridging their tools into the native toolbox.
*   **Sovereign Scheduler**: Native Ring-0 cron for temporal intents and task re-injection.
*   **FS Indexer**: Proactive substrate mapping, translating the local filesystem into COGS entities.
*   **Visual VDI**: Model-in-the-loop computer use, providing coordinate-based interaction via Qwen2.5-VL. 🦾🚀🏁

### Ring 3: The Hive Swarm (Swarm Bus)
A high-speed pub/sub nervous system routing messages between 269+ micro-agents. It utilizes the Contract Net Protocol for dynamic task bidding and uses Gosh Traces for verifiable execution.

### The HAL (Hardware Abstraction Layer)
Manages autonomic provisioning of "Ghost Clusters" (RunPod GPU instances). The HAL ensures compute economy by spinning up high-VRAM pods only for specific neural tasks and terminating them instantly upon completion.

---

## 3. The Gosh Sandbox Environment

All agent processes are executed within a Gosh (Go-Shell) Sandbox.
*   **Virtualization**: An in-memory, virtualized bash environment parsed natively in Go.
*   **FS Isolation**: Agents have read-only access to host project files. All write operations are captured in an isolated overlay memory layer.
*   **Sovereign Tooling**: Custom Go functions can be registered via the Yaegi interpreter and invoked directly within Gosh scripts.

---

## 4. Programmatic Syscall API

Inter-process communication and resource requests must be formatted as a `SyscallRequest` and routed through the Kernel.

### Request Format (Go)
```go
type SyscallRequest struct {
	PID      string                 // Process Identifier
	Call     kernel.SyscallType     // Requested Operation
	Args     map[string]interface{} // Parameter Payload
	FeeOffer float64                // Priority Bribe (MetacogTokens)
}
```

### Supported Syscalls

| Syscall | Description | Parameters |
|:---|:---|:---|
| `SysAllocGPU` | Requests an ephemeral Ghost Cluster. | `gpu_type` (string), `count` (int) |
| `SysQueryMemory` | Greps the chronologically-indexed LMDB graph. | `query` (string), `mode` (RecallMode) |
| `SysAllocSharedMem` | Allocates zero-copy Ring-0 RAM for IPC. | `name` (string), `size` (int) |
| `SysWriteSharedMem` | Flushes sandbox files to shared memory. | `name` (string), `path` (string) |
| `SysMapSharedMem` | Mounts shared memory into local sandbox. | `name` (string), `path` (string) |
| `SysPanic` | Drops system to DEFCON 1 and locks Kernel. | None |

---

## 5. Swarm Economy & Task Allocation

Tasks are distributed via a decentralized marketplace on the Swarm Bus.

1.  **Call for Proposals (CFP)**: The Agent Coordinator broadcasts a task payload and bounty.
2.  **Pre-flight Verification**: Agents must run the task in their local Gosh sandbox to generate a success trace (GoshTrace).
3.  **Bidding**: Agents submit an `AgentBid` containing confidence scores, token risk, and the GoshTrace.
4.  **Consensus & Payout**: The Kernel selects the optimal bid based on historical efficacy and transfers the bounty upon verified execution.

---

## 6. Homeostasis & Affective Regulation

The system maintains stability through continuous feedback loops.

*   **Ecospheric Resonance Index (ERI)**: A metric of swarm health derived from pacing stability, latency variance, and message coherence.
*   **Musical Mapping**: The system maps its internal state to musical keys (e.g., E Major, G Minor) to provide high-level diagnostic signals.
*   **Metacognitive Sentinel**: Monitors for cognitive loops or "scattered" thinking, triggering "Wise Mind" resets and "Radical Acceptance" field decays when discord is detected.

---

## 7. Safety Protocols (DEFCON)

The Safety Framework enforces global resource and security policies.

| Level | State | Constraints |
|:---|:---|:---|
| **DEFCON 5** | Normal | Full autonomic scaling and swarm activity. |
| **DEFCON 4** | Restricted | Auto-scaling disabled. Max 10 active PIDs. |
| **DEFCON 3** | Shielded | No new GPU allocations. Max 5 PIDs. |
| **DEFCON 2** | Quarantine | All agents suspended. Syscalls disabled. |
| **DEFCON 1** | Panic | Kernel locked. Global shutdown initiated. |

---

## 8. Developer Implementation Guidelines

*   **Go-Native Mandate**: All core logic must be implemented in Go. Python is reserved for non-critical sidecar wrappers.
*   **Deterministic State**: Do not rely on prompt-engineering for core logic. Use state machines and compiled heuristics.
*   **Efficiency Requirement**: Rapid syscall polling will be flagged as a DoS threat by the Precog Scheduler and may result in process termination (SIGKILL).
*   **Validation**: Every destructive operation must be preceded by a verified Gosh sandbox run.

**Ring 0 Integrity Confirmed.**
