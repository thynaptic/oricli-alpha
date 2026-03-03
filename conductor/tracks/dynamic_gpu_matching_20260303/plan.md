# Implementation Plan: Dynamic GPU Matching for Training Size

## Phase 1: VRAM Estimation & Scoring Engine
- [ ] Task: Audit `scripts/runpod_bridge.py` to define the baseline memory footprints for currently supported models (character RNN, word RNN, Transformer/GPT-2).
- [ ] Task: Implement `calculate_required_vram(model_params, dataset_size, hyperparameters)` function.
- [ ] Task: Write unit tests in `tests/test_vram_estimation.py` to validate estimation across varying dataset sizes and batch sizes.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: VRAM Estimation & Scoring Engine' (Protocol in workflow.md)

## Phase 2: Selection Logic & Inventory Filtering
- [ ] Task: Update `_select_candidate_gpus` in `runpod_bridge.py` to accept the calculated VRAM floor instead of a static `--min-vram`.
- [ ] Task: Implement the "Balanced Headroom" scoring algorithm to sort filtered GPUs.
- [ ] Task: Refactor the pod creation loop to implement the "Wait and Retry" resilience logic when no candidates match.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Selection Logic & Inventory Filtering' (Protocol in workflow.md)

## Phase 3: Curriculum Integration & CLI
- [ ] Task: Update `runpod_bridge.py` to parse current curriculum stage metadata (if in `--auto` or `--curriculum` mode) to feed the estimation engine.
- [ ] Task: Enhance CLI logging to report the VRAM floor and selection rationale during the scanning phase.
- [ ] Task: Perform end-to-end dry-run verification using mock RunPod API responses to simulate supply constraints.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Curriculum Integration & CLI' (Protocol in workflow.md)
