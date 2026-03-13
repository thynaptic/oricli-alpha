# Implementation Plan: Stage 3 Capability Phase (HotpotQA)

## Phase 1: Environment & Data Validation
- [x] Task: Verify HotpotQA accessibility on RunPod.
    - [x] Run `scripts/test_hf_load.py` with `hotpot_qa:distractor`.
    - [x] Confirm text extraction yields high-quality multi-hop questions.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Environment & Data Validation' (Protocol in workflow.md)

## Phase 2: Training Implementation
- [x] Task: Execute Stage 3 training via `runpod_bridge.py`.
    - [x] Launch with Stage 2 model path as `--model-name`.
    - [x] Monitor Sentinel logs for `[Oricli-Alpha-Sentinel]` events.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Training Implementation' (Protocol in workflow.md)

## Phase 3: Artifact Verification
- [x] Task: Validate synced Stage 3 weights.
    - [x] Check local `models/neural_text_generator_remote/` for new curriculum folder.
    - [x] Run a sample generation using Stage 3 weights to verify "Capability" boost.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Artifact Verification' (Protocol in workflow.md)
