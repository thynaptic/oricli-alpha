# Specification: Remote Benchmarking Mode for RunPod Bridge

## Overview
Implement a dedicated `--benchmark` mode in `scripts/runpod_bridge.py`. This feature enables standalone evaluation of Mavaia models on remote GPUs, allowing for high-performance benchmarking (e.g., LiveBench) without requiring a local GPU. Results are automatically synchronized back to local and S3 storage.

## Functional Requirements
1.  **Standalone CLI Mode**: Add a `--benchmark` flag to `runpod_bridge.py` that skips the training flow and executes a specified evaluation script.
2.  **Generic Benchmarking Interface**: 
    -   Introduce a `--bench-script` argument (default: `LiveBench/livebench/evaluate.py`) to allow for different benchmarks.
    -   Provide a `--bench-args` argument to forward specific flags to the evaluation script.
3.  **Hardware Lifecycle**: 
    -   Reuse the "Dynamic GPU Matching" logic to select an appropriate node based on the model being evaluated.
    -   Automatically terminate the pod after benchmarking completes (configurable via `--terminate`).
4.  **Automated Data Sync**:
    -   Detect new result files (e.g., `livebench_results_*.json`).
    -   Pull results back to the local `results/` or root directory.
    -   Mirror results to the configured S3 bucket for persistent tracking.
5.  **Environment Preparation**: Ensure benchmarking dependencies (like `LiveBench` itself) are correctly installed or synced during the pod setup phase.

## Non-Functional Requirements
-   **Observability**: Real-time progress streaming from the remote benchmark process to the local CLI.
-   **Local-First Verification**: The bridge must verify the existence of the model weights to be benchmarked before launching the pod.

## Acceptance Criteria
-   Executing `python3 scripts/runpod_bridge.py --benchmark --pod-id <id>` successfully runs LiveBench on the specified pod.
-   Results are visible in the local repository after the command exits.
-   The bridge correctly handles S3 uploads for the benchmarking artifacts.

## Out of Scope
-   Automated multi-node benchmarking.
-   Visualization of benchmark results (handled by `scripts/report_card.py`).
