# Product Requirements Document: Oricli-Alpha

## 1. Mission Statement
To build the definitive **Sovereign Agent OS**: a proactive, local-first intelligence capable of autonomous, multi-day goal execution, sensory integration, and self-directed evolution—moving toward **Artificial General Localized Intelligence (AGLI)**. See [AGLI Vision](docs/AGLI_VISION.md) for the strategic trajectory.

## 2. Target Audience
Founders, developers, and researchers building high-stakes, privacy-first cognitive systems that require deep reasoning and autonomous action without reliance on centralized cloud LLMs.

## 3. Core Functional Requirements

### 3.1 Cognitive Infrastructure
- **Ollama Utility Bridge**: Offloads general text generation and light reasoning to local Ollama models (e.g. frob/qwen3.5-instruct 4B) to maximize system performance and focus internal compute on high-level orchestration.
- **Dynamic Reasoning**: Replaces linear pipelines with Graph-based execution (DGE) tailored to each query.
- **Profile-Governed Agents**: Task-specific agent profiles constrain which modules, operations, instructions, and model preferences an agent may use, enabling safer specialization without duplicating module logic.
- **Distributed "Hive" Swarm**: A decentralized multi-agent system where 269+ modules operate as independent micro-agents. Features a real-time Swarm Bus (Pub/Sub) and Contract Net Protocol (Broker/Bidding) for dynamic task allocation.
- **Native Sovereign API**: A dedicated, remote-capable interface exposing Oricli's core OS functions (Goals, Swarms, Knowledge Graph) alongside OpenAI-compatible endpoints.
- **Dual-Mode Client**: `OricliAlphaClient` supports both local module proxying and remote REST API orchestration via a `base_url`.
- **Hybrid Memory Layer**: Uses Pandas for high-speed vectorized data processing and Neo4j for persistent, scalable relationship management across the knowledge graph.
- **Collaborative Swarm Layer**: Distributed node coordination now supports shared blackboard state, peer review, consensus scoring, bid-based participant routing, and final synthesis before an overall answer is returned.

- **Persistent Swarm Sessions**: Collaborative runs persist message logs, shared state, contributions, reviews, and final consensus for resumable multi-round deliberation.
- **Skill-Aware Swarm Nodes**: Swarm participants can now combine a hard `agent_profile` policy with a soft `skill_manager` overlay, yielding inspectable instruction layers and skill-aware bidding without relaxing execution constraints.
- **Neural Subconscious**: Maintains a vectorized influence field to ensure consistency and persistent bias without bloating prompt context.
- **Multi-Modal Native**: Processes vision (image) and auditory (voice) inputs as first-class citizens in the cognitive graph.
- **Formal Verification Bridge**: Translates generated Python into Lean 4 and verifies correctness via local Lean compiler or LLM semantic check.
- **Code Translation Engine**: AST-based cross-language porting (e.g. Python→Rust) with strict Big-O complexity preservation.
- **Knowledge Graph Builder**: Extracts entities and relationships from unstructured text into queryable RDF-style graphs, integrated with `world_knowledge`.
- **Game Theory Solver**: Symbolic normal-form game engine (`game_theory_solver` module) for multi-agent strategic reasoning (Nash equilibria, best responses, and canonical dilemmas such as Prisoner’s Dilemma, Stag Hunt, Chicken, and coordination games).

### 3.2 Proactive Agency
- **Sovereign Goals**: Supports multi-step, multi-day objectives with persistent state storage and automatic resumption across restarts.
- **Strategic Planner**: Long-horizon planning and decomposition of high-level goals into executable tracks.
- **Predictive Speculation**: Anticipates follow-up queries and pre-computes reasoning paths to achieve near-zero latency.
- **Synthetic Dreaming**: Autonomous memory consolidation and insight generation during system idle periods.
- **Collaborative Deliberation**: Multiple specialized agents can now exchange interim findings, review one another, and produce a consensus answer instead of relying on a single-pass response.

### 3.3 Security & Reliability
- **Adversarial Auditing**: Mandatory red-team pass on all execution plans before they are run.
- **Metacognitive Regulation**: Internal DBT/CBT-based sentinel to detect and self-correct looping, hallucinations, or cognitive entropy.
- **Self-Modification**: Autonomous analysis of execution traces to propose and test codebase optimizations.

### 3.4 Skill Personas
Oricli-Alpha exposes a set of **builtin skills** (role presets) that shape how she thinks, writes, and evaluates work, layered on top of the core brain modules:
- **Senior Python Engineer** (`senior_python_dev`): Deep Python refactors, performance tuning, exception safety, and testable designs.
- **DevOps/SRE** (`devops_sre`): CI/CD, observability, infra-as-code, and high-availability deployment design.
- **System Architect** (`system_architect`): Distributed systems, storage selection, and large-scale topology design.
- **Technical Writer** (`technical_writer`): READMEs, API specs, tutorials, and migration docs with working examples.
- **Data Scientist** (`data_scientist`): EDA, statistical modeling, visualizations, and data-driven recommendations.
- **Offensive Security Researcher** (`offensive_security`): Attack-surface analysis, vuln discovery, and mitigation guidance.

### 3.5 Agent Profile Library
Oricli-Alpha also exposes a set of **builtin agent execution profiles** that govern which modules and operations are allowed for a task:
- **Research** (`research_agent_profile`): Retrieval-grounded search, ranking, synthesis, and evidence verification.
- **Code** (`code_agent_profile`): Implementation-focused engineering analysis and answer formatting.
- **Compliance** (`compliance_agent_profile`): Control mapping and regulatory evidence analysis.
- **Debug** (`debug_agent_profile`): Failure isolation, reproduction, and root-cause-oriented diagnosis.
- **Benchmark** (`benchmark_agent_profile`): Performance measurement, timing interpretation, and regression analysis.
- **Security** (`security_agent_profile`): Threat modeling, adversarial review, and hardening guidance.
- **Memory** (`memory_agent_profile`): Retrieval, recall, and long-horizon context stitching.
- **Orchestrator** (`orchestrator_agent_profile`): Delegation, routing, and multi-agent stage coordination.
These profiles can also be resolved declaratively from task types such as `debug`, `benchmark`, `security`, `memory`, and `orchestration`, reducing ad hoc policy selection at runtime.

## 4. Technical Architecture Requirements

### 4.1 Orchestration
- **Async Virtual Clustering**: Ability to scale horizontally across independent GPU nodes using an S3-hybrid coordination strategy.
- **Resource Elasticity**: Automatic fallback to auto-selection if specific GPU requested is unavailable (Supply Constraint).
- **Swarm Blackboard Coordination**: Multi-agent runs use a shared blackboard with persisted session state, round barriers, and consensus policies (`weighted_vote`, `majority`, `verifier_wins`, `merge_top`).
- **Async Swarm Execution**: Collaborative nodes can execute concurrently within a round, then safely merge outputs into shared state before peer review and arbitration.
- **Economic Routing**: Swarm participants estimate utility-scored bids and can be selected by `auto`, `all`, `top_k`, or `threshold` policies before each collaborative run.

### 4.2 Training & Learning
- **JIT Absorption**: Real-time Supervised Fine-Tuning (SFT) on verified web-search results.
- **Tool-Efficacy Pass**: Automated DPO (Direct Preference Optimization) training based on benchmarked tool-use failures.
- **LoRA Adapter Routing**: Modular weight updates stored as distinct adapters to prevent catastrophic forgetting.

## 5. Roadmap & Future Vision (The Hive)
The capstone of Oricli-Alpha is the transition from an "Orchestrated OS" to a "Distributed Hive," in line with the [AGLI Vision](docs/AGLI_VISION.md).
- **Decentralization**: 250+ brain modules operating as independent micro-agents, with the first collaborative swarm substrate now implemented.
- **Market Dynamics**: First-pass agent bidding and route selection are now implemented; the next phase is richer Contract Net-style negotiation and learned bid calibration.
- **Collective Intelligence**: Emergent problem-solving now combines peer-to-peer module collaboration, verifier arbitration, persistent blackboard state, and skill/profile composition at the node level.

## 6. Metrics for Success
- **Action-IQ**: Percentage of correct tool selection and syntax compliance (ToolBench).
- **Resilience**: Rate of successful autonomous recovery from detected hallucinations (Sentinel).
- **Latency**: Perceived response time reduction through predictive speculation (Pre-Cog).
- **Fluidity**: Effectiveness of multi-modal sensory routing in complex reasoning tasks for Oricli-Alpha.
- **Verification Rigor**: Formal verification bridge and code translation engine adoption for correctness- and complexity-preserving code generation.
