# Specification: Curriculum Electives via LoRA

## Overview
Implement an "Electives" system within the Mavaia curriculum training framework (`scripts/train_curriculum.py`). This feature allows developers to train specialized reasoning "modes" (e.g., Coding, Business, Medical) as independent LoRA adapters. These adapters build upon a shared foundation model without modifying it directly, preventing catastrophic forgetting and allowing for a modular, multi-mode cognitive architecture.

## Functional Requirements
1.  **Elective Selection**: Add an `--elective` flag to `scripts/train_curriculum.py` that accepts one or more stage names or indices to be treated as specialized electives.
2.  **LoRA Enforcement**: Stages designated as electives must automatically enable LoRA fine-tuning (`--lora`) in the underlying `train_neural_text_generator.py` script.
3.  **Unique Artifact Suffixes**: Elective adapters must be saved with unique file suffixes (e.g., `adapter_coding.safetensors`) instead of overwriting the base model checkpoints.
4.  **Base Model Logic**:
    -   **Default (Intermediate Base)**: Electives should, by default, use the output of the most recent non-elective stage as their starting foundation.
    -   **Manual Override**: Add an `--elective-base` flag to allow users to manually specify a starting model path for elective training.
5.  **Curriculum Flow**: Non-elective stages proceed sequentially as usual. Elective stages fork from the designated base and produce independent artifacts.

## Non-Functional Requirements
-   **Local-First**: All model operations must remain local-first and compatible with the existing RunPod/S3 orchestration.
-   **Compatibility**: The new flags must not break standard sequential curriculum training.
-   **Type Safety**: All new logic in `train_curriculum.py` must use Python type hints.

## Acceptance Criteria
-   Executing a curriculum run with `--elective coding` successfully trains the "coding" stage using LoRA.
-   The resulting artifact for the elective is identifiable by a unique suffix or name.
-   Manual base override via `--elective-base` successfully initializes the LoRA adapter from the specified path.
-   Verification via `run_tests.py` shows no regressions in core curriculum logic.

## Out of Scope
-   Dynamic multi-adapter switching during inference (handled in a separate track).
-   Merging elective LoRAs back into the primary foundation model.
-   Modifying the character/word RNN models (LoRA electives are for transformer architectures).
