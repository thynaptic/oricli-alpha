# Implementation Plan: Dataset Discovery Elective

## Phase 1: Search Infrastructure & Ranking
- [ ] Task: Implement `DatasetSearch` service in `mavaia_core/data/search.py`.
    - [ ] Integrate Hugging Face `huggingface_hub` for dataset discovery.
    - [ ] Integrate Wikipedia search via `wikipedia` package.
    - [ ] Integrate Internet Archive search via `internetarchive` package.
- [ ] Task: Implement the Scoring & Ranking Engine.
    - [ ] Define weighted scoring for relevance, popularity, and data size.
    - [ ] Implement result normalization across different sources.
- [ ] Task: Write unit tests for `DatasetSearch` and Ranking logic.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Search Infrastructure & Ranking' (Protocol in workflow.md)

## Phase 2: Curriculum Pipeline Integration
- [ ] Task: Add CLI arguments to `scripts/train_curriculum.py`.
    - [ ] Add `--find-elective [query]` and `--auto-select`.
- [ ] Task: Implement Selection Logic.
    - [ ] Implement `interactive_select()` helper for CLI display and input.
    - [ ] Implement `auto_inject_stage()` to generate a curriculum stage from search results.
- [ ] Task: Integrate search flow into `main()` loop of `train_curriculum.py`.
- [ ] Task: Write integration tests for the discovery-to-training flow.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Curriculum Pipeline Integration' (Protocol in workflow.md)

## Phase 3: RunPod Bridge Support
- [ ] Task: Add `--find-elective` and `--auto-select` to `scripts/runpod_bridge.py`.
- [ ] Task: Update bridge argument forwarding logic.
- [ ] Task: Ensure interactive selection works over SSH/Bridge or defaults gracefully to auto-select if remote.
- [ ] Task: Perform end-to-end dry-run verification on a remote pod.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: RunPod Bridge Support' (Protocol in workflow.md)
