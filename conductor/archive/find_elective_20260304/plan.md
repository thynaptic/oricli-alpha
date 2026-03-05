# Implementation Plan: Dataset Discovery Elective

## Phase 1: Search Infrastructure & Ranking
- [x] Task: Implement `DatasetSearch` service in `mavaia_core/data/search.py`.
    - [x] Integrate Hugging Face `huggingface_hub` for dataset discovery.
    - [x] Integrate Wikipedia search via `wikipedia` package.
    - [x] Integrate Internet Archive search via `internetarchive` package.
- [x] Task: Implement the Scoring & Ranking Engine.
    - [x] Define weighted scoring for relevance, popularity, and data size.
    - [x] Implement result normalization across different sources.
- [x] Task: Write unit tests for `DatasetSearch` and Ranking logic.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Search Infrastructure & Ranking' (Protocol in workflow.md)

## Phase 2: Curriculum Pipeline Integration
- [x] Task: Add CLI arguments to `scripts/train_curriculum.py`.
    - [x] Add `--find-elective [query]` and `--auto-select`.
- [x] Task: Implement Selection Logic.
    - [x] Implement `interactive_select()` helper for CLI display and input.
    - [x] Implement `auto_inject_stage()` to generate a curriculum stage from search results.
- [x] Task: Integrate search flow into `main()` loop of `train_curriculum.py`.
- [x] Task: Write integration tests for the discovery-to-training flow.
- [~] Task: Conductor - User Manual Verification 'Phase 2: Curriculum Pipeline Integration' (Protocol in workflow.md)

## Phase 3: RunPod Bridge Support
- [x] Task: Add `--find-elective` and `--auto-select` to `scripts/runpod_bridge.py`.
- [x] Task: Update bridge argument forwarding logic.
- [x] Task: Ensure interactive selection works over SSH/Bridge or defaults gracefully to auto-select if remote.
- [x] Task: Perform end-to-end dry-run verification on a remote pod.
- [x] Task: Conductor - User Manual Verification 'Phase 3: RunPod Bridge Support' (Protocol in workflow.md)
