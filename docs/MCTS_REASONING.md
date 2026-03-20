# MCTS Reasoning Engine

**Location:** `pkg/cognition/`  
**Entry point:** `MCTSEngine.SearchV2(ctx, draftAnswer) → MCTSResult`

Oricli-Alpha's MCTS engine is a compiled Go implementation. It treats each candidate answer as a tree node, explores branches via LLM callbacks, and selects the path that maximizes a dual-eval score (primary + adversarial). The engine is the cognitive backbone for complex reasoning, planning, and multi-step problem solving.

---

## Architecture

```
SearchV2(ctx, draftAnswer)
     │
     ├─ normalizedConfig()          clamp/default all config fields
     ├─ build root ThoughtNode
     │
     ├─ [MaxConcurrency > 1]        → runParallelSearch()   (worker pool)
     └─ [MaxConcurrency == 1]       → sequential loop
          │
          └─ for each iteration:
               selectAndMaybeExpand()   UCB1 / PUCT + RAVE + VirtualVisits
               evaluateNode()           transposition check → VN pre-screen → LLM dual-eval
               backpropagate()          update visits, cumulative score, RAVE table
```

---

## Core Components

### 1. Selection — UCB1 + PUCT + RAVE

`selectionScore(child, parent, cfg)` computes the branch score used to descend the tree.

**UCB1 mode** (`Strategy = "ucb1"`):
```
score = Q + C · √(ln N / n)
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

### 2. RAVE — Rapid Action Value Estimation

Global action-value table keyed by FNV-1a hash of the answer text. Every `backpropagate` call updates the RAVE table. `selectionScore` blends the node's local Q with the global RAVE estimate:

```
β = √(k / (3N + k))          β→1 at N=0, β→0 at N→∞
blended_Q = (1-β)·Q + β·RAVE_Q
```

**Config:** `RAVEEquivalence float64` — equivalence parameter `k`. `0` disables RAVE.  
**Default:** `300`

### 3. Policy Network — Branch Priors

`PolicyNetwork` interface assigns a prior probability to each candidate branch before expansion. The `HeuristicPolicyNetwork` (built-in, no ML model required) scores branches on 8 factors:

| Factor | Signal |
|---|---|
| Length vs parent | More detail → higher prior |
| Step markers | "first", "step 1", "then" → structured reasoning |
| Specificity | Numbers, proper nouns, named entities |
| Sentence structure | Multi-sentence answers |
| Query overlap | Word overlap with original query |
| Hedge penalty | "maybe", "perhaps", "I think" → lower prior |
| All-caps words | Emphasis / named entities |
| Parenthetical depth | Extra context → higher prior |

Scores are normalised across the full sibling set using min-max scaling with a 0.10 floor (worst branch always gets ≥10% prior). Falls back to uniform on any error.

**Config:** `PolicyNet *PolicyNetConfig` — `nil` = uniform priors (disabled).

### 4. Value Network — Pre-Screening

Optional lightweight model that estimates branch quality before committing to a full dual-LLM evaluation.

Three zones:
- `score < AcceptBelow` → skip LLM entirely, use VN score
- `AcceptBelow ≤ score < EscalateAbove` → use VN score directly
- `score ≥ EscalateAbove` → escalate to full LLM eval

**Config:** `ValueNet *ValueNetConfig`

### 5. Transposition Table

Within-search evaluation cache keyed on FNV-1a hash of the answer text. Avoids re-evaluating identical branches that appear via different tree paths.

**Config:** `MaxTableSize int` — `0` = default 256, `-1` = disabled.

### 6. Virtual Loss

Increments `VirtualVisits` on a selected node before evaluation so parallel workers don't select the same in-flight node. Decremented after backpropagation.

**Config:** `VirtualLoss float64` — auto-set to `1.0` when `MaxConcurrency > 1` and `VirtualLoss ≤ 0`.

### 7. Pruning

Branches scoring below `PruneThreshold` are marked `Pruned = true` and excluded from future selection. A configurable kill-switch (`KillSwitchThreshold`) immediately terminates a branch mid-evaluation.

### 8. Parallel Leaf Selection

When `MaxConcurrency > 1` (and `Deterministic = false`), `runParallelSearch` spawns a worker pool. Each worker runs an independent select → eval → backprop loop. Workers use a `sync.RWMutex` on the tree and atomic counters for coordination.

**Blocking strategy:** When all children of a node are in-flight (`bestScore == -Inf`), a worker receives `nil` from `selectAndMaybeExpand`. It checks `activeEvals`:
- `activeEvals > 0` → other workers are evaluating; yield via `runtime.Gosched()` and retry (budget not consumed)
- `activeEvals == 0` → tree permanently exhausted; exit

**Config:** `MaxConcurrency int`, `VirtualLoss float64`

---

## Configuration Reference

```go
MCTSConfig{
    // Core search parameters
    Iterations     int     // total evaluations (default: 12)
    BranchFactor   int     // max children per node (default: 3)
    RolloutDepth   int     // max tree depth (default: 3)
    ExplorationC   float64 // UCB1 exploration constant (default: 1.414)
    Strategy       string  // "puct" (default) or "ucb1"

    // Parallelism
    MaxConcurrency int     // worker pool size; 1 = sequential (default: 1)
    VirtualLoss    float64 // anti-collision penalty (default: 0.2; auto 1.0 in parallel)
    Deterministic  bool    // force MaxConcurrency=1 for reproducible results

    // Pruning
    PruneThreshold    float64 // prune branches below this score (default: 0.2)
    KillSwitchThreshold float64

    // Enhancements
    RAVEEquivalence float64        // RAVE k parameter (0 = disabled; default: 300)
    PolicyNet       *PolicyNetConfig  // nil = uniform priors
    ValueNet        *ValueNetConfig   // nil = full LLM eval always
    MaxTableSize    int            // transposition table cap (-1 = disabled)
    PriorWeight     float64        // PUCT prior coefficient (default: 1.0)

    // Timeouts
    EvalTimeout  time.Duration
    TotalTimeout time.Duration
}
```

---

## Result

```go
MCTSResult{
    Answer          string        // best answer found
    BestScore       float64       // highest score achieved
    IterationsRun   int           // actual iterations completed
    ExpandedNodes   int
    PrunedNodes     int
    TranspositionHits int         // LLM calls avoided via cache
    ValueNetHits    int           // evals short-circuited by value network
    RAVETableSize   int           // unique answers in RAVE table
    PolicyNetPriorizations int    // branches with non-uniform priors
    Root            *ThoughtNode  // full tree for diagnostics
}
```

---

## Tree Diagnostics

`DiagnoseTree(root *ThoughtNode) → TreeDiagnostics` performs a BFS walk and computes:

- Total nodes, max depth, avg branch factor
- Pruned/terminal counts
- Depth histogram and average score by depth
- Top 10 nodes by confidence

**Export methods:**
- `.JSON() ([]byte, error)` — structured JSON snapshot
- `.Summary() string` — human-readable text with depth bar
- `.Mermaid() string` — Mermaid flowchart (top 20 nodes; parallelogram for pruned/terminal)

---

## Callbacks (External LLM Hooks)

```go
MCTSCallbacks{
    ProposeBranches func(ctx, parentAnswer string, n int) ([]string, error)
    EvaluatePath    func(ctx, candidate string) (MCTSEvaluation, error)
    AdversarialEval func(ctx, candidate string) (MCTSEvaluation, error)  // optional red-team
}
```

`EvaluatePath` and `AdversarialEval` are the only points where external LLM calls occur. All other logic is pure Go.

---

## Quick Start

```go
eng := &cognition.MCTSEngine{
    Config: cognition.MCTSConfig{
        Iterations:      20,
        BranchFactor:    3,
        RolloutDepth:    3,
        MaxConcurrency:  4,
        RAVEEquivalence: 300,
        PolicyNet: &cognition.PolicyNetConfig{
            Network: cognition.HeuristicPolicyNetwork{},
        },
    },
    Callbacks: cognition.MCTSCallbacks{
        ProposeBranches: myLLM.ProposeBranches,
        EvaluatePath:    myLLM.EvaluatePath,
        AdversarialEval: myLLM.AdversarialEval,
    },
}

result, err := eng.SearchV2(ctx, draftAnswer)
diag := cognition.DiagnoseTree(result.Root)
fmt.Println(diag.Summary())
```
