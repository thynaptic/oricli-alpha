# Specification: Fix Persistent SSH 255 Stabilization Errors

## Overview
Resolve the constant SSH exit code 255 errors occurring during the initial "true" connection check in `runpod_bridge.py`. These errors are currently blocking the initialization of new pods.

## Functional Requirements
- **Stable Initial Handshake**: Refine `_ssh_base` and `setup_pod_env` to handle the immediate 255 errors that occur when the `ssh.runpod.io` proxy is reachable but the pod routing is not yet active.
- **Resilient Retry Logic**: Implement a more patient stabilization phase that prioritizes connection success, potentially including increased delays or backoff between the very first attempts.
- **Proxy-Specific Tuning**: Further tune SSH flags specifically for the RunPod proxy to avoid premature connection closures.

## Non-Functional Requirements
- **Stability First**: Prioritize successful connection over rapid failure.
- **UI Integrity**: Retain the single-line, non-scrolling "Stabilizing SSH" status display.

## Acceptance Criteria
- [ ] `runpod_bridge.py` successfully completes the "true" connection check without immediate exit.
- [ ] The stabilization counter correctly increments and eventually leads to a "Connection stable!" state.
- [ ] Environment setup proceeds only after the SSH link is verified as reliably open.

## Out of Scope
- Modifying RunPod infrastructure or base images.
- Changing training or distillation logic.
