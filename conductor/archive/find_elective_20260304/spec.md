# Specification: Dataset Discovery Elective (--find-elective)

## Overview
Add a dynamic dataset discovery mechanism to the curriculum training pipeline. This feature enables users to specify a topic, idea, or category (e.g., "cybersecurity", "modern slang", "scientific logic") and have the system automatically find the best matching dataset from multiple sources and integrate it as a new curriculum elective stage.

## Functional Requirements
- **Flag Addition**: Add `--find-elective [query]` to `scripts/train_curriculum.py` and `scripts/runpod_bridge.py`.
- **Multi-Source Search**:
    - **Hugging Face**: Search for relevant datasets via the `huggingface_hub` or `datasets` API.
    - **Wikipedia**: Search for relevant articles/categories.
    - **Internet Archive**: Search for relevant texts/collections.
- **Ranking Engine**: Implement a combined scoring system that prioritizes:
    - **Relevance**: Semantic or lexical match to the query.
    - **Popularity**: Download counts, likes, or citations.
    - **Data Quality/Size**: Preference for clean, usable text volumes.
- **User Interaction Modes**:
    - **Interactive (Default)**: Display the top 3-5 matches with metadata (name, source, size, description) and wait for user selection.
    - **Automatic**: Add `--auto-select` flag to bypass interaction and pick the #1 ranked result.
- **Curriculum Integration**:
    - Automatically generate a new "Elective Stage" configuration for the selected dataset.
    - Target LoRA adapter training (standard for electives) to avoid base model drift.
    - Immediately start training the new stage within the current execution context.

## Non-Functional Requirements
- **Rate Limiting**: Gracefully handle API rate limits for external sources.
- **Data Sovereignty**: Ensure discovered dataset URLs/IDs are logged for reproducibility.

## Acceptance Criteria
- Running `python scripts/train_curriculum.py --find-elective "quantum physics"` displays a list of datasets.
- Selecting a dataset successfully scaffolds a new elective stage.
- Training completes and produces a valid LoRA adapter.
- The feature works seamlessly over the RunPod bridge (`scripts/runpod_bridge.py`).

## Out of Scope
- Automated dataset cleaning/scrubbing beyond standard Oricli-Alpha preprocessing.
- Training multiple discovered datasets in a single command pass.
