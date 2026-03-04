# Implementation Plan: Benchmark Sync & Model Output Fix

This plan addresses the benchmark result retrieval inconsistency and 0.0% score issue.

## Phase 1: Diagnostics & Root Cause Analysis
- [ ] Task: Create `scripts/benchmark_diagnostic.py` to be run on the pod to inspect `LiveBench/livebench/data/`.
- [ ] Task: Analyze the model's actual answer files (jsonl) for the failed tasks to confirm if it is outputting bare HTML or some other format.
- [ ] Task: Investigate if the model's system prompt or the bridge's inference parameters were changed in a way that affects instruction following.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Diagnostics & Root Cause Analysis' (Protocol in workflow.md)

## Phase 2: Retrieval & Path Correction
- [ ] Task: Refine the `get_bench_results` function in `scripts/runpod_bridge.py` to ensure the remote `data/` folder is correctly synchronized to the local root.
- [ ] Task: Update the `remote_benchmark` logic to ensure `data/` is not prematurely deleted if results are needed.
- [ ] Task: Add a local verification step after benchmark completion to check if `data/` exists and contains files.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Retrieval & Path Correction' (Protocol in workflow.md)

## Phase 3: Parser Resilience
- [ ] Task: Update `LiveBenchResultParser` in `mavaia_core/evaluation/livebench_parser.py` to handle markdown-wrapped JSONL outputs.
- [ ] Task: Implement a more robust `clean_llm_output` or similar logic in the local parser.
- [ ] Task: Test the parser against a variety of model response formats (bare jsonl, markdown jsonl, mixed text).
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Parser Resilience' (Protocol in workflow.md)

## Phase 4: Final Verification
- [ ] Task: Execute a full remote benchmark run and verify that detailed results are pulled and correctly parsed.
- [ ] Task: Ensure that the '0 percentages' issue is resolved or clearly explained by the diagnostic output.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Final Verification' (Protocol in workflow.md)
