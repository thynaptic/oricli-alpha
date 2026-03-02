# Implementation Plan: Stage 2.5 — Prose Modernization & Basic Logic Refinement

## Phase 1: Data Strategy & Acquisition
- [ ] Task: Identify and validate a "Modern Prose" dataset.
    - [ ] Run `scripts/test_hf_load.py` with proposed candidate (e.g., `HuggingFaceH4/no_robots`).
    - [ ] Verify dataset quality and extraction logic.
- [ ] Task: Define the "Basic Logic" subset for refinement.
    - [ ] Create a filtered subset of Orca-Math or similar logic dataset.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Data Strategy & Acquisition' (Protocol in workflow.md)

## Phase 2: Training & Monitoring
- [ ] Task: Configure `train_curriculum.py` for Stage 2.5.
    - [ ] Add Stage 2.5 to the curriculum definition.
    - [ ] Set appropriate `stop_at_loss` and `min_improvement` for this phase.
- [ ] Task: Execute Stage 2.5 training.
    - [ ] Run `runpod_bridge.py` targeting Stage 2.5.
    - [ ] Monitor Sentinel logs for specific "Prose" vs "Logic" performance indicators.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Training & Monitoring' (Protocol in workflow.md)

## Phase 3: Verification & Polishing
- [ ] Task: Verify Model Outputs.
    - [ ] Perform comparative sampling between Stage 2 and Stage 2.5.
    - [ ] Confirm "Prose Modernization" goals are met.
- [ ] Task: Finalize Stage 2.5 Checkpoint.
    - [ ] Sync all weights and logs.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Verification & Polishing' (Protocol in workflow.md)
