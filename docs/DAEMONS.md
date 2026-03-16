# Oricli-Alpha Autonomous Daemons

Oricli-Alpha uses a set of background **Daemons** to maintain cognitive health, absorb knowledge, and improve tool efficacy asynchronously. With Phase 1 of the Go migration complete, these daemons are now orchestrated by the **Go-Native Backbone** (`pkg/service/daemon.go`).

## 1. JIT Knowledge Daemon (Go-Orchestrated)
**"The Librarian"**

*   **Role**: Monitors verified facts and triggers "Just-In-Time" (JIT) absorption.
*   **Implementation**: Native Go service (`pkg/service/absorption.go`) monitoring `oricli_core/data/jit_absorption.jsonl`.
*   **Threshold**: Activates after **5** new verified facts.
*   **Action**: Orchestrates remote RunPod clusters to fine-tune JIT adapters.

## 2. Dream Daemon (Go-Orchestrated)
**"The Subconscious Consolidator"**

*   **Role**: Runs during idle periods to consolidate memories and generate novel insights.
*   **Implementation**: Integrated into the Go sidecar mesh.
*   **Trigger**: System idle for >30 minutes (monitored by Go Swarm Bus activity).
*   **Action**: 
    1.  Samples facts from the Memory Bridge (LMDB).
    2.  Coordinates with Python sidecars for analogical reasoning.
    3.  Persists insights back to the Neo4j Knowledge Graph via Go native drivers.

## 3. Metacognition Daemon (Go-Orchestrated)
**"The Self-Improver"**

*   **Role**: Autonomic self-modification. Monitors execution traces for inefficiencies.
*   **Implementation**: Go Monitor Service (`pkg/service/monitor.go`).
*   **Trigger**: Real-time heartbeat and trace analysis.
*   **Action**: Identifies latency bottlenecks or loops across the Swarm and proposes re-routing or scaling.

## 4. Tool-Efficacy Daemon (Go-Orchestrated)
**"The Toolmaster"**

*   **Role**: Monitors tool usage failures and corrections.
*   **Implementation**: Native Go Tool service (`pkg/service/tool.go`).
*   **Threshold**: Activates after **10** corrections.
*   **Action**: Triggers fine-tuning cycles for tool-calling reliability.

---

## Infrastructure
Daemons are now internal Goroutines within the `oricli-go` backbone. They are managed as part of the primary system process, ensuring high availability and zero-overhead communication with the Swarm Bus.
