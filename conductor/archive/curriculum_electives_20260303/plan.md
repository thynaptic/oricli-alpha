# Implementation Plan: Curriculum Electives via LoRA

## Phase 1: Argument Infrastructure & Parsing
- [x] Task: Audit `scripts/train_curriculum.py` to identify the most robust point for elective interception.
- [x] Task: Add `--elective` and `--elective-base` arguments to `train_curriculum.py` using `argparse`.
- [x] Task: Implement internal logic to categorize selected stages into "Base" (sequential) and "Elective" (forked) buckets.
- [x] Task: Update `_write_progress` and `curriculum_progress.json` structure to track elective status.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Argument Infrastructure & Parsing' (Protocol in workflow.md)

## Phase 2: Elective Execution Logic
- [x] Task: Modify `_run_stage` in `train_curriculum.py` to support elective behavior.
    - [x] Implement logic to automatically append `--lora` to `extra_args` if the stage is an elective.
    - [x] Implement base model selection: use `--elective-base` if provided, otherwise default to the output of the last completed non-elective stage.
- [x] Task: Update `train_neural_text_generator.py` to support a new `--adapter-name` flag for unique LoRA artifact naming.
- [x] Task: Update the `save_model` operation in `oricli_core/brain/modules/neural_text_generator.py` to utilize the custom adapter name when saving LoRA weights.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Elective Execution Logic' (Protocol in workflow.md)

## Phase 3: Verification & TDD
- [x] Task: Write unit tests in a new `tests/test_curriculum_electives.py` to validate elective stage parsing and base model selection.
- [x] Task: Create a mock curriculum run script to verify that elective stages produce separate artifacts with unique suffixes.
- [x] Task: Run full regression suite `python3 run_tests.py` to ensure zero impact on standard curriculum flows.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Verification & TDD' (Protocol in workflow.md)
