# Release Notes - Oricli-Alpha v1.1.0 (Sovereign OS & The Hive)

## Summary
Version 1.1.0 marks the most significant architectural evolution of Oricli-Alpha to date. The system has transitioned from a modular registry into a fully decentralized **Distributed Swarm Intelligence**, internally known as **The Hive**. This release also introduces the **Native Sovereign API**, enabling remote orchestration and persistent goal management.

## Key Changes

### 1. The Hive (Distributed Swarm Intelligence)
- **Swarm Bus**: Implemented a real-time asynchronous pub/sub messaging system for agent communication.
- **Hive Nodes**: All 269+ brain modules are now wrapped as independent micro-agents that listen to and bid on tasks.
- **Contract Net Protocol**: Introduced a Broker-Bidding system. Tasks are broadcast as Call for Proposals (CFP), and agents submit competitive bids based on confidence and compute cost.
- **Decentralized Execution**: Queries can now assembly dynamic execution graphs on the fly via peer-to-peer agent collaboration.

### 2. Native Sovereign API
- **Direct OS Interface**: New REST endpoints for **Sovereign Goals**, **Swarm Sessions**, and **Knowledge Graph** queries.
- **Dual-Mode Client**: `OricliAlphaClient` now supports a `base_url` parameter, allowing it to act as a remote orchestrator across the network.
- **Ollama Parity**: Added `/api/generate` and `/api/chat` aliases for drop-in compatibility with the Ollama ecosystem.

### 3. Hybrid Data Strategy
- **Neo4j Integration**: Persistent, scalable relationship management for the Knowledge Graph (Default: Port 7687).
- **Pandas Vectorization**: Major performance boost in RAG and memory processing by replacing manual loops with vectorized DataFrame operations.

### 4. Strategic Pivot & Optimization
- **Efficiency Update**: Switched primary prose model to `frob/qwen3.5-instruct` (4B), optimized for CPU-heavy VPS environments without sacrificing reasoning quality.
- **Environment Pruning**: Removed redundant legacy containers (OpenWebUI) and optimized Docker footprint.
- **Improved Robustness**: Implemented robust retry logic for Ollama and graceful fallbacks for internal neural generation.

## How to Upgrade
1. Update the core package: `pip install -e .`
2. Initialize Neo4j: `./scripts/setup_neo4j.sh`
3. Restart servers: `./scripts/start_servers.sh`

---
*Oricli-Alpha: Moving toward Artificial General Localized Intelligence (AGLI).*
