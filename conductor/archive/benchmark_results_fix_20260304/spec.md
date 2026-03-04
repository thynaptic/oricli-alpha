# Specification: Remote Benchmark Results Retrieval & Display Fix

## 1. Overview
The current `@scripts/runpod_bridge.py --benchmark` command fails to provide detailed results or percentages after a LiveBench run. While the bridge indicates a successful run and result retrieval, no meaningful output (e.g., test summaries, pass/fail percentages, or knowledge gap analysis) is displayed in the terminal, and no local files appear in expected directories.

## 2. Goals
- **Successful Retrieval:** Ensure all LiveBench output files (JSON, logs, etc.) generated on the remote RunPod are correctly identified, bundled, and transferred to the local machine.
- **Detailed Terminal Reporting:** Display a comprehensive summary of the benchmark results directly in the terminal (stdout) upon completion.
- **Knowledge Gap Analysis:** Implement or expose a mechanism to derive 'what datasets Mavaia needs next' from the benchmark results and display this insight.

## 3. Functional Requirements
- **Remote File Identification:** Update `runpod_bridge.py` to robustly locate LiveBench results on the pod (typically in `outputs/` or a LiveBench-specific directory).
- **Result Parsing:** Implement a parser for the retrieved LiveBench result files (e.g., JSON) to extract passing/failing counts and percentages for each category.
- **Summary Display:** Print a formatted table or summary to the terminal, including:
    - List of tests ran.
    - Pass/fail count and percentage per category.
    - Overall performance score.
- **Knowledge Gap Engine:** Correlate failing categories with suggested datasets from the Mavaia curriculum or external sources (e.g., 'Requires more Wikipedia-based reasoning for Stage 5').

## 4. Acceptance Criteria
- Running `python3 scripts/runpod_bridge.py --benchmark` results in a detailed table printed to stdout after the 'Results retrieved' message.
- The terminal output includes specific percentages (e.g., 'Coding: 85% Pass').
- A 'Knowledge Gap Analysis' section is visible with at least one dataset recommendation based on failures.
- Verification that result files are actually present in a local `results/benchmark_<timestamp>/` directory for archival.

## 5. Out of Scope
- Integration with the Flask UI (results will remain CLI-focused for this track).
- Modifications to the LiveBench core logic (we focus on the bridge and reporting).
