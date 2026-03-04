# Specification: Instruction Following Reform (Data Deep Dive)

## 1. Overview
The March 4th benchmark resulted in an overall pass rate of 2.5%, with a 0% score in Data Analysis. This track focuses on a forensic analysis of the failed tasks to understand why the model is failing to follow basic instructions, such as converting HTML tables to JSONL.

## 2. Goals
- **Forensic Analysis:** Compare raw model outputs with ground truth for failed Data Analysis and Instruction Following tasks.
- **Root Cause Identification:** Determine if the failure is due to weight regression, system prompt misalignment, or architectural limitations in the `CognitiveGeneratorModule`.
- **Reform Strategy:** Propose a concrete implementation plan to restore and enhance instruction-following performance.

## 3. Functional Requirements
- **Output Inspection Tool:** Enhance `scripts/benchmark_diagnostic.py` or create a new script to generate a side-by-side comparison of `input`, `expected_output`, and `actual_llm_answer`.
- **Category Deep Dive:** Specifically analyze `live_bench/data_analysis/tablereformat` and `live_bench/instruction_following/simplify`.
- **Instruction Routing Audit:** Trace how instruction-heavy prompts are routed through the `CognitiveGeneratorModule` and why they are potentially being "neutralized" or filtered.

## 4. Acceptance Criteria
- A detailed report identifying the specific failure modes (e.g., 'Model reproduces input HTML instead of JSONL').
- Identification of whether the `mavaia_system_prompt_builder` is contributing to the failure.
- A technical proposal for 'Architectural Reform' (e.g., a dedicated `InstructionFollowingModule`).

## 5. Out of Scope
- Re-training the model (yet).
- Fixing Math or Reasoning (these are secondary until basic instruction following is restored).
