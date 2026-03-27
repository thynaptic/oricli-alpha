# MCTS Reasoning & Strategic Planning

**Location:** `pkg/cognition/mcts.go`, `pkg/cognition/adaptive.go`, `pkg/core/reasoning/mcts.go`  
**Entry point:** `MCTSEngine.SearchV2(ctx, draftAnswer) → MCTSResult`  
**Adaptive budgeting:** `adaptive.go` — `DetermineBudget()`, `AnalyzeComplexity()`, `AdaptiveBudget.ScaledNumPredict()`

Oricli-Alpha's MCTS engine is a compiled Go implementation. It treats each candidate answer as a tree node, explores branches via LLM callbacks, and selects the path that maximizes a dual-eval score (primary + adversarial). The engine is the cognitive backbone for complex reasoning, multi-step problem solving, and long-horizon planning.

---

## 1. Adaptive Budgeting & Complexity Detection

The engine utilizes a high-precision complexity detector to optimize compute allocation.
*   **Deep Reasoning Signals**: Analyzes 9 factors including Uncertainty, Sequential Decision-Making, Game Theory, and Multi-Path Reasoning.
*   **Dynamic Scaling**: Automatically adjusts `Iterations` (50-200), `RolloutDepth`, and `MaxConcurrency` based on the calculated complexity score.
*   **Exploration Modulation**: Dynamically updates the Exploration Constant (`UCB1C`). High exploration benefit queries (e.g., "what if" scenarios) trigger wider tree searches.
*   **Early Convergence**: Monitors branch confidence during search. Terminates early if a path reaches >95% confidence, preserving compute resources.

---

## 2. Long-Horizon Strategic Planning

The engine extends MCTS into autonomous goal execution through the Strategic Orchestrator.
*   **Strategic DAGs**: Decomposes complex goals into Directed Acyclic Graphs with explicit dependency tracking.
*   **Self-Healing Strategy**: Detects step failures during execution and autonomously generates recovery sub-plans to work around obstacles.
*   **Bounty Economy**: Assigns MetacogToken bounties to execution steps, ensuring accountability within the Hive Swarm.

---

## 3. Architecture

```
SearchV2(ctx, draftAnswer)
     │
     ├─ DetermineBudget()           Analyze query complexity & exploration benefit
     │    └─ defined in pkg/cognition/adaptive.go — returns AdaptiveBudget
     ├─ ApplyToConfig()             Update Iterations, Depth, and UCB1C
     ├─ build root ThoughtNode
     │
     ├─ [MaxConcurrency > 1]        → runParallelSearch() (worker pool)
     └─ [MaxConcurrency == 1]       → sequential loop
          │
          └─ for each iteration:
               convergence check        Exit if best-node confidence > ConvergenceThreshold (field, not method)
               selectAndMaybeExpand()   UCB1 / PUCT + RAVE + VirtualVisits + transposition table
               evaluateNode()           VN pre-screen → LLM dual-eval → RAVE table update
               backpropagate()          update visits, cumulative score, RAVE table
```

> **Note:** `CheckConvergence()` is not a method in the codebase. The convergence threshold is the `ConvergenceThreshold` field on `MCTSConfig`. Termination is handled inline per-iteration in `SearchV2`.

---

## 4. Core Selection Components — UCB1 + PUCT + RAVE

`selectionScore(child, parent, cfg)` computes the branch score used to descend the tree.

**UCB1 mode** (`Strategy = "ucb1"`):
```
score = Q + UCB1C · √(ln N / n)
```

**PUCT mode** (default):
```
score = Q + PriorWeight · p · √N / (1 + n)
```

Where:
- `Q` = average backpropagated score (blended with RAVE when enabled)
- `p` = prior from PolicyNetwork (or uniform `1/BranchFactor`)
- `N` = parent visits, `n` = child visits
- Nodes with `VirtualVisits > 0` (in-flight evaluations) return `-Inf` to prevent double-selection

---

## 5. Enhancements

### RAVE — Rapid Action Value Estimation
Global action-value table keyed by FNV-1a hash. `selectionScore` blends the node's local Q with the global RAVE estimate:
`β = √(k / (3N + k))` where `k` is `RAVEEquivalence`.

### Policy Network — Branch Priors
`PolicyNetwork` interface assigns priors before expansion. The `HeuristicPolicyNetwork` scores branches on 8 factors (length, markers, specificity, etc.) to bias search toward structured reasoning.

### Value Network — Pre-Screening
Optional lightweight model that estimates branch quality.
- `< AcceptBelow`: use VN score directly.
- `≥ EscalateAbove`: escalate to full dual-LLM evaluation.

### Transposition Table
Within-search evaluation cache keyed on FNV-1a hash. Avoids redundant evaluation of identical branches reached via different paths.

---

## 6. Tree Diagnostics

`DiagnoseTree(root *ThoughtNode) → TreeDiagnostics` performs a BFS walk and computes:
- Total nodes, max depth, avg branch factor.
- Pruned/terminal counts.
- Depth histogram and average score by depth.
- Top 10 nodes by confidence.

Export methods: `.JSON()`, `.Summary()`, and `.Mermaid()` (flowchart visualization).
