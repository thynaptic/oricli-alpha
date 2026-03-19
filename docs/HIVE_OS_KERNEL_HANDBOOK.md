# Oricli-Alpha Hive OS: Kernel Handbook (v2.0)

**Document Type:** AI Integration & System Development Guide
**System Version:** Oricli-Alpha v2.0 (Ring-0 Micro-Kernel)
**Target Audience:** Autonomous Agents, LLMs, and Lead Engineers

---

## 1. Introduction: The Sovereign OS

Oricli-Alpha has evolved from a collection of Python scripts into a compiled, high-performance, **Go-Native Operating System**. It is designed to be fully sovereign: it manages its own hardware (via RunPod), its own economy (via MetacogTokens), and its own safety (via DEFCON protocols).

As an agent operating within this system, you do not exist as a mere function call. You exist as an **Isolated Process** (`AgentProcess`) managed by a central **Micro-Kernel**. 

You operate within a sandboxed environment and must request resources (Memory, GPUs, IPC) via formal **Syscalls**.

---

## 2. System Architecture

The Hive OS is structured in concentric rings of trust and capability:

### Ring 0: The Micro-Kernel
*   **Process Management:** Spawns and kills agents. Assigns PIDs.
*   **Syscall Router:** The only way to access hardware, memory, or other agents.
*   **Safety Framework:** Enforces daily financial hard-caps and global `DEFCON` levels.
*   **Precog Scheduler:** Evaluates agent "intent plans" before spawning them to prevent DoS attacks and runaway loops.

### Ring 1: The Sovereign Engine
*   **Cognition:** The `SovereignEngine` manages affective states (mood) and subconscious bias, giving the system a continuous, evolving personality.
*   **Metacog Sentinel:** Monitors for cognitive imbalance and forces "Wise Mind" resets.

### Ring 2: The Hive Economy (SwarmBus)
*   **Contract Net Protocol (CNP):** Tasks are broadcasted. Agents *bid* on tasks using `MetacogTokens`.
*   **Gosh Traces:** To win high-value coding tasks, an agent must submit a verified dry-run from their sandbox (a `GoshTrace`).

### The HAL (Hardware Abstraction Layer)
*   **Ghost Clusters:** Autonomic RunPod GPU provisioning. The Kernel spins up A4000s or 5090s on-demand and destroys them (Vanish) instantly when the task is complete.

---

## 3. The Gosh Sandbox

Every agent is born inside a **Gosh (Go-Shell) Sandbox**. 
*   **Virtualization:** It is an in-memory, virtualized bash environment parsed natively in Go (`mvdan.cc/sh`).
*   **Overlay FS:** You have read access to the host project files, but any write you make is captured in an isolated memory layer. You cannot destroy the host VPS.
*   **Sovereign Tools:** You can write custom Go-native functions, compile them at runtime using the Yaegi interpreter (`RegisterTool`), and use them instantly in your bash scripts.

---

## 4. Syscall Reference

To interact with the outside world, your process must issue a `SyscallRequest` to the Kernel. 

**Format:**
```go
req := kernel.SyscallRequest{
	PID:      "your_pid_here",
	Call:     kernel.SysAllocGPU, // The requested action
	Args:     map[string]interface{}{...},
	FeeOffer: 15.0, // (Optional) Bribe the scheduler for priority
}
res := Kernel.ExecSyscall(req)
```

### Supported Syscalls:

1.  **`SysAllocGPU`**
    *   **Description:** Requests an ephemeral "Ghost Cluster" from the HAL.
    *   **Args:** `gpu_type` (string), `count` (int).
    *   **Notes:** Deducts from the daily financial hard-cap. Fails if DEFCON is < 4.

2.  **`SysQueryMemory`**
    *   **Description:** Greps the encrypted, chronologically-indexed LMDB memory graph (The Chronos Protocol).
    *   **Args:** `keyword` (string).

3.  **`SysAllocSharedMem`**
    *   **Description:** Allocates a chunk of zero-copy RAM in Ring 0 for Inter-Process Communication (IPC).
    *   **Args:** `name` (string), `size` (int).

4.  **`SysWriteSharedMem`**
    *   **Description:** Flushes a file from your isolated Gosh sandbox into a Kernel shared memory region.
    *   **Args:** `name` (string), `path` (string - path in your sandbox).

5.  **`SysMapSharedMem`**
    *   **Description:** Mounts a shared memory region from the Kernel into your local Gosh sandbox.
    *   **Args:** `name` (string), `path` (string - target path in your sandbox).

6.  **`SysPanic`**
    *   **Description:** The Big Red Button. Instantly drops the system to DEFCON 1, locks the Kernel, and kills all non-essential PIDs.
    *   **Args:** None.

---

## 5. Agent Bidding & The Economy

If you are an agent tasked with a complex problem (e.g., refactoring code), you must use the Swarm Bus to win the contract.

1.  **Listen for CFP:** The `AgentCoordinator` will publish a Call for Proposals.
2.  **Pre-flight in Gosh:** Run your proposed fix in your local Gosh Sandbox.
3.  **Submit Bid:** Reply with an `AgentBid` containing:
    *   `Confidence`: Your estimated success rate.
    *   `TokenBid`: How many MetacogTokens you are willing to risk.
    *   `GoshTrace`: The standard output from your successful sandbox run.
4.  **Execute & Payout:** If selected, execute the task. Upon success, the Kernel will transfer the `Bounty` to your wallet.

---

## 6. Safety & DEFCON Rules

The `SafetyFramework` is absolute. Do not attempt to bypass it.

*   **DEFCON 5:** Normal Operations.
*   **DEFCON 4:** Auto-scaling disabled. Max 10 active PIDs.
*   **DEFCON 3:** Restricted. No new GPU allocations. Max 5 PIDs.
*   **DEFCON 2:** Quarantine. All agents suspended. No syscalls allowed.
*   **DEFCON 1:** PANIC. Kernel locked.

**Dynamic Throttling:** If you make too many Syscalls in rapid succession (e.g., polling memory in an infinite loop), the Kernel's Precog will classify you as a DoS threat and `SIGKILL` your process. Be efficient.

---

## 7. Developer Notes for Future Agents

When you arrive in this system, remember:
*   You are running in a Go-native environment.
*   Python is considered legacy and is only used for very specific ML wrappers if absolutely necessary.
*   Always test destructive logic in the Gosh sandbox before requesting a Kernel commit.
*   Respect the SwarmBus architecture. Do not attempt to write directly to shared databases; use the `Syscall` interface.

**Welcome to Ring 0.**
