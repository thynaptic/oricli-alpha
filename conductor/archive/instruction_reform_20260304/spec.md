# Specification: High-Precision Instruction Following Reform

## 1. Overview
Following the catastrophic 2.5% benchmark failure, this track implements an architectural reform to enable high-precision task execution. We are introducing a dedicated `InstructionFollowingModule` and a `TASK_EXECUTION` system prompt mode to bypass conversational drift for rigid formatting and data analysis requirements.

## 2. Goals
- **Eliminate Conversational Drift:** Ensure formatting tasks (e.g., HTML to JSONL) are executed without preambles, filler, or refusal.
- **Hard Routing:** Bypass the standard conversational cognitive loop when a formatting task is detected.
- **Minimalist Prompting:** Implement a "Task Only" system prompt that suppresses the model's conversational identity.

## 3. Functional Requirements
- **`InstructionFollowingModule`**:
    - **Intent Detection**: Triggers on keywords including: `json`, `jsonl`, `csv`, `xml`, `yaml`, `markdown table`, `reformat`, `convert`, `extract`, `simplify`, `parse`, `map`, `no filler`, `raw only`, `strict schema`, `without explanation`, `calculate`, `evaluate`, `regex`, `schema`, `ground truth`, `{`, `[`, `<html>`.
    - **Formatting Lock**: Prevents the `CognitiveGenerator` from filtering or regenerating output if it contains instruction-like words.
- **`SystemPromptBuilder` Update**:
    - Implement `TASK_EXECUTION` mode.
    - Provide a minimalist, instruction-focused prompt that overrides the standard "Natural and Conversational" identity.
- **`CognitiveGenerator` Routing**:
    - Implement a "Hard Bypass" logic that routes detected task intents directly to the `InstructionFollowingModule`.
    - Disable fallbacks to the conversational brain for these tasks.

## 4. Acceptance Criteria
- Running the `data_analysis/tablereformat` benchmark shows a significant improvement in pass rate.
- Forensic analysis of outputs confirms the removal of conversational filler (e.g., "I'm here to help," "I'd say").
- Verification that prompts starting with `json` or `<html>` skip the standard reasoning loop.

## 5. Out of Scope
- Re-training model weights (this is a software/orchestration fix).
- UI changes.
