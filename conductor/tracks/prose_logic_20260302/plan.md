# Implementation Plan: Stage 2.5 — Prose Modernization & Basic Logic Refinement

## Phase 1: Data Strategy & Acquisition
- [x] Task: Identify and validate a "Modern Prose" dataset.
    - [x] Run `scripts/test_hf_load.py` with proposed candidate (e.g., `HuggingFaceH4/no_robots`).
    - [x] Verify dataset quality and extraction logic.
- [x] Task: Define the "Basic Logic" subset for refinement.
    - [x] Create a filtered subset of Orca-Math or similar logic dataset.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Data Strategy & Acquisition' (Protocol in workflow.md)

## Phase 2: Training & Monitoring
- [x] Task: Configure `train_curriculum.py` for Stage 2.5.
    - [x] Add Stage 2.5 to the curriculum definition.
    - [x] Set appropriate `stop_at_loss` and `min_improvement` for this phase.
- [x] Task: Execute Stage 2.5 training.
    - [x] Run `runpod_bridge.py` targeting Stage 2.5.
    - [x] Monitor Sentinel logs for specific "Prose" vs "Logic" performance indicators.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Training & Monitoring' (Protocol in workflow.md)

## Phase 3: Verification & Polishing
- [x] Task: Verify Model Outputs.
    - [x] Perform comparative sampling between Stage 2 and Stage 2.5.
    - [x] Confirm "Prose Modernization" goals are met.
- [x] Task: Finalize Stage 2.5 Checkpoint.
    - [x] Sync all weights and logs.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Verification & Polishing' (Protocol in workflow.md)
