# Specification: Strategic Pre-Execution Planner

## Objective
To provide Oricli-Alpha with a high-fidelity "Planning Mode" that explicitly simulates and validates different reasoning paths before committing to a specific execution graph.

## Core Concepts

1. **Approach Generation (Tree of Thoughts - ToT)**:
   - When given a complex goal, the planner uses ToT to branch out into multiple possible high-level strategies (e.g., "Strategy A: Code-first", "Strategy B: Research-first").
   - This creates a search space of potential plans.

2. **Simulation & Validation (MCTS)**:
   - For each generated strategy, the planner uses MCTS to simulate potential outcomes and look ahead.
   - It assigns a "Strategic Confidence Score" to each branch based on simulated probability of success and resource efficiency.

3. **Step Decomposition (Chain of Thought - CoT)**:
   - The winning strategy (highest MCTS score) is then expanded via CoT into a detailed, step-by-step cognitive plan.
   - These steps serve as the "Logical Blueprint" for the `pathway_architect`.

## Technical Architecture

### Module: `strategic_planner.py`
- Inherits from `BaseBrainModule`.
- Depends on `tree_of_thought`, `mcts_search_engine`, and `chain_of_thought`.

### Workflow
1. **Goal Received**: User submits a complex task (e.g., "Audit this repo and propose a 3-stage migration plan").
2. **Phase 1 (ToT)**: `strategic_planner` calls `tree_of_thought` to generate 3 diverse approaches.
3. **Phase 2 (MCTS)**: Calls `mcts_search_engine` to perform rollouts for each approach.
4. **Phase 3 (CoT)**: Calls `chain_of_thought` to refine the best approach into 5-10 discrete steps.
5. **Output**: A `StrategicPlan` object that is passed to `cognitive_generator` and `pathway_architect`.

## Advantages
- **Reduces Cognitive Volatility**: By "thinking before acting," the system is less likely to start down a path that leads to a hallucination or loop.
- **Improved Alignment**: The user can see the plan *before* the final answer is generated, allowing for "Strategic Interception" if needed.
