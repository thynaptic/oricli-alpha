# MCTS Reasoning Engine

Oricli-Alpha employs a **Monte-Carlo Tree Search (MCTS)** engine for advanced reasoning, decision-making, and planning. This allows the system to simulate future states and choose the optimal path before committing to an answer.

## Architecture

The system is split into two primary modules:
1.  **`mcts_search_engine`**: The low-level algorithmic core (UCB1, rollout, backprop).
2.  **`mcts_reasoning`**: The high-level orchestrator that connects MCTS to the Memory Graph and Cognitive Generator.

## Core Components

### 1. UCB1 Selection
Upper Confidence Bound applied to Trees (UCB1) balances **Exploration** (trying new paths) vs. **Exploitation** (following promising paths).

$$ UCB1 = \frac{w_i}{n_i} + C \sqrt{\frac{\ln N}{n_i}} $$

### 2. Rollout / Simulation
Instead of a simple heuristic, the engine performs "rollouts" using the `cognitive_generator` or `tot_thought_generator`. It simulates the conversation N turns into the future to see if a path leads to a successful resolution.

### 3. Backpropagation
Success/Failure signals from rollouts are propagated back up the tree to update the value estimates of parent nodes.

## Integration with Memory
The `mcts_reasoning` module integrates with the **Memory Graph**:
*   **Context Retrieval**: Before starting the search, it pulls relevant long-term memories to seed the root node.
*   **Graph Traversal**: In some modes, the MCTS tree can map directly to nodes in the Memory Graph, allowing for "reasoning over the graph".

## Operations

*   **`execute_mcts`**: Performs the full search.
    *   *Inputs*: `query`, `context`, `configuration` (depth, rollouts, C-param).
    *   *Outputs*: `result` (best path), `confidence`, `metadata`.
*   **`should_activate`**: Heuristic check to see if the query is complex enough to warrant the computational cost of MCTS.

## Port Origin
This engine is a Python port of the original `MCTSSearchEngine.swift`, adapted for the Oricli-Alpha modular architecture.
