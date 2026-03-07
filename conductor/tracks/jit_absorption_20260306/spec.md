# Specification: JIT Knowledge Absorption

## Objective
Enable Mavaia to autonomously expand her knowledge base by learning from verified web-search results generated in response to unknown user queries.

## Components

1. **The Absorption Buffer**:
   - A `jsonl` file (`mavaia_core/data/jit_absorption.jsonl`) that stores prompt-response pairs.
   - Each entry must be verified by the `agent_coordinator` before being appended.

2. **The Verification Loop**:
   - Triggered when Mavaia uses `web_search` to answer a query.
   - An "Analyst Agent" synthesizes the search results.
   - A "Verifier Agent" checks for factual accuracy and "Thynaptic Style" compliance.

3. **The JIT Daemon (`mavaia_jit_daemon.py`)**:
   - A background process that monitors the buffer size and current time.
   - Triggers `scripts/runpod_bridge.py` when:
     - The buffer exceeds N entries.
     - A scheduled window is reached (e.g., nightly at 2 AM).

4. **Integration with Bridge**:
   - The bridge pulls the JIT buffer from S3/Local.
   - Trains a specific LoRA adapter: `jit_absorbed_knowledge`.

## Workflow
1. User asks: "What is the latest status of Project X?" (Unknown to Mavaia).
2. Mavaia: `execute_tool("web_search", ...)`
3. Pipeline: `Search -> Synthesis -> Verification`.
4. Final Answer saved to `jit_absorption.jsonl`.
5. Daemon: Detects new data -> Triggers RunPod -> Trains `jit_absorbed_knowledge` adapter.
6. Mavaia: Loads new adapter -> "I now know the status of Project X."
