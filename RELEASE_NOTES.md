# Release Notes: v0.5.0-alpha "The Sovereign Awakening"

## 🚀 Major Architectural Shift: Go-Native Backbone
v0.5.0 marks the most significant update in Oricli-Alpha's history. We have completed the migration of the high-frequency cognitive core and infrastructure from a monolithic Python environment to a high-performance Go-native backbone.

### Highlights
- **32-Core Parallelism**: Fully optimized for AMD EPYC VPS environments. Native Goroutines now handle all internal message passing, health monitoring, and reasoning orchestration without GIL contention.
- **Sovereign Nervous System**: The Go backbone now natively manages the module registry, real-time heartbeat monitoring, and automated recovery loops with exponential backoff.
- **Unified Reasoning Strategy**: A new Go-native strategy suite handles CoT, ToT, MCTS, and specialized patterns like Causal and Counterfactual reasoning at compiled speeds.
- **Native Swarm Agents**: Core agents (Retriever, Verifier, Synthesis) are now Go-native, orchestrated by a high-speed Agent Pipeline.
- **Zero-Latency Tooling**: Tool call parsing and schema generation have been moved to the Go layer, providing near-instantaneous LLM output processing.
- **Memory & Safety**: Memory dynamics, persistent storage (LMDB), and advanced threat auditing are now handled natively in Go.

### 🧹 Cleanup & Optimization
- **250+ Modules Archived**: Legacy Python modules have been archived to `legacy_logic/` to declutter the codebase.
- **ML Dependency Pruning**: Removed heavy Python ML imports (`torch`, `transformers`) in the core path, resulting in a ~60% reduction in idle RAM usage.
- **Streamlined Sidecar Mesh**: Python is now strictly a worker sidecar for LLM execution and specialized libraries, communicated via high-bandwidth gRPC.

### 🛠 Improvements
- **New API Endpoints**: `/v1/metrics`, `/v1/traces`, and `/v1/health/detailed` provide real-time introspection into the Go backbone.
- **JIT Absorption**: Direct "vibration" of verified knowledge into the Go-native Subconscious Field.
- **ARC & Symbolic Solvers**: Native Go management of the Abstraction & Reasoning Corpus and formal logic solvers.

## Installation & Running
The system now requires Go 1.21+ to build the backbone.
```bash
go build -o bin/backbone cmd/backbone/main.go
./bin/backbone
```
The Python worker is managed automatically by the backbone sidecar mesh.

---
*Oricli-Alpha is now truly Sovereign.*
