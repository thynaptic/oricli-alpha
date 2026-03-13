# Implementation Plan: Sovereign Goal Execution

## Phase 1: Objective Infrastructure
- [ ] Create `oricli_core/data/global_objectives.jsonl`.
- [ ] Implement `oricli_core/services/goal_service.py` for thread-safe objective management.
- [ ] Update `long_horizon_planner` to support `load_plan` and `save_plan`.

## Phase 2: Goal Daemon Implementation
- [ ] Create `scripts/oricli_goal_daemon.py`.
- [ ] Implement the scheduling logic: Check for pending goals and available virtual cluster capacity.
- [ ] Integrate with `runpod_bridge.py` to trigger goal-specific execution passes.

## Phase 3: S3 Sync for Goals
- [ ] Update the `runpod_bridge` watchdog to sync the `global_objectives` and active plan states to S3.
- [ ] Ensure pods pull the latest plan state before resuming execution.

## Phase 4: Integration & UX
- [ ] Add a top-level command or API endpoint to submit global objectives.
- [ ] Implement a "Status Report" generator that summarizes progress on all active sovereign goals.

## Phase 5: Verification
- [ ] Submit a multi-step research goal.
- [ ] Verify the daemon launches a pod, executes the first 2 steps, syncs to S3, and resumes correctly after a simulated restart.
