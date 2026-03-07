# Implementation Plan: JIT Knowledge Absorption

## Phase 1: Data Infrastructure
- [ ] Create `mavaia_core/data/jit_absorption.jsonl`.
- [ ] Implement `mavaia_core/services/absorption_service.py` to handle thread-safe writes to the buffer.

## Phase 2: Pipeline Integration
- [ ] Update `mavaia_core/brain/modules/agent_coordinator.py` to trigger the absorption service after a successful, verified web-search synthesis.
- [ ] Ensure the "Verifier Agent" has a specific instruction to flag "Learnable" content.

## Phase 3: The JIT Daemon
- [ ] Implement `scripts/mavaia_jit_daemon.py` based on the RFAL daemon template.
- [ ] Configure it to trigger `runpod_bridge.py` with the `--train-jit` flag (to be added).

## Phase 4: Bridge Integration
- [ ] Update `scripts/runpod_bridge.py` to support the `--train-jit` flag.
- [ ] Ensure the JIT buffer is synced to S3 and then to the pod for training.

## Phase 5: Verification
- [ ] Mock an unknown query.
- [ ] Verify the pipeline generates a valid JIT entry.
- [ ] Verify the daemon detects and triggers the bridge.
