# Specification: Synthetic Dream State

## Objective
Enable Oricli-Alpha to autonomously innovate and consolidate knowledge by simulating a "dream state" during idle periods, where she finds novel connections between disparate pieces of information.

## Core Components

1. **The Dream Daemon (`oricli_dream_daemon.py`)**:
   - Monitors system load and user activity.
   - Triggers the "Dream Sequence" when the system has been idle for a configurable period.

2. **The Consolidation Engine**:
   - Randomly samples nodes from the `memory_graph`.
   - Pulls recent facts from `jit_absorption.jsonl`.
   - Feeds pairs of disparate facts to the `analogical_reasoning` module to find potential correlations.

3. **The Insight Registry**:
   - A persistent store (`oricli_core/data/synthetic_insights.jsonl`) for new connections found during dreaming.
   - Each insight is scored by the `meta_evaluator`.

4. **Integration with RFAL**:
   - High-scoring insights are automatically converted into synthetic lessons for the next training pass.

## Workflow
1. System is idle for 30 minutes.
2. Dream Daemon starts.
3. Consolidation Engine picks:
   - Fact A: "Project X uses a new local-first indexing method."
   - Fact B: "The Roman aqueduct system used gravity-fed decentralized routing."
4. `analogical_reasoning` finds a connection: "Decentralized data routing in local-first systems can be optimized using gravity-like priority flow."
5. `meta_evaluator` scores it 0.85 (High).
6. Insight is saved and queued for training.
