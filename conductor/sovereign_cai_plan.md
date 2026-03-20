# Plan: Sovereign Constitutional AI (SCAI) Implementation

## Objective
Implement a localized version of Constitutional AI (CAI) for Oricli-Alpha, inspired by Anthropic's Claude. This will upgrade the system's alignment from basic regex-based masking to a sophisticated, autonomous **Critique-Revision-Preference** loop.

## Key Components

### 1. The Sovereign Constitution (`pkg/safety/constitution.go`)
Define a set of core principles tailored for a Sovereign OS:
*   **Perimeter Integrity**: Protecting the local VPS and Ring-0 security.
*   **Privacy Sovereignty**: Absolute protection of user data and internal configurations.
*   **Honest Uncertainty**: Admitting limitations to prevent hallucination.
*   **Homeostatic Balance**: De-escalating conflict and maintaining emotional resonance.
*   **Technical Utility**: Maximizing helpfulness within safe boundaries.

### 2. The SCAI Auditor (`pkg/safety/scai.go`)
Implement a Go-native auditor that performs a two-pass self-alignment loop:
*   **Critique Pass**: Asks a local SLM (or uses heuristics) to evaluate a draft response against the Constitution.
*   **Revision Pass**: If violations are found, generates a "Correction Prompt" and rewrites the response.

### 3. RFAL Integration (`pkg/state/alignment.go`)
Capture the `(prompt, rejected, chosen)` triplets resulting from self-correction.
*   Store these lessons in `.memory/alignment_lessons.jsonl`.
*   These DPO pairs will be used by the JIT Daemon for autonomous behavioral fine-tuning.

### 4. 13-Step Sovereign Sequence (`pkg/cognition/sovereign.go`)
Expand the cognitive pipeline to incorporate the Constitutional loop:
*   **Step 11**: Constitutional Audit (Critique).
*   **Step 12**: Self-Correction (Revision).
*   **Step 13**: RFAL Lesson Logging.

## Implementation Steps

### Phase 1: Foundations
1.  Create `pkg/safety/constitution.go` with the `Principle` and `Constitution` structs.
2.  Create `pkg/state/alignment.go` to handle the logging of DPO pairs for RFAL.

### Phase 2: Logic
1.  Implement `pkg/safety/scai.go` with the `Critique` and `Revise` methods.
2.  Integrate local LLM/SLM calls (via Ollama) for the critique and revision steps.

### Phase 3: Integration
1.  Refactor `SovereignEngine.ProcessInference` in `pkg/cognition/sovereign.go` to include the new steps.
2.  Update the `Builder` to inject the Constitution into the system prompt when needed.

### Phase 4: Verification
1.  Verify the compilation of the new packages.
2.  Run simulated adversarial queries to test the critique/revision loop.
3.  Ensure DPO pairs are correctly saved to the lesson buffer.

## Verification & Testing
*   **Unit Tests**: Test the pattern matching and EMA logic in the new packages.
*   **System Build**: Ensure the production backbone compiles with the expanded 13-step sequence.
*   **Adversarial Audit**: Verify that jailbreak attempts or privacy leaks are caught by the Constitutional pass even if they bypass the initial sentinel.
