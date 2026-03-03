# Implementation Plan: Smart Resume & Auto-Gap Detection

## Phase 1: Logic & Discovery Infrastructure
- [x] Task: Implement a weight discovery helper in `scripts/train_curriculum.py`.
    - [x] Add logic to check `latest_run.txt`.
    - [x] Implement scanning of the `curriculum` model directory for stage-specific `config.json` or `run_config.json` files.
    - [x] (Optional) Add a basic S3 check if credentials are present.
- [x] Task: Create a `get_stage_performance(run_dir)` function to extract the last recorded loss.
- [x] Task: Define the `SmartResumePolicy` class to encapsulate threshold comparisons and scaling math.
- [~] Task: Conductor - User Manual Verification 'Phase 1: Logic & Discovery Infrastructure' (Protocol in workflow.md)

## Phase 2: Curriculum Integration
- [x] Task: Add the `--smart-resume` argument to the `argparse` setup in `train_curriculum.py`.
- [x] Task: Modify the main execution loop in `train_curriculum.py`.
    - [x] Integrate the discovery and performance check before starting each stage.
    - [x] Implement the "Skip", "Retouch", and "Full" decision logic.
    - [x] Ensure `data_pct` and `epochs` are dynamically scaled for "Retouch" passes.
- [x] Task: Update the `_write_progress` logic to record why a stage was skipped or retouched.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Curriculum Integration' (Protocol in workflow.md)

## Phase 3: Validation & TDD
- [x] Task: Write unit tests in `tests/test_smart_resume.py`.
    - [x] Test the performance extraction with mock `run_config.json` files.
    - [x] Test the `SmartResumePolicy` decision matrix (Skip vs Retouch vs Full).
- [x] Task: Run a mock curriculum run with pre-existing "low-loss" checkpoints to verify skipping behavior.
- [x] Task: Run full regression suite `python3 run_tests.py` to ensure zero impact on standard sequential training.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Validation & TDD' (Protocol in workflow.md)
