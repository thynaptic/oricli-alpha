# Specification: Benchmark Sync & Model Output Fix

## 1. Overview
The current `@scripts/runpod_bridge.py --benchmark` flow results in incomplete result retrieval and 0.0% scores for model evaluations, particularly in data analysis tasks. Users report that the model appears to be outputting HTML instead of the requested JSONL, and results are not consistently synchronized from the remote pod.

## 2. Goals
- **Robust Result Retrieval:** Ensure the `data/` directory and its contents are consistently pulled from the remote pod to the local project root.
- **Improved Parsing:** Enhance the parser to handle cases where the model might include extraneous text or formatting around its JSONL output.
- **On-Pod Diagnostics:** Provide a script to verify benchmark status and result existence directly on the pod before retrieval.
- **Root Cause Analysis (Model):** Investigate if recent curriculum training (e.g., Stage 9) has caused a regression in instruction-following for formatting tasks.

## 3. Functional Requirements
- **Update `runpod_bridge.py`:** Refine `rsync` patterns and ensure the `data/` folder is correctly mapped to the local project root.
- **Diagnostic Script:** Create `scripts/benchmark_diagnostic.py` to be executed on the pod to check for generated results and their format.
- **Enhanced `LiveBenchResultParser`:** Update the parser to be more resilient to variations in LLM output (e.g., handling markdown blocks or leading/trailing text).
- **Automated Verification:** Add a step to verify the local `data/` structure immediately after retrieval.

## 4. Acceptance Criteria
- `python3 scripts/runpod_bridge.py --benchmark` successfully pulls the `data/` directory from the pod.
- The `LiveBenchResultParser` correctly processes model judgments even if extraneous text is present.
- A diagnostic report can be generated from the pod showing exactly what files exist in `LiveBench/livebench/data/`.
- Clear identification of why the model is failing the HTML-to-JSONL conversion task (e.g., system prompt mismatch or weight regression).

## 5. Out of Scope
- Re-training the model (this track focuses on diagnosis and parsing/retrieval).
- Modifications to the LiveBench core grading logic (unless strictly necessary for parsing resilience).
