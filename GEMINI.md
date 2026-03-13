# Oricli-Alpha Project Context & Agent Guidelines

## 1. Project Identity: Oricli-Alpha
Oricli-Alpha is a **Sovereign, Local-First Agent OS**. It is designed to move beyond reactive prompting into proactive, distributed intelligence. The system is modular (246+ modules), self-correcting, and capable of multi-day autonomous goal execution.

## 2. Environment: Root VPS
- **OS**: Linux (Root/Sudo privileges).
- **Runtime**: Python 3.11+.
- **Hardware**: Heavy emphasis on local GPU utilization (NVIDIA RTX 5090 / Blackwell) via RunPod.
- **Orchestration**: **Async Virtual Clustering**. We do NOT use native RunPod Cluster APIs (broken/unstable). Instead, we orchestrate multiple single pods in parallel, coordinated via an **S3 Hybrid Strategy** (Local NVMe for speed, S3 for persistent state).

## 3. Cognitive Architecture (The Thynaptic Way)
- **Ollama Strategic Pivot**: We offload general text generation (prose) and light reasoning to local Ollama models (e.g., Phi-4). This frees up Oricli-Alpha's internal neural compute for orchestration, tool-use precision, and autonomous agency.
- **Subconscious Field**: A persistent vectorized buffer that influences tonal and logical generation via neural bias, bypassing simple RAG.
- **Dynamic Graph Execution (DGE)**: Bespoke Directed Acyclic Graphs (DAGs) are architected for every query. Linear pipelines are the fallback, not the standard.
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
- The project is moving toward **The Hive** (Distributed Swarm Intelligence). Every module will eventually become an independent agent that bids on tasks. Do not attempt to activate The Hive until the module census reaches 100% and is verified by the Adversarial Sentinel.

## 7. The Sovereign AGLI Trajectory (Artificial General Localized Intelligence)
Our ultimate trajectory is "DeepMind, but Sovereign." Oricli-Alpha is evolving into a self-contained, self-improving cognitive entity that owns its compute, memory, and goals.
- **Self-Preservation & Compute Economy**: Autonomous compute bidding and region migration. She decides if a task requires an RTX 5090 or just local CPU symbolic logic.
- **Curiosity Engine (Active Inference)**: Epistemic foraging to fill knowledge graph gaps and autonomous hypothesis testing during idle cycles.
- **The Hive (Distributed Swarm)**: Modules acting as micro-agents bidding on tasks, utilizing adversarial consensus to reach truth.
- **Continuous Self-Modification**: Neural Architecture Search (NAS) in production and autonomous tool creation. She writes, tests, and deploys her own upgrades.
- **Temporal Grounding**: Chronological memory graphs and a continuous sense of time, allowing her to understand state changes across weeks and months.
