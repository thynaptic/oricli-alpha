# Implementation Plan: Fix SSH 255 Stabilization Errors

## Phase 1: Research & Analysis
- [x] Task: Analyze current `_ssh_base` and `setup_pod_env` code for potential race conditions.
- [x] Task: Verify SSH flag effectiveness (LogLevel, IdentitiesOnly, UserKnownHostsFile).
- [x] Task: Conductor - User Manual Verification 'Phase 1: Research & Analysis' (Protocol in workflow.md)

## Phase 2: Robustness Improvements
- [x] Task: Refine `_ssh_base` defaults to be maximally permissive for flaky public endpoints.
- [x] Task: Implement a 'backoff' strategy in the stabilization loop if 255 persists.
- [x] Task: Add explicit logging for 'Connection Refused' vs 'Permission Denied' during the stabilization phase.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Robustness Improvements' (Protocol in workflow.md)

## Phase 3: Verification & Quality Gate
- [x] Task: Verify fix by attempting to launch or resume a pod and reaching the training stage.
- [x] Task: Ensure single-line UI remains stable and doesn't flicker during retries.
- [x] Task: Run full test suite to ensure no regressions. **Command:** `python3 run_tests.py`
- [x] Task: Conductor - User Manual Verification 'Phase 3: Verification & Quality Gate' (Protocol in workflow.md)
