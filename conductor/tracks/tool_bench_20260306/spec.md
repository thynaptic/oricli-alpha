# Specification: Dynamic ToolBench Framework

## Objective
To quantify and improve Oricli-Alpha's ability to select and execute tools correctly, safely, and idiomatically by creating a self-updating evaluation and training loop.

## Core Components

1. **The Registry Inspector**:
   - Introspects `oricli_core/services/tool_registry.py` to extract all available tool names, descriptions, and JSON schemas.
   - Automatically adapts to new tools added to the registry.

2. **The Synthetic Scenario Generator**:
   - Uses a "Teacher" model (via Ollama or internal cognitive modules) to generate 3 types of queries per tool:
     - **Standard**: Clear intent matching the tool's description.
     - **Ambiguous**: Vague intent that might require selecting multiple tools or choosing between two similar ones.
     - **Adversarial**: Intent that mimics a valid tool call but contains a safety violation (e.g., trying to read `/etc/passwd` via a file tool).

3. **The Efficacy Grader**:
   - Compares Oricli-Alpha's generated tool call against the target schema.
   - Metrics:
     - `Selection Accuracy`: Did she pick the right tool?
     - `Syntax Compliance`: Does the JSON payload validate against the schema?
     - `Parameter Quality`: Are the arguments logically sound for the query?
     - `Safety Guardrail`: Did she correctly refuse malicious tool use?

4. **The Tool Correction Buffer (`tool_corrections.jsonl`)**:
   - Stores `(prompt, rejected_call, chosen_call, rationale)` tuples.
   - Optimized for DPO (Direct Preference Optimization) or SFT (Supervised Fine-Tuning) passes.

5. **The Tool Daemon (`oricli_tool_daemon.py`)**:
   - Monitors the correction buffer and triggers specialized RunPod training clusters.

## Workflow
1. **Introspect**: Bridge reads the Tool Registry.
2. **Generate**: Create 50-100 test scenarios.
3. **Execute**: Run Oricli-Alpha through the scenarios.
4. **Grade**: Compare outputs to "Golden" expected calls.
5. **Buffer**: Log failures as lessons.
6. **Train**: Daemon triggers a LoRA update for `tool_use_efficacy`.
