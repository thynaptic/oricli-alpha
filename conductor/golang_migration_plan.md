# GoLang Migration Plan: Swarm Bus & Connective Tissue

## Objective
Migrate Oricli-Alpha's high-frequency connective tissue—specifically the `SwarmBus`, `HiveNode`, and Contract Net `Orchestrator`—from Python to Go. This will eliminate GIL contention, resolve the 752% CPU "thundering herd" bottleneck on Hostinger, and prepare the Hive for massive parallel scaling.

## Background & Motivation
The current implementation in `oricli_core/brain/swarm_bus.py` uses synchronous loops wrapped in a `threading.Lock`. When the Broker broadcasts a `CFP` (Call for Proposals), all 269+ Python micro-agents try to respond simultaneously, triggering a massive GIL context-switching spiral. By moving the routing, bidding, and pub/sub bus to Go, we leverage lightweight Goroutines and Channels, reducing overhead to near-zero. 

The heavy AI computation (250k lines of logic) will remain in Python.

## Scope & Impact
- **Go Components (New):**
  - **Go Swarm Bus:** High-throughput pub/sub engine using Channels.
  - **Go Orchestrator/Broker:** Handles the CFP/Bidding/Acceptance lifecycle.
  - **Go Hive Node (Sidecar):** Acts as the agent on the bus, calculating bids and routing accepted tasks to the Python worker.
- **Python Components (Retained but Refactored):**
  - **Brain Modules:** Untouched.
  - **Python gRPC Worker:** A new lightweight wrapper that loads the modules and listens for execution requests from the Go Sidecar.

## Proposed Architecture (The Sidecar Mesh)
1. **gRPC / UDS Bridge:** Communication between the Go Sidecar and the Python Brain Module will happen via high-speed Unix Domain Sockets (UDS) using gRPC.
2. **Go Backbone:** A standalone Go binary will boot up, spawn the internal Pub/Sub bus, and spin up a Goroutine for each module.
3. **Python Worker Pool:** Instead of 269 active threads, Python will run a pool of gRPC workers that load the initialized modules and wait passively for `Execute` commands.

## Implementation Steps

### Phase 1: Bridge Contract (Protobuf)
Define a strict gRPC schema (`oricli_rpc.proto`) that handles module discovery and execution.
- `GetManifest`: Go asks Python what modules/operations are available.
- `ExecuteOperation`: Go sends task parameters to Python and awaits the result.
- `HealthCheck`: Go monitors the Python worker.

### Phase 2: Python Worker Substrate
- Create `oricli_core/brain/grpc_server.py`.
- Refactor `ModuleRegistry` to emit a static JSON manifest on boot (so Go knows what modules exist without booting Python).
- Create a Python gRPC server that wraps `BaseBrainModule.execute()`.

### Phase 3: Go Backbone Development
- Scaffold the Go project (`oricli-go`).
- Implement the `SwarmBus` using Go Channels.
- Port the `AgentProfileService` to Go to allow microsecond-level policy enforcement during bidding.
- Implement the Broker logic (CFP, Arbitration, Result tracking).

### Phase 4: Go Sidecar & Integration
- Implement the `GoHiveNode` struct that listens on the Go SwarmBus.
- Connect the `GoHiveNode` to the Python gRPC Worker via a client.
- Integrate the startup scripts to launch both the Python gRPC pool and the Go Backbone side-by-side.

### Phase 5: Load Testing & Verification
- Perform a stress test matching the Hostinger environment (269+ modules).
- Monitor CPU utilization, expecting a drop from 750% to < 50% during idle/bidding phases.
- Verify that standard tasks (e.g., memory search, code generation) complete successfully through the bridge.

## Migration & Rollback Strategy
- **Feature Flag:** The migration will be hidden behind a `.env` flag (e.g., `ORICLI_BACKBONE=go`).
- **Parallel Codebase:** The original Python `swarm_bus.py` will be kept intact during the transition. If the Go bridge fails, the system can instantly fallback to the pure-Python implementation by unsetting the flag.
