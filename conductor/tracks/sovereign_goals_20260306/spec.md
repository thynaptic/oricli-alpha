# Specification: Sovereign Goal Execution

## Objective
Enable Oricli-Alpha to autonomously pursue long-term objectives that persist across sessions and cluster deployments.

## Core Components

1. **The Global Objective Registry**:
   - A persistent store (`oricli_core/data/global_objectives.jsonl`) for high-level goals.
   - Each goal includes metadata: `priority`, `deadline`, `status` (pending, active, completed, failed), and `reasoning_trace`.

2. **The Sovereign Goal Daemon (`oricli_goal_daemon.py`)**:
   - A background process that orchestrates the execution of global objectives.
   - Schedules "Execution Windows" on available RunPod nodes.
   - Handles state synchronization via S3 to ensure work isn't duplicated.

3. **Persistent Plan State**:
   - Expansion of `long_horizon_planner` to support saving and resuming partial plans.
   - Checkpoint-style storage for plan progress: `Step 3 of 10 completed`.

4. **Resource Arbitration**:
   - Logic to decide when to launch a new pod vs. using an idle member of a virtual cluster for goal execution.

## Workflow
1. User provides a Sovereign Goal: "Research the competitive landscape of local-first AI backbones."
2. Oricli-Alpha records the goal in `global_objectives.jsonl`.
3. Goal Daemon:
   - Breaks goal into sub-tasks (Search, Analyze, Summarize).
   - Assigns sub-tasks to available virtual cluster pods.
   - Periodically syncs partial results to S3.
4. Final Synthesis: Aggregate all sub-task results into a comprehensive report.
