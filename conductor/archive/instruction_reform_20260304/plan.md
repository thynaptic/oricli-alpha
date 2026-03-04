# Implementation Plan: High-Precision Instruction Following Reform

This plan implements the architectural and prompting changes required to fix catastrophic instruction-following failures.

## Phase 1: New Module - `InstructionFollowingModule` [988f896]
- [x] Task: Create `mavaia_core/brain/modules/instruction_following.py` with intent detection and raw execution logic.
- [x] Task: Write unit tests for intent detection using the approved keyword list.
- [x] Task: Conductor - User Manual Verification 'Phase 1: New Module' (Protocol in workflow.md)

## Phase 2: System Prompt Reform [f0a0eca]
- [x] Task: Update `mavaia_core/brain/modules/mavaia_system_prompt_builder.py` to include `TASK_EXECUTION` mode.
- [x] Task: Implement the minimalist, "Identity Suppression" prompt for task mode.
- [x] Task: Write unit tests to verify the task prompt is correctly generated when the flag is passed.
- [x] Task: Conductor - User Manual Verification 'Phase 2: System Prompt Reform' (Protocol in workflow.md)

## Phase 3: Cognitive Generator Integration [7904732]
- [x] Task: Modify `mavaia_core/brain/modules/cognitive_generator.py` to implement the "Hard Bypass" for detected tasks.
- [x] Task: Update the `CognitiveGenerator` to disable conversational filtering/anti-echo for high-precision tasks.
- [x] Task: Write integration tests to ensure a task prompt (e.g., "convert html to json") correctly bypasses the conversational loop.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Cognitive Generator Integration' (Protocol in workflow.md)

## Phase 4: Final Validation
- [x] Task: Run the `data_analysis/tablereformat` benchmark and verify improvement via `scripts/forensic_benchmark.py`.
- [x] Task: Verify that standard conversational queries still function normally through the standard pipeline.
- [x] Task: Conductor - User Manual Verification 'Phase 4: Final Validation' (Protocol in workflow.md)
