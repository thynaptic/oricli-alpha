# Implementation Plan: Smart Resume & Auto-Gap Detection

## Phase 1: Logic & Discovery Infrastructure
- [ ] Task: Implement a weight discovery helper in `scripts/train_curriculum.py`.
    - [ ] Add logic to check `latest_run.txt`.
    - [ ] Implement scanning of the `curriculum` model directory for stage-specific `config.json` or `run_config.json` files.
    - [ ] (Optional) Add a basic S3 check if credentials are present.
- [ ] Task: Create a `get_stage_performance(run_dir)` function to extract the last recorded loss.
- [ ] Task: Define the `SmartResumePolicy` class to encapsulate threshold comparisons and scaling math.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Logic & Discovery Infrastructure' (Protocol in workflow.md)

## Phase 2: Curriculum Integration
- [ ] Task: Add the `--smart-resume` argument to the `argparse` setup in `train_curriculum.py`.
- [ ] Task: Modify the main execution loop in `train_curriculum.py`.
    - [ ] Integrate the discovery and performance check before starting each stage.
    - [ ] Implement the "Skip", "Retouch", and "Full" decision logic.
    - [ ] Ensure `data_pct` and `epochs` are dynamically scaled for "Retouch" passes.
- [ ] Task: Update the `_write_progress` logic to record why a stage was skipped or retouched.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Curriculum Integration' (Protocol in workflow.md)

## Phase 3: Validation & TDD
- [ ] Task: Write unit tests in `tests/test_smart_resume.py`.
    - [ ] Test the performance extraction with mock `run_config.json` files.
    - [ ] Test the `SmartResumePolicy` decision matrix (Skip vs Retouch vs Full).
- [ ] Task: Run a mock curriculum run with pre-existing "low-loss" checkpoints to verify skipping behavior.
- [ ] Task: Run full regression suite `python3 run_tests.py` to ensure zero impact on standard sequential training.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Validation & TDD' (Protocol in workflow.md)
