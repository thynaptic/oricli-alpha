# Reasoning Systems — Oricli-Alpha / ORI Studio

**Document Type:** Technical Reference  
**Version:** v2.1.0  
**Status:** Active  

---

## Overview

Oricli-Alpha’s reasoning stack is a **Go-native orchestration layer** that treats LLMs as compute subsystems, not as the sole source of intelligence. Reasoning is composed from deterministic state machines, structured search, memory retrieval, and policy gates, then fused with generation for the final response. The system dynamically routes between methods based on task complexity and explicit routing preferences.  

**Primary entrypoints and references:**
- Go-native reasoning pipeline and execution: `pkg/core/http/server.go`, `pkg/core/reasoning/`, `pkg/core/metareasoning/`
- MCTS engine: `docs/MCTS_REASONING.md`, `pkg/cognition/mcts_*`, `pkg/node/tree_reasoning_module.go`
- ToT engine: `pkg/cognition/tot.go`
- Reasoning strategies service: `pkg/service/reasoning_strategies.go`, `pkg/node/reasoning_strategies_module.go`
- Sovereign Engine orchestration: `pkg/cognition/` (router, instructions, generators)

---

## Core Reasoning Methods (Live)

### 1) Monte Carlo Tree Search (MCTS)*
**Purpose:** Deep deliberative search for complex or high-uncertainty queries.  
**Implementation:** Compiled Go MCTS engine with rollouts, branch expansion, and adversarial evaluation.  
**References:** `docs/MCTS_REASONING.md`, `pkg/cognition/mcts_*`, `pkg/core/http/server.go`

### 2) Tree of Thoughts (ToT)
**Purpose:** Breadth-first search over multiple reasoning branches; best-path selection.  
**Implementation:** Go-native ToT engine with layer expansion, diversity prompts, and path reconstruction.  
**References:** `pkg/cognition/tot.go`, `pkg/node/tree_reasoning_module.go`

### 3) Structured Reasoning Strategies
**Purpose:** Specialized prompting patterns for targeted analysis.  
**Methods:** Analogical, causal, comparative, temporal, step-by-step, verification, and more.  
**References:** `pkg/service/reasoning_strategies.go`, `pkg/node/reasoning_strategies_module.go`

### 4) Adaptive Reasoning Budgeting
**Purpose:** Dynamically scale depth/iterations based on complexity signals.  
**Implementation:** Complexity detector that tunes MCTS depth, rollout counts, and activation thresholds.  
**References:** `pkg/cognition/adaptive.go`, `pkg/cognition/substrate.go`

---

## Memory-Grounded Reasoning

### 5) Hybrid Retrieval + RAG
**Purpose:** Ground reasoning with durable memory, knowledge graph context, and RAG fragments.  
**Implementation:** Hybrid retrieval (keyword + embeddings), provenance weighting, volatility-aware decay, and memory anchoring.  
**References:** `docs/MEMORY_ARCHITECTURE.md`, `docs/POCKETBASE_MEMORY.md`, `docs/EPISTEMIC_HYGIENE.md`

### 6) Relational Context + Belief State*
**Purpose:** Maintain structured entity relationships and session-local fog-of-war state during reasoning.  
**Implementation:** RelationalContext derived from the Working Memory Graph; per-session BeliefState tracking.  
**References:** `pkg/cognition/instructions.go`, `pkg/api/server_v2.go`

---

## Meta-Reasoning & Verification

### 7) Aletheia Loop / Balanced Prompting*
**Purpose:** Counter confirmation bias and improve reliability via structured adversarial evaluation.  
**Implementation:** Balanced prompting + verifier pass; optionally triggers corrective actions.  
**References:** `pkg/cognition/instructions.go`, `pkg/cognition/epistemic_filter.go`, `pkg/api/server_v2.go`

### 8) Self-Consistency + Grounded Verifier
**Purpose:** Cross-check candidate answers for stability and evidence alignment.  
**References:** `docs/CHANGELOG.md` (v3.x cognition upgrades), `pkg/cognition/` modules

### 9) ExploiterLeague Adversarial Auditing*
**Purpose:** Post-stream adversarial auditing of responses via specialist “exploiter” checks.  
**Implementation:** Multi-agent audit loop inspired by league-based training.  
**References:** `pkg/cognition/exploiter_league.go`, `pkg/api/server_v2.go`

---

## Planning & Decomposition

### 10) Response Planning*
**Purpose:** Hierarchical decision-making over action space (plan → subplan → action).  
**Implementation:** ResponsePlanner with multi-level decision modeling and arbitration.  
**References:** `pkg/cognition/instructions.go`, `pkg/cognition/planner.go`

### 11) SELF-DISCOVER Plan Composition
**Purpose:** Compose reasoning plans dynamically based on task structure.  
**Implementation:** Plan discovery, persistence, and reuse for effective structures.  
**References:** `pkg/api/server_v2.go`, `docs/CHANGELOG.md`

---

## Symbolic & Hybrid Reasoning

### 12) Symbolic Overlay & Logical Filters
**Purpose:** Constrain reasoning with deterministic symbolic scaffolding where required.  
**Implementation:** Symbolic overlays, constraint filters, and policy-consistent reasoning prompts.  
**References:** `pkg/core/http/server.go`, `pkg/core/reasoning/`, `pkg/cognition/symbolic.go`

### 13) ARC Induction/Transduction
**Purpose:** Abstract reasoning via induction + transduction for ARC-style tasks.  
**References:** `docs/arc_induction_transduction_implementation.md`, `pkg/` ARC modules

---

## Routing & Orchestration

### 14) Reasoning Router
**Purpose:** Selects the optimal method (MCTS, ToT, direct, multi-agent) based on policy + query signals.  
**References:** `pkg/core/http/server.go`, `pkg/service/reasoning_orchestrator.go`, `pkg/cognition/` router logic

### 15) Multi-Agent Reasoning (Swarm)
**Purpose:** Distribute reasoning across specialized agents and aggregate results.  
**References:** `pkg/core/orchestrator/`, `pkg/service/agent.go`, `docs/ROSETTA.md`

---

## Notes on DeepMind-Inspired Methods

Methods marked with an asterisk (*) are inspired by DeepMind research lines or systems (e.g., AlphaGo/AlphaZero MCTS, AlphaStar league training, and Aletheia-style verification). These are inspirations only; implementations are sovereign, Go-native, and tailored to Oricli-Alpha’s architecture.
