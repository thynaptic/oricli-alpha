# Implementation Plan: Remote Benchmarking Mode

## Phase 1: Argument & State Infrastructure
- [x] Task: Add `--benchmark`, `--bench-script`, and `--bench-args` to `runpod_bridge.py`.
- [x] Task: Implement `remote_benchmark` function in `runpod_bridge.py` to handle the execution logic.
- [x] Task: Modify the `main` control flow to branch into the benchmark path when the flag is present.
- [~] Task: Conductor - User Manual Verification 'Phase 1: Argument & State Infrastructure' (Protocol in workflow.md)

## Phase 2: Execution & Result Sync
- [x] Task: Enhance `ensure_oricli_installed` or create a new `ensure_bench_ready` to handle `LiveBench` dependencies on the pod.
- [x] Task: Implement the `get_bench_results` function to identify and pull specific result patterns from the pod.
- [x] Task: Integrate S3 upload logic for benchmarking results.
- [~] Task: Conductor - User Manual Verification 'Phase 2: Execution & Result Sync' (Protocol in workflow.md)

## Phase 3: Final Verification & TDD
- [x] Task: Write unit tests in `tests/test_bridge_benchmark.py` to validate argument parsing and benchmark command generation.
- [x] Task: Perform a dry-run benchmark against a mock pod to verify result synchronization paths.
- [x] Task: Run full regression suite `python3 run_tests.py` to ensure training flows are unaffected.
- [~] Task: Conductor - User Manual Verification 'Phase 3: Final Verification & TDD' (Protocol in workflow.md)
