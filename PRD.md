# Product Requirements Document: Oricli-Alpha

## 1. Mission Statement
To build the definitive **Sovereign Agent OS**: a proactive, local-first intelligence capable of autonomous, multi-day goal execution, sensory integration, and self-directed evolution—moving toward **Artificial General Localized Intelligence (AGLI)**. See [AGLI Vision](docs/AGLI_VISION.md) for the strategic trajectory.

## 2. Target Audience
Founders, developers, and researchers building high-stakes, privacy-first cognitive systems that require deep reasoning and autonomous action without reliance on centralized cloud LLMs.

## 3. Core Functional Requirements

### 3.1 Cognitive Infrastructure
- **Ollama Utility Bridge**: Offloads general text generation and light reasoning to local Ollama models (e.g. qwen2.5:7b) to maximize system performance and focus internal compute on high-level orchestration.
- **Dynamic Reasoning**: Replaces linear pipelines with Graph-based execution (DGE) tailored to each query.
- **Neural Subconscious**: Maintains a vectorized influence field to ensure consistency and persistent bias without bloating prompt context.
- **Multi-Modal Native**: Processes vision (image) and auditory (voice) inputs as first-class citizens in the cognitive graph.
- **Formal Verification Bridge**: Translates generated Python into Lean 4 and verifies correctness via local Lean compiler or LLM semantic check.
- **Code Translation Engine**: AST-based cross-language porting (e.g. Python→Rust) with strict Big-O complexity preservation.
- **Knowledge Graph Builder**: Extracts entities and relationships from unstructured text into queryable RDF-style graphs, integrated with `world_knowledge`.

### 3.2 Proactive Agency
- **Sovereign Goals**: Supports multi-step, multi-day objectives with persistent state storage and automatic resumption across restarts.
- **Strategic Planner**: Long-horizon planning and decomposition of high-level goals into executable tracks.
- **Predictive Speculation**: Anticipates follow-up queries and pre-computes reasoning paths to achieve near-zero latency.
- **Synthetic Dreaming**: Autonomous memory consolidation and insight generation during system idle periods.

### 3.3 Security & Reliability
- **Adversarial Auditing**: Mandatory red-team pass on all execution plans before they are run.
- **Metacognitive Regulation**: Internal DBT/CBT-based sentinel to detect and self-correct looping, hallucinations, or cognitive entropy.
- **Self-Modification**: Autonomous analysis of execution traces to propose and test codebase optimizations.

## 4. Technical Architecture Requirements

### 4.1 Orchestration
- **Async Virtual Clustering**: Ability to scale horizontally across independent GPU nodes using an S3-hybrid coordination strategy.
- **Resource Elasticity**: Automatic fallback to auto-selection if specific GPU requested is unavailable (Supply Constraint).

### 4.2 Training & Learning
- **JIT Absorption**: Real-time Supervised Fine-Tuning (SFT) on verified web-search results.
- **Tool-Efficacy Pass**: Automated DPO (Direct Preference Optimization) training based on benchmarked tool-use failures.
- **LoRA Adapter Routing**: Modular weight updates stored as distinct adapters to prevent catastrophic forgetting.

## 5. Roadmap & Future Vision (The Hive)
The capstone of Oricli-Alpha is the transition from an "Orchestrated OS" to a "Distributed Hive," in line with the [AGLI Vision](docs/AGLI_VISION.md).
- **Decentralization**: 250+ brain modules operating as independent micro-agents (current: 253 registered).
- **Market Dynamics**: Agents bidding on sub-tasks via a Contract Net protocol.
- **Collective Intelligence**: Emergent problem-solving through peer-to-peer module collaboration.

## 6. Metrics for Success
- **Action-IQ**: Percentage of correct tool selection and syntax compliance (ToolBench).
- **Resilience**: Rate of successful autonomous recovery from detected hallucinations (Sentinel).
- **Latency**: Perceived response time reduction through predictive speculation (Pre-Cog).
- **Fluidity**: Effectiveness of multi-modal sensory routing in complex reasoning tasks for Oricli-Alpha.
- **Verification Rigor**: Formal verification bridge and code translation engine adoption for correctness- and complexity-preserving code generation.
