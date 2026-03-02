# Implementation Plan: Stage 3 Capability Phase (HotpotQA)

## Phase 1: Environment & Data Validation
- [ ] Task: Verify HotpotQA accessibility on RunPod.
    - [ ] Run `scripts/test_hf_load.py` with `hotpot_qa:distractor`.
    - [ ] Confirm text extraction yields high-quality multi-hop questions.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Environment & Data Validation' (Protocol in workflow.md)

## Phase 2: Training Implementation
- [ ] Task: Execute Stage 3 training via `runpod_bridge.py`.
    - [ ] Launch with Stage 2 model path as `--model-name`.
    - [ ] Monitor Sentinel logs for `[Mavaia-Sentinel]` events.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Training Implementation' (Protocol in workflow.md)

## Phase 3: Artifact Verification
- [ ] Task: Validate synced Stage 3 weights.
    - [ ] Check local `models/neural_text_generator_remote/` for new curriculum folder.
    - [ ] Run a sample generation using Stage 3 weights to verify "Capability" boost.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Artifact Verification' (Protocol in workflow.md)
