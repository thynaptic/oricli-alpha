# Reasoning Systems — Oricli-Alpha / ORI Studio

**Document Type:** Technical Reference  
**Version:** v3.1.0  
**Status:** Active  

---

## Overview

Oricli-Alpha's reasoning stack is a **Go-native orchestration layer** that treats LLMs as compute subsystems, not as the sole source of intelligence. Reasoning is composed from deterministic state machines, structured search, memory retrieval, and policy gates, then fused with generation for the final response. The system routes queries across a **dual-track architecture**: a fast-path for keyword-matched queries and an **Adaptive Reasoning Engine (ARE)** for high-complexity / ambiguous queries.

**Primary entrypoints and references:**
- Mode classification & dispatch: `pkg/cognition/reasoning_modes.go` (`ClassifyReasoningMode()`), `pkg/cognition/reasoning_engines.go`
- Adaptive Reasoning Engine: `pkg/cognition/adaptive_engine.go` (`runAdaptive()`, `arePolicy()`, `areValue()`)
- Sovereign engine orchestration: `pkg/cognition/sovereign.go`, `pkg/cognition/instructions.go`
- MCTS engine: `docs/MCTS_REASONING.md`, `pkg/cognition/mcts_*`, `pkg/core/reasoning/mcts.go`
- ToT engine: `pkg/cognition/tot.go`, `pkg/service/reasoning_tot.go`
- CoT / MCTS service wrappers: `pkg/service/reasoning_cot.go`, `pkg/service/reasoning_mcts.go`
- Core reasoning pipeline: `pkg/core/reasoning/` (decompose, executor, multiagent, geometry_fusion)
- Meta-reasoning evaluation: `pkg/core/metareasoning/chain.go`, `pkg/core/metareasoning/evaluator.go`
- Reasoning strategies service: `pkg/service/reasoning_strategies.go`, `pkg/node/reasoning_strategies_module.go`

---

## Dual-Track Architecture (v3.1.0)

### Track 1 — Fast Path
All queries with a strong keyword signal route directly to a specific mode. Same latency as before; no change for these paths.

### Track 2 — Adaptive Reasoning Engine (ARE)
Fires when complexity ≥ 0.55 AND no strong keyword signal is present. Replaces the old static `ModeDiscover` catch-all.

The ARE runs a **multi-step loop** (max 3 steps, hard cap):

```
Query → [complexity ≥ 0.55, no keyword] → ARE loop:
  Step 1: Consistency (3-vote plurality — fastest standalone answerer)
  Step 2: Debate     (adversarial synthesis → finalized with 1 LLM call)  [if step 1 < 0.60]
  Step 3: Discover   (structured plan → finalized with 1 LLM call)         [if step 2 < 0.60]
```

**Exit criteria:** Confidence (Value score) ≥ 0.75 → stop early. Budget exhausted → return best answer seen. Always returns a non-empty answer.

**Context design:** ARE uses `context.WithoutCancel` so HTTP client disconnection doesn't kill mid-step reasoning. Each step has its own 90s timeout.

### Value Function (`areValue`)
Pure heuristic, < 1ms. Scores answer quality on [0.0, 1.0]:

| Condition | Score |
|-----------|-------|
| Empty | 0.0 |
| < 50 chars | 0.20 |
| 50–200 chars | 0.50 |
| 200–500 chars | 0.62 |
| > 500 chars | 0.70 |
| + structured output (lists, code, headings) | +0.08 |
| + reasoning markers (therefore, because, etc.) | +0.04 |
| - hedging opener (I don't know, I cannot, etc.) | -0.30 |

---

## Reasoning Mode Dispatcher (v3.1.0)

All inference passes route through `ClassifyReasoningMode()` in `pkg/cognition/reasoning_modes.go`. It accepts a stimulus string + `AdaptiveBudget` and returns one of 13 `ReasoningMode` constants. The selected mode's runner executes in `pkg/cognition/reasoning_engines.go` or `pkg/cognition/adaptive_engine.go`.

| Mode | Constant | Trigger Signal |
|------|----------|----------------|
| Standard | `ModeStandard` | Default / low complexity |
| Case-Based Reasoning | `ModeCBR` | Familiar pattern, provenance match |
| Program-Aided Language | `ModePAL` | Math, formulae, rate problems (`how long` + digit), code execution |
| Active Prompting | `ModeActive` | Knowledge gaps detected |
| Least-to-Most | `ModeLeastToMost` | Ordered decomposition needed |
| Self-Refine | `ModeSelfRefine` | Draft critique → refinement |
| ReAct | `ModeReAct` | Tool-use / observation loop |
| Multi-Agent Debate | `ModeDebate` | High-stakes or contested claim |
| Causal Chain | `ModeCausal` | WHY / WHAT-IF / HOW queries |
| SELF-DISCOVER | `ModeDiscover` | Called from ARE Step 3 (internal) |
| Self-Consistency | `ModeConsistency` | Logical argument eval; ARE Step 1 |
| CrossDomain Bridge | `ModeCrossdomainBridge` | Cross-domain synthesis |
| **Adaptive (ARE)** | `ModeAdaptive` | **complexity ≥ 0.55, no keyword hit** |

**Routing priority order** (first match wins in `ClassifyReasoningMode()`):
1. **PAL** — `reMath` match (arithmetic, `how long.*\d`, formula, etc.)
2. **LogicEval → Consistency** — `reLogicEval` match (`therefore`, `valid argument`, `it follows that`, `modus ponens`, etc.)
3. **Adaptive (ARE)** — complexity ≥ 0.55 (replaces old ModeDiscover catch-all)
4. **Causal / Debate / ReAct / LeastToMost / SelfRefine** — keyword + complexity gate
5. **CBR** — complexity > 0.45
6. **Consistency** — complexity ≥ 0.30
7. **Active** — uncertainty detected
8. **Standard** — fallback

---

## Core Reasoning Methods (Live)

### 1) Monte Carlo Tree Search (MCTS)*
**Purpose:** Deep deliberative search for complex or high-uncertainty queries.  
**Implementation:** Compiled Go MCTS engine with rollouts, branch expansion, and adversarial evaluation.  
**References:** `docs/MCTS_REASONING.md`, `pkg/cognition/mcts_*`, `pkg/core/reasoning/mcts.go`, `pkg/service/reasoning_mcts.go`

### 2) Tree of Thoughts (ToT)
**Purpose:** Breadth-first search over multiple reasoning branches; best-path selection.  
**Implementation:** Go-native ToT engine with layer expansion, diversity prompts, and path reconstruction.  
**References:** `pkg/cognition/tot.go`, `pkg/service/reasoning_tot.go`, `pkg/node/tree_reasoning_module.go`

### 3) Chain-of-Thought (CoT)
**Purpose:** Step-by-step reasoning trace for structured problem solving.  
**Implementation:** CoT service wrapper with prompt construction and trace extraction.  
**References:** `pkg/service/reasoning_cot.go`

### 4) Structured Reasoning Strategies
**Purpose:** Specialized prompting patterns for targeted analysis.  
**Methods:** Analogical, causal, comparative, temporal, step-by-step, verification, and more.  
**References:** `pkg/service/reasoning_strategies.go`, `pkg/node/reasoning_strategies_module.go`

### 5) Adaptive Reasoning Budgeting
**Purpose:** Dynamically scale depth/iterations based on complexity signals.  
**Implementation:** Complexity detector that tunes MCTS depth, rollout counts, and activation thresholds.  
**References:** `pkg/cognition/adaptive.go`, `pkg/cognition/substrate.go`

---

## v3.0.0 Reasoning Modes

### 6) Program-Aided Language (PAL)
**Purpose:** Offload math, logic, and deterministic computation to a Python3 subprocess — zero hallucinated arithmetic.  
**Trigger:** `reMath` regex: arithmetic expressions, unit conversions, `how long.*\d` / `\d.*how long` (rate/machine problems), formulas, equations.  
**Implementation:** PAL runner spawns a sandboxed Python3 process; result is injected back into response context.  
**References:** `pkg/cognition/pal.go`, `pkg/cognition/reasoning_engines.go`

### 7) Case-Based Reasoning (CBR)
**Purpose:** Match current query against provenance-solved cases; return known-good answers with lineage trace.  
**Implementation:** `ProvenanceSolved` tier seeded by every clean SelfAlign pass; `QuerySolved()` lookup before generation.  
**References:** `pkg/cognition/reasoning_engines.go`, `pkg/cognition/reasoning_modes.go`

### 8) Active Prompting
**Purpose:** Identify knowledge gaps in the query, then fill them via targeted search/memory before generating.  
**Implementation:** `IdentifyGaps()` → per-gap tool dispatch → enriched context passed to generation.  
**References:** `pkg/cognition/reasoning_engines.go`

### 9) Least-to-Most Decomposition
**Purpose:** Break complex queries into ordered sub-problems; solve each in dependency order (max 3 steps).  
**Implementation:** Ordered chained decomposition; each sub-answer feeds the next.  
**References:** `pkg/cognition/reasoning_engines.go`, `pkg/core/reasoning/decompose.go`

### 10) Self-Refine
**Purpose:** Draft → critique → conditional re-generation (1 iteration max); improves quality without compounding errors.  
**Implementation:** Critique pass checks for contradictions, omissions, and hallucination markers; re-generation only on failure.  
**References:** `pkg/cognition/reasoning_engines.go`

### 11) ReAct (Reason + Act)
**Purpose:** Think → Act → Observe loop for tool-augmented queries (max 3 hops).  
**Implementation:** Each hop emits a thought trace, calls a tool, observes the result, and decides to continue or conclude.  
**References:** `pkg/cognition/reasoning_engines.go`

### 12) Multi-Agent Debate
**Purpose:** High-stakes or contested claims evaluated by a panel: Advocate + Skeptic + Contrarian → Judge synthesis.  
**Implementation:** 4-role multi-agent debate with aggregated verdict.  
**References:** `pkg/cognition/reasoning_engines.go`, `pkg/core/reasoning/multiagent.go`

### 13) Causal Chain Reasoning
**Purpose:** Explicit causal extraction for WHY / WHAT-IF / HOW queries — produces structured cause→effect chains.  
**Implementation:** Dedicated causal decomposition pass; integrates with Working Memory Graph for persistent causal links.  
**References:** `pkg/cognition/causal.go`, `pkg/cognition/reasoning_engines.go`

### 14) Self-Consistency
**Purpose:** Generate N parallel candidate answers, then consensus-vote to select the most stable response.  
**Trigger:** Two paths: (1) `reLogicEval` match — syllogisms, deductive argument validity, logical fallacy questions (fires before SELF-DISCOVER catch-all); (2) medium-complexity factual queries (0.30 ≤ complexity < 0.45, below CBR threshold).  
**Logic rationale:** Small models (≤3B) fail on argument validity with single-path generation. 3 independent samples at varying temperature (0.5/0.6/0.7) + plurality vote provides error-correction that SELF-DISCOVER cannot — diversity of reasoning paths surfaces the correct answer even when any individual path fails.  
**Implementation:** Parallel sampling with diversity injection; majority-vote or embedding-similarity consensus.  
**References:** `pkg/cognition/reasoning_engines.go`, `pkg/cognition/verification.go`

---

## Memory-Grounded Reasoning

### 15) Hybrid Retrieval + RAG
**Purpose:** Ground reasoning with durable memory, knowledge graph context, and RAG fragments.  
**Implementation:** Hybrid retrieval (keyword + embeddings), provenance weighting, volatility-aware decay, and memory anchoring.  
**References:** `docs/MEMORY_ARCHITECTURE.md`, `docs/POCKETBASE_MEMORY.md`, `docs/EPISTEMIC_HYGIENE.md`

### 16) Relational Context + Belief State*
**Purpose:** Maintain structured entity relationships and session-local fog-of-war state during reasoning.  
**Implementation:** RelationalContext derived from the Working Memory Graph; per-session BeliefState tracking.  
**References:** `pkg/cognition/instructions.go`, `pkg/api/server_v2.go`

---

## Meta-Reasoning & Verification

### 17) Aletheia Loop / Balanced Prompting*
**Purpose:** Counter confirmation bias and improve reliability via structured adversarial evaluation.  
**Implementation:** Balanced prompting + verifier pass; optionally triggers corrective actions.  
**References:** `pkg/cognition/instructions.go`, `pkg/cognition/epistemic_filter.go`, `pkg/api/server_v2.go`

### 18) ExploiterLeague Adversarial Auditing*
**Purpose:** Post-stream adversarial auditing of responses via specialist "exploiter" checks.  
**Implementation:** Multi-agent audit loop inspired by league-based training.  
**References:** `pkg/cognition/exploiter_league.go`, `pkg/api/server_v2.go`

### 19) Meta-Reasoning Evaluation Chain
**Purpose:** Evaluate and score intermediate reasoning chains; prune low-quality branches before synthesis.  
**Implementation:** Chain evaluator with scoring heuristics; feeds back into adaptive budget controller.  
**References:** `pkg/core/metareasoning/chain.go`, `pkg/core/metareasoning/evaluator.go`

---

## Planning & Decomposition

### 20) Response Planning*
**Purpose:** Hierarchical decision-making over action space (plan → subplan → action).  
**Implementation:** `ResponsePlanner` (`pkg/cognition/response_planner.go`) models ActionType, ResponseStructure, and ResponseLength. `pkg/cognition/planner.go` handles Roadmap/WorkOrder construction.  
**References:** `pkg/cognition/response_planner.go`, `pkg/cognition/planner.go`, `pkg/cognition/instructions.go`

### 21) SELF-DISCOVER Plan Composition
**Purpose:** LLM self-composes a reasoning plan for novel task structures; plan is persisted and reused.  
**Implementation:** Plan discovery pass → structured plan JSON → execution via reasoning engines.  
**References:** `pkg/cognition/self_discover.go`, `pkg/cognition/reasoning_engines.go`

### 22) Task Decomposition
**Purpose:** Break multi-step goals into executable sub-tasks with dependency ordering.  
**References:** `pkg/core/reasoning/decompose.go`, `pkg/core/reasoning/executor.go`

---

## Symbolic & Hybrid Reasoning

### 23) Symbolic Overlay & Logical Filters
**Purpose:** Constrain reasoning with deterministic symbolic scaffolding where required.  
**Implementation:** Symbolic overlays, constraint filters, and policy-consistent reasoning prompts.  
**References:** `pkg/cognition/symbolic.go`, `pkg/core/reasoning/`

### 24) ARC Induction/Transduction
**Purpose:** Abstract reasoning via induction + transduction for ARC-style tasks.  
**References:** `docs/arc_induction_transduction_implementation.md`, `pkg/` ARC modules

---

## Routing & Orchestration

### 25) Reasoning Router
**Purpose:** Selects the optimal mode from the 11-mode dispatcher based on policy + query signals.  
**Implementation:** `ClassifyReasoningMode()` in `pkg/cognition/reasoning_modes.go` with `AdaptiveBudget` gating.  
**References:** `pkg/cognition/reasoning_modes.go`, `pkg/service/reasoning_orchestrator.go`, `pkg/cognition/sovereign.go`

### 26) Multi-Agent Reasoning (Swarm)
**Purpose:** Distribute reasoning across specialized agents and aggregate results via consensus.  
**References:** `pkg/core/reasoning/multiagent.go`, `pkg/core/orchestrator/`, `pkg/service/agent.go`, `docs/ROSETTA.md`

---

## Notes on DeepMind-Inspired Methods

Methods marked with an asterisk (*) are inspired by DeepMind research lines or systems (e.g., AlphaGo/AlphaZero MCTS, AlphaStar league training, and Aletheia-style verification). These are inspirations only; implementations are sovereign, Go-native, and tailored to Oricli-Alpha's architecture.
