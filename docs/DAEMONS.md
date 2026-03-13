# Oricli-Alpha Autonomous Daemons

Oricli-Alpha uses a set of background **Daemons** to maintain cognitive health, absorb knowledge, and improve tool efficacy asynchronously. These daemons run independently of the main interaction loop.

## 1. JIT Knowledge Daemon (`oricli_jit_daemon.py`)
**"The Librarian"**

*   **Role**: Monitors verified facts and triggers "Just-In-Time" (JIT) absorption into the model weights via LoRA.
*   **Trigger**: Watches `oricli_core/data/jit_absorption.jsonl`.
*   **Threshold**: Activates after **5** new verified facts.
*   **Action**: Triggers a remote RunPod cluster (2-node Blackwell or similar) to fine-tune a JIT adapter.
*   **Cooldown**: 2 hours.

## 2. Dream Daemon (`oricli_dream_daemon.py`)
**"The Subconscious Consolidator"**

*   **Role**: Runs during idle periods to consolidate memories and generate novel insights.
*   **Trigger**: System idle for >30 minutes.
*   **Action**:
    1.  Samples disparte facts from `jit_absorption.jsonl` and the Memory Graph.
    2.  Uses `cognitive_generator` and `insight_service` to find analogical connections.
    3.  Persists valid insights back to the Memory Graph.
*   **Cycle**: Runs every 5 minutes while idle.

## 3. Metacognition Daemon (`oricli_metacognition_daemon.py`)
**"The Self-Improver"**

*   **Role**: Autonomic self-modification. Monitors execution traces for inefficiencies and proposes architectural changes.
*   **Trigger**: Hourly scan (3600s).
*   **Action**:
    1.  Analyzes `cognitive_trace_diagnostics` for errors, latency, or loops.
    2.  Uses `python_codebase_search` and `python_refactoring_reasoning` to propose patches.
    3.  Can trigger **Neural Architecture Search (NAS)** to optimize module structures.

## 4. Tool-Efficacy Daemon (`oricli_tool_daemon.py`)
**"The Toolmaster"**

*   **Role**: Monitors tool usage failures and corrections to improve tool-calling reliability.
*   **Trigger**: Watches `oricli_core/data/tool_corrections.jsonl`.
*   **Threshold**: Activates after **10** corrections.
*   **Action**: Triggers a remote RunPod cluster to train a specific `tool_efficacy` adapter.
*   **Cooldown**: 4 hours.

---

## Infrastructure
All daemons are typically managed via systemd (e.g., `oricli-jit.service`) or the master script `scripts/start_servers.sh`. They log to `*.log` files in the repo root.
