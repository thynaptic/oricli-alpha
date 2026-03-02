# Specification: Fix SSH 255 Stabilization Errors

## Overview
Address and resolve persistent SSH exit code 255 errors that occur when the `runpod_bridge.py` script attempts to stabilize connections to newly launched or resumed RunPod instances. These errors prevent environment setup and training from proceeding.

## Functional Requirements
- **Reliable Connection Logic**: Refine the logic in `setup_pod_env` and `_run_ssh` to better handle instances where the SSH service is reported as "up" but is not yet accepting connections.
- **Graceful Retries**: Implement a more robust retry mechanism that differentiates between transient networking issues and definitive connection failures.
- **Diagnostic Transparency**: Ensure that if an SSH 255 persists beyond the standard stabilization window, clear diagnostic information is surfaced.

## Non-Functional Requirements
- **UI Integrity**: Maintain the single-line, non-scrolling progress display during the stabilization phase.
- **Robustness**: SSH configurations should minimize interference from local user SSH configs or agents.

## Acceptance Criteria
- [ ] `runpod_bridge.py` successfully completes the "stabilize ssh" phase and proceeds to environment setup on a live pod.
- [ ] No manual intervention (like editing `.ssh/known_hosts`) is required to clear 255 errors.
- [ ] The "Stabilizing SSH connection" counter correctly reflects attempts and eventually succeeds.

## Out of Scope
- Changes to the RunPod API itself or the base container images.
- Modifications to the training logic (`train_neural_text_generator.py`).
