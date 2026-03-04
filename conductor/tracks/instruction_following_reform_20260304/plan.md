# Implementation Plan: Instruction Following Reform (Data Deep Dive)

This plan outlines the forensic analysis steps to understand the 2.5% benchmark failure.

## Phase 1: forensic Data Analysis
- [ ] Task: Create `scripts/forensic_benchmark.py` to compare `model_answer` vs `ground_truth` for `data_analysis/tablereformat`.
- [ ] Task: Quantify the failure modes (e.g., % of answers that are bare HTML, % that are empty, % that are malformed JSON).
- [ ] Task: Conductor - User Manual Verification 'Phase 1: forensic Data Analysis' (Protocol in workflow.md)

## Phase 2: Root Cause Investigation
- [ ] Task: Audit `mavaia_core/brain/modules/cognitive_generator.py` to see if it filters out the JSONL formatting instructions.
- [ ] Task: Test the model directly with a "raw" prompt (bypassing the brain modules) to see if the underlying weights are capable of the task.
- [ ] Task: Analyze the impact of the `mavaia_system_prompt_builder` on instruction following.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Root Cause Investigation' (Protocol in workflow.md)

## Phase 3: Reform Proposal
- [ ] Task: Draft a design for a dedicated `InstructionFollowingModule` that handles formatting tasks with high priority.
- [ ] Task: Propose updates to the curriculum (Stage 8: Alignment) to specifically target these failures.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Reform Proposal' (Protocol in workflow.md)
