# Specification: Smart Resume & Auto-Gap Detection

## Overview
Implement an intelligent curriculum resumption system via a new `--smart-resume` flag in `scripts/train_curriculum.py`. This system will automatically determine whether to skip a training stage, "retouch" it with scaled data, or perform a full run based on the detected loss of existing weights across local and remote storage.

## Functional Requirements
1.  **Argument Implementation**: Add `--smart-resume` to `scripts/train_curriculum.py`.
2.  **Multi-Source weight Discovery**: 
    -   Verify weights by checking the `latest_run.txt` pointer.
    -   Scan local checkpoint directories for stage-specific results.
    -   Fallback to remote storage (S3) if local weights are missing.
3.  **Intelligent Gap Detection**:
    -   Parse the `eval_loss` or `loss` from the discovered weight metadata/logs.
    -   Define a "Success Threshold" (e.g., Loss < 0.05).
    -   Compare current model performance against the threshold for each curriculum stage.
4.  **Dynamic Stage Behavior**:
    -   **Skip**: If detected loss is well below the threshold, mark the stage as acquired and move to the next.
    -   **Retouch**: If loss is marginal (e.g., 0.05 < Loss < 0.15), trigger a "retouch" pass using **Dynamic Scaling** (automatically reducing `data_percentage` or `epochs`).
    -   **Full Run**: If no weights are found or loss is high, proceed with the full stage.

## Non-Functional Requirements
-   **Transparency**: The script must log the detection results (e.g., "Stage 3 acquired (Loss: 0.03). Skipping...").
-   **Local-First**: Prioritize local weight validation to minimize network overhead.

## Acceptance Criteria
-   Running `train_curriculum.py --smart-resume` correctly skips stages that have already reached the target loss.
-   Stages with marginal loss are re-run with significantly reduced data/epochs.
-   The system correctly handles cases where weights exist on S3 but not locally.
