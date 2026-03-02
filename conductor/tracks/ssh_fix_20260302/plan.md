# Implementation Plan: Fix SSH 255 Stabilization Errors

## Phase 1: Research & Analysis
- [ ] Task: Analyze current `_ssh_base` and `setup_pod_env` code for potential race conditions.
- [ ] Task: Verify SSH flag effectiveness (LogLevel, IdentitiesOnly, UserKnownHostsFile).
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Research & Analysis' (Protocol in workflow.md)

## Phase 2: Robustness Improvements
- [ ] Task: Refine `_ssh_base` defaults to be maximally permissive for flaky public endpoints.
- [ ] Task: Implement a 'backoff' strategy in the stabilization loop if 255 persists.
- [ ] Task: Add explicit logging for 'Connection Refused' vs 'Permission Denied' during the stabilization phase.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Robustness Improvements' (Protocol in workflow.md)

## Phase 3: Verification & Quality Gate
- [ ] Task: Verify fix by attempting to launch or resume a pod and reaching the training stage.
- [ ] Task: Ensure single-line UI remains stable and doesn't flicker during retries.
- [ ] Task: Run full test suite to ensure no regressions. **Command:** `python3 run_tests.py`
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Verification & Quality Gate' (Protocol in workflow.md)
