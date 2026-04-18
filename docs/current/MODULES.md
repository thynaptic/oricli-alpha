# Oricli-Alpha Native Modules (Go Backbone)

This repository has completed its architectural transition to a Go-native backbone. Intelligence is now decentralized across a high-performance Swarm Bus.

## Architecture: Go-First
Oricli-Alpha's core is implemented in Go to leverage true multi-core parallelism on EPYC VPS hardware. Python is utilized as a **Sidecar Mesh** for specific LLM execution and specialized math libraries.

## Core Services (Go-Native)

### 1. The Nervous System
- **Module Registry**: Handles discovery and metadata for the entire swarm.
- **Monitor Service**: Real-time heartbeat and health diagnostics.
- **Availability Manager**: Ensures 0% downtime via native recovery loops.
- **Recovery Service**: Exponential backoff and self-healing.

### 2. Cognitive Orchestration
- **Reasoning Orchestrator**: Selects between MCTS, ToT, and CoT based on complexity.
- **Swarm Bus**: Native high-speed message passing via Goroutines.
- **Planner Service**: Multi-step strategic execution and prompt chaining.

### 3. Specialized Reasoning
- **ARCSolver**: Native logic for ARC (Abstraction & Reasoning Corpus) tasks.
- **Symbolic Solver Manager**: Orchestrates Z3, SymPy, and Prolog bridges.
- **Strategy Suite**: Causal, Counterfactual, Analogical, and Deductive reasoning.

### 4. Swarm Agents
- **Retriever Agent**: Concurrent memory and web retrieval.
- **Verifier Agent**: Real-time factual validation and self-correction.
- **Synthesis Agent**: Grounded response generation.
- **Agent Pipeline**: End-to-end orchestration of the Q&A lifecycle.

### 5. Utilities & Infrastructure
- **Memory Bridge**: High-speed LMDB storage with AES-GCM encryption.
- **Tool Service**: Native tool registration and LLM tool-call parsing.
- **Voice Engine**: Persona-aware naturalization and emotional tracking.
- **Safety Service**: Advanced threat analysis and instruction injection detection.

## Legacy & ML Archival
All legacy Python-based logic modules (250+) have been archived to `oricli_core/brain/modules/archive/legacy_logic/`. Heavy ML models and datasets are archived to `legacy_ml/` to optimize system memory.

## Integration
Python modules interact with the Go backbone via:
1. **gRPC**: For high-bandwidth execution and manifest discovery.
2. **Go Bridge (`go_bridge.py`)**: A compatibility layer allowing Python agents to call Go-native services as if they were local.
