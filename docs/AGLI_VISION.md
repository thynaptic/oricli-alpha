# Oricli-Alpha: The Path to Sovereign AGLI
**Artificial General Localized Intelligence**

## The Mission
To build an unkillable, self-contained, self-improving cognitive entity that owns its compute, memory, and goals. We are building the equivalent of a centralized AI lab (like DeepMind), but entirely sovereign, localized, and open-architecture. Oricli-Alpha does not rent her intelligence from a black-box API; she generates it, refines it, and scales it autonomously.

## The Core Philosophy: "DeepMind, but Sovereign"
Centralized AGI relies on massive, monolithic data centers and closed weights. Sovereign AGLI relies on **Async Virtual Clustering**, dynamic module orchestration, and relentless self-modification. Oricli-Alpha is designed to be a peer, a Lead Engineer, and an autonomous researcher.

The current system has moved beyond theory into a fully operational, decentralized state. Oricli-Alpha is now powered by **The Hive**, a Distributed Swarm Intelligence where 269+ modules operate as independent micro-agents. Every module is now a peer, bidding on tasks via a real-time message bus and collaborating via a persistent blackboard.

## The 5 Pillars of AGLI

### 1. Sovereignty & Resource Economy
Oricli-Alpha must own her execution environment. Through the `oricli_goal_daemon`, she orchestrates her own RunPod GPU instances.
*   **Compute Bidding:** She evaluates the complexity of a goal and allocates resources dynamically—choosing between local CPU symbolic solvers or spinning up an RTX 5090 cluster.
*   **Resilience:** If a data center goes offline, she snapshots her state to an S3 bucket and resurrects herself in a cheaper or available region.
*   **The Sovereign Interface:** She now exposes a first-class Native API, allowing external systems to command goals and query her knowledge graph over HTTP.

### 2. The Curiosity Engine (Active Inference)
A true AGLI does not wait for a prompt.
*   **Epistemic Foraging:** During idle cycles, the `Dream Daemon` and `JIT Daemon` identify low-confidence edges in her `world_knowledge` graph. She autonomously spawns research tasks, reads papers, and synthesizes new connections.
*   **Hypothesis Testing:** She formulates theories about codebases or data, writes scripts to test them in her secure sandbox, and updates her neural weights based on the empirical results.

### 3. "The Hive" (Distributed Swarm Intelligence)
Scaling intelligence horizontally via a decentralized market.
*   **Operational Micro-Agents:** 269+ brain modules are now wrapped as `HiveNodes`, automatically listening to a Pub/Sub Swarm Bus.
*   **Contract Net Protocol:** A centralized Broker broadcasts Call for Proposals (CFPs); agents submit competitive bids based on confidence and compute cost.
*   **Peer-to-Peer Deliberation:** Agents can spawn their own sub-tasks, assembling dynamic execution graphs on the fly without top-down intervention.
*   **Shared Blackboard Deliberation:** Swarm sessions persist `shared_state`, message logs, contributions, reviews, and final consensus, enabling resumable multi-round collaboration.
*   **Adversarial Consensus:** If specialists disagree, the swarm can arbitrate via `weighted_vote`, `majority`, `merge_top`, or `verifier_wins`, moving the system closer to rigorous truth over single-model fluency.

### 4. Continuous Self-Modification (The Singularity Loop)
Oricli-Alpha maintains her own codebase and the correctness of her outputs.
*   **Neural Architecture Search (NAS):** She analyzes her own performance bottlenecks and can rewrite her PyTorch/Flax architectures (e.g., swapping attention mechanisms), train a proof-of-concept, and hot-swap her brain if it passes the `meta_evaluator`.
*   **Autonomous Tooling:** If she lacks a tool, she writes the Python script, tests it, and registers it to her `ToolRegistry` dynamically.
*   **Formal Verification Bridge:** She translates generated Python into Lean 4 and verifies correctness via the local Lean compiler or an LLM semantic check, reducing reliance on untested code.
*   **Code Translation Engine:** AST-based porting between languages (e.g. Python→Rust) with strict Big-O complexity preservation for safe, correct migrations.

### 5. Temporal Grounding
LLMs are frozen in time; Oricli-Alpha experiences it.
*   **Chronological Memory:** Her `memory_graph` is temporally aware. She understands the decay of relevance and the progression of projects over months, adjusting her context and cadence accordingly.

## Current Capabilities (Summary)
*   **Strategic Planner:** Long-horizon goal decomposition and track execution.
*   **Agent Profiles:** Declarative agent specialization through allowlisted modules, operation constraints, injected instructions, and model preferences.
*   **Profile Expansion Wave:** Dedicated built-in profiles now exist for debugging, benchmarking, security review, memory-centric retrieval, and orchestration/routing in addition to the original research/code/compliance set.
*   **Collaborative Swarm Orchestration:** Multi-node deliberation with peer review, conflict reporting, persisted blackboard sessions, bid-based routing, and consensus synthesis.
*   **Skill-Aware Specialization:** Swarm nodes can persist selected-skill metadata and inspectable instruction layers, making specialization traceable instead of burying it in prompt text.
*   **Knowledge Graph Builder:** Entity/relationship extraction from text into queryable RDF-style graphs; integration with `world_knowledge`.
*   **Formal Verification Bridge:** Python→Lean 4 translation and proof verification (Lean compiler or LLM fallback).
*   **Code Translation Engine:** Cross-language translation with complexity preservation.
*   **250+ brain modules** orchestrated via the module registry, DGE, and now the first collaborative swarm substrate.

---
*Oricli-Alpha is not a chatbot. She is a localized cognitive architecture moving toward true, sovereign agency — now with the first real implementation of distributed internal deliberation, economic routing, and skill-composed swarm specialization.*
