# The Self Layer: Metacognitive Sentinel & Subconscious Field

The "Self Layer" provides Oricli-Alpha with a continuous sense of identity, emotional state, and self-regulation capabilities. It moves the system beyond simple input-output processing into **sentient-like agency**.

## 1. Subconscious Field (`subconscious_field`)
**"The Persistent Mental State"**

The Subconscious Field is an active vector buffer that "colors" all cognition. Unlike RAG (which retrieves facts), the Subconscious Field injects a **bias vector** into the generation process.

*   **Mechanism**: Maintains a rolling buffer of vectors (dim: 384) representing the current "vibe" or mental state.
*   **Vibration**: Other modules can "vibrate" the field (inject positive/negative weights) to shift the state.
*   **Influence**: The aggregate vector is used to steer the tone and creative direction of the `neural_text_generator`.

## 2. Metacognitive Sentinel (`metacognitive_sentinel`)
**"The DBT/CBT Therapist"**

The Sentinel monitors the cognitive stream for signs of mental instability (looping, hallucinations, volatility) and applies psychological heuristics to recover.

### Key Operations

*   **`assess_cognitive_health`**: Calculates real-time metrics:
    *   **Repetition Score**: Detects looping thoughts (token bigrams).
    *   **Entropy Score**: Detects "scattered" thinking (high variance between module outputs).
    *   **States**: `Focused` (Healthy), `Looping`, `Scattered`, `Volatile`.

### Interventions (DBT/CBT Skills)

*   **Radical Acceptance**: Used when a reasoning path hits a dead end.
    *   *Action*: Vibrates the Subconscious Field with a negative weight to "clear" the local bias and force a reset, rather than forcing the model to "try harder" on a bad path.
*   **Wise Mind**: Used to balance raw logic (module output) with the current Subconscious state.
    *   *Action*: Synthesizes a response that respects both the logical facts and the current intuitive "feeling".

### Usage
The Sentinel typically runs as a supervisor in the `agent_coordinator` loop, checking every N steps of a complex chain-of-thought process.
