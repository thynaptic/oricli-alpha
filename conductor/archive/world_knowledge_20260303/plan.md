# Implementation Plan: Stage 9 - Comprehensive World Knowledge

## Phase 1: Curriculum Definition & Stage Metadata
- [x] Task: Update `_stage_defs` in `scripts/train_curriculum.py` to include Stage 9 with correct metadata (name, title, datasets, age, school).
- [x] Task: Update `_auto_stage_overrides` in `scripts/train_curriculum.py` to provide safe default epochs and data percentages for the new datasets.
- [x] Task: Verify that `python3 scripts/train_curriculum.py --list-stages` correctly displays Stage 9.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Curriculum Definition & Stage Metadata' (Protocol in workflow.md)

## Phase 2: Data Pipeline Verification
- [x] Task: Write a verification script to ensure `NeuralTextGeneratorData` can successfully load and extract text from the selected datasets (Wikipedia, CommonSenseQA, FineWeb-Edu).
- [x] Task: Update `oricli_core/brain/modules/neural_text_generator_data.py` if any specific column mapping or extraction logic is missing for these new sources.
- [x] Task: Run a "dry run" of Stage 9 to verify the total character count and estimated training time.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Data Pipeline Verification' (Protocol in workflow.md)

## Phase 3: Execution & Weight Integration
- [x] Task: Implement a smoke test to verify that Stage 9 correctly loads the Stage 8 weights as its foundation.
- [x] Task: Execute a minimal training run of Stage 9 (Stage index 9) to ensure checkpoints are saved in the correct directory.
- [x] Task: Update `scripts/report_card.py` to include Stage 9 in the "Next Steps" or "Diploma" logic if necessary.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Execution & Weight Integration' (Protocol in workflow.md)

## Phase 4: Final Verification & TDD
- [x] Task: Add unit tests in `tests/test_curriculum_knowledge.py` to validate that Stage 9 is sequenced correctly and handles multi-source datasets.
- [x] Task: Run the full regression suite `python3 run_tests.py` to ensure zero impact on Stages 1-8.
- [x] Task: Conductor - User Manual Verification 'Phase 4: Final Verification & TDD' (Protocol in workflow.md)
