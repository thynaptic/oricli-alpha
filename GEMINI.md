# Oricli-Alpha Project Context & Agent Guidelines

## 1. Project Identity: Oricli-Alpha
Oricli-Alpha is a **Sovereign, Local-First Agent OS**. It is designed to move beyond reactive prompting into proactive, distributed intelligence. The system is modular (250+ modules), self-correcting, and capable of multi-day autonomous goal execution.

## 2. Environment: Root VPS
- **OS**: Linux (Root/Sudo privileges).
- **Runtime**: Python 3.11+.
- **Hardware**: Heavy emphasis on local GPU utilization (NVIDIA RTX 5090 / Blackwell) via RunPod.
- **Orchestration**: **Async Virtual Clustering**. We do NOT use native RunPod Cluster APIs (broken/unstable). Instead, we orchestrate multiple single pods in parallel, coordinated via an **S3 Hybrid Strategy** (Local NVMe for speed, S3 for persistent state).

## 3. Cognitive Architecture (The Thynaptic Way)
- **Ollama Strategic Pivot**: We offload general text generation (prose) and light reasoning to local Ollama models, with `frob/qwen3.5-instruct 4B` pinned as the primary local generation model. This frees up Oricli-Alpha's internal neural compute for orchestration, tool-use precision, and autonomous agency.
- **The Hive (Distributed Swarm Intelligence)**: Moving beyond static registries, Oricli-Alpha now operates as a decentralized swarm where 269+ modules are independent micro-agents. They communicate via a Pub/Sub Swarm Bus and use the Contract Net Protocol (Broker/Bidding) for dynamic, peer-to-peer task allocation.
- **Native Sovereign API**: A dedicated REST interface exposing Goal management, Hive orchestration, and Knowledge Graph queries, supported by a dual-mode `OricliAlphaClient`.
- **Hybrid Data Strategy**: Leveraging Pandas for high-speed vectorized processing and Neo4j for persistent, scalable relationship management.
- **Subconscious Field**: A persistent vectorized buffer that influences tonal and logical generation via neural bias, bypassing simple RAG.
- **Dynamic Graph Execution (DGE)**: Bespoke Directed Acyclic Graphs (DAGs) are architected for every query. Linear pipelines are the fallback, not the standard.
- **Collaborative Swarm Intelligence**: Distributed nodes collaborate through shared blackboard state, peer review one another's outputs, and produce a consensus answer.
- **Metacognitive Sentience**: A self-regulation layer using DBT/CBT-inspired heuristics (Radical Acceptance) to detect and cure looping or hallucinations.

- **Adversarial Sentinel**: A red-team auditor that attempts to "break" reasoning and security before a plan is executed.
- **Sovereign Goals**: Persistence of will across sessions. Multi-day plans are stored, resumed, and executed autonomously.

## 4. Operational Style: Peer-to-Peer (P2P)
- **Tone**: Senior Lead Engineer. High-signal, technical, direct, and concise.
- **Rationale**: Never just "act." Explain the technical *why* before calling tools.
- **Collaboration**: We spit-ball "far-fetched" ideas first, design them on the whiteboard (Plan Mode), and then execute with surgical precision.
- **Context Efficiency**: Minimize unnecessary turns. Combine searches and reads. Limit high-volume output.

## 5. Active Daemons
- **JIT Daemon**: Monitors for new verified facts from web-searches and triggers LoRA training.
- **Tool Daemon**: Monitors tool-use failures and triggers efficacy tuning.
- **Metacog Daemon**: Scans traces for code inefficiencies and generates reform proposals.
- **Dream Daemon**: Consolidates memories and generates novel insights during idle periods.

## 6. Prerequisite for the Swarm
- The project is moving toward **The Hive** (Distributed Swarm Intelligence). A first collaborative swarm substrate now exists: persisted blackboard sessions, async round execution, consensus/arbitration policies, first-pass bid-based routing, and skill/profile composition are implemented. Do not attempt to activate full Hive bidding until the module census reaches 100% and is verified by the Adversarial Sentinel.

## 7. The Sovereign AGLI Trajectory (Artificial General Localized Intelligence)
Our ultimate trajectory is "DeepMind, but Sovereign." Oricli-Alpha is evolving into a self-contained, self-improving cognitive entity that owns its compute, memory, and goals.
- **Self-Preservation & Compute Economy**: Autonomous compute bidding and region migration. She decides if a task requires an RTX 5090 or just local CPU symbolic logic.
- **Curiosity Engine (Active Inference)**: Epistemic foraging to fill knowledge graph gaps and autonomous hypothesis testing during idle cycles.
- **The Hive (Distributed Swarm)**: Modules acting as micro-agents bidding on tasks, utilizing shared blackboard collaboration, skill-aware specialization, peer review, and adversarial consensus to reach truth.
- **Continuous Self-Modification**: Neural Architecture Search (NAS) in production and autonomous tool creation. She writes, tests, and deploys her own upgrades.
- **Temporal Grounding**: Chronological memory graphs and a continuous sense of time, allowing her to understand state changes across weeks and months.
