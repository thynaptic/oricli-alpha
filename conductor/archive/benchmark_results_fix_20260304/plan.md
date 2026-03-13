# Implementation Plan: Remote Benchmark Results Retrieval & Display Fix

This plan outlines the steps to fix the issue where detailed benchmark results are not displayed or retrieved correctly by `runpod_bridge.py`.

## Phase 1: Investigation & Test Harness
- [x] Task: Manually verify the location of LiveBench results on a RunPod instance (e.g., `outputs/`, `livebench/outputs/`).
- [x] Task: Create a mock benchmark result file (JSON) to facilitate local development and testing.
- [x] Task: Write unit tests to simulate `runpod_bridge.py` encountering these files and failing to parse or display them.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Investigation & Test Harness' (Protocol in workflow.md)

## Phase 2: Core Retrieval & Parsing Fix
- [x] Task: Update the file identification logic in `scripts/runpod_bridge.py` to robustly locate remote LiveBench outputs.
- [x] Task: Implement a `LiveBenchResultParser` class in `oricli_core/evaluation/` to extract counts, categories, and percentages from JSON results.
- [x] Task: Write tests for `LiveBenchResultParser` using mock data.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Core Retrieval & Parsing Fix' (Protocol in workflow.md)

## Phase 3: Reporting & Display Implementation
- [x] Task: Implement a terminal-based reporting function that prints a summary table of the benchmark results.
- [x] Task: Update `runpod_bridge.py` to call this reporting function after successful retrieval.
- [x] Task: Implement the 'Knowledge Gap Analysis' logic to recommend datasets based on failing categories.
- [x] Task: Write end-to-end tests to verify that the full `--benchmark` flow displays the expected output in the terminal.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Reporting & Display Implementation' (Protocol in workflow.md)

## Phase 4: Final Verification
- [x] Task: Run a live remote benchmark test on a RunPod instance to confirm full end-to-end success.
- [x] Task: Verify that all result files are archived locally in `results/benchmark_<timestamp>/`.
- [x] Task: Ensure code follows Black and Ruff standards and meets >60% coverage.
- [x] Task: Conductor - User Manual Verification 'Phase 4: Final Verification' (Protocol in workflow.md)
