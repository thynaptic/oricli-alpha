# Implementation Plan: Fix Persistent SSH 255 Errors

## Phase 1: SSH Flag & Timeout Tuning
- [x] Task: Update `_ssh_base` to remove restrictive flags (`BatchMode`, `ConnectionAttempts`) that cause immediate 255 on proxy hiccups.
- [x] Task: Increase `ConnectTimeout` and tune `ServerAlive` intervals for high-latency proxy links.
- [x] Task: Conductor - User Manual Verification 'Phase 1: SSH Flag & Timeout Tuning' (Protocol in workflow.md)

## Phase 2: Stabilization Logic Refinement
- [x] Task: Modify the initial connection check in `setup_pod_env` to be more patient with proxies (increased initial delay).
- [x] Task: Implement a cleaner error-capture mechanism that distinguishes between "Port not open" and "Proxy closed connection".
- [x] Task: Ensure the single-line UI correctly reflects the "Stabilizing..." state without flickering during retries.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Stabilization Logic Refinement' (Protocol in workflow.md)

## Phase 3: Final Verification
- [x] Task: End-to-end test by launching a fresh pod and reaching the "Connection stable!" state.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Final Verification' (Protocol in workflow.md)
