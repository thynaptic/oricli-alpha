# Reform Proposal: Instruction Following & Data Analysis

## 1. The Problem
The March 4th benchmark revealed a catastrophic failure (2.5% pass rate) in instruction following. 
- **Conversational Drift:** The model treats task-specific instructions (e.g., "convert HTML to JSONL") as conversation topics.
- **Architectural Neutralization:** The `CognitiveGeneratorModule` actively filters out words like "respond" and "provide," which are core to benchmark prompts.
- **Prompt Misalignment:** The system prompt emphasizes "Natural and Conversational" identity, which conflicts with "Only output the table" constraints.

## 2. Architectural Reform: `InstructionFollowingModule`
We propose a new module designed to "short-circuit" the conversational brain for high-precision tasks.

### Key Features:
- **Task Intent Detection:** Recognizes keywords like "convert," "format," "JSONL," "CSV," and "Table."
- **Formatting Lock:** When active, it suppresses `CognitiveGenerator`'s personality filters and "Anti-Echo" logic.
- **Raw Execution Mode:** Allows the model to output structured data without conversational preambles (e.g., "I'd say...", "Here is your table:").

## 3. System Prompt Reform
Update `mavaia_system_prompt_builder.py` to support a `TASK_EXECUTION` mode.

### Implementation:
- **Priority Override:** If a task is detected, the prompt shifts from "Great Chat Partner" to "Precise Data Engineer."
- **Negative Constraints:** Explicitly instruct the model: "DO NOT include conversational filler," "DO NOT acknowledge the instruction," "ONLY output the requested format."

## 4. Curriculum Reform: Stage 8 Alignment
The current `knowledge_world_dense` training may have diluted the model's ability to follow rigid instructions.

### Strategy:
- **Negative Constraint Training:** Use DPO (Direct Preference Optimization) to penalize conversational filler in task-based responses.
- **Format Enforcement:** Inject 10,000+ examples of HTML-to-JSONL and CSV-to-Markdown conversions into the Stage 8 dataset.
- **Dataset Target:** `Intel/orca_dpo_pairs` and a custom synthesized "Constraint Dataset."

## 5. Next Steps
1. Implement the `InstructionFollowingModule` prototype.
2. Update the `SystemPromptBuilder` with `TASK_EXECUTION` logic.
3. Run a targeted benchmark on `data_analysis/tablereformat` to verify improvement.
