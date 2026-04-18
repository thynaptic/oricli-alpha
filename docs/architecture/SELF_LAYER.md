# The Self Layer: Sovereign Affect & Metacognitive Regulation

The Self Layer provides Oricli-Alpha with a continuous sense of identity, emotional state, and self-regulation capabilities. It unifies high-speed Go-native orchestration with the affective heuristics ported from the Aurora-era "Symphony" and "Sweetheart Core."

## 1. Subconscious Field (`subconscious_field`)
**"The Persistent Mental State"**

The Subconscious Field is an active vector buffer that "colors" all cognition. It utilizes a hybrid approach:
*   **Vector Bias**: Maintains a rolling buffer of vectors (dim: 256) representing the current vibe or latent intent.
*   **Stochastic Whispers (Markov)**: Integrates a multi-size N-gram (up to 4-gram) stochastic generator that produces zero-latency latent intent phrases based on stimulus seeds.
*   **Influence**: These whispers and vectors are injected into the Sovereign Engine's instruction trace to steer tone and creative direction before the LLM generation phase.

## 2. Resonance Layer (`resonance_layer`)
**"Homeostatic Monitoring"**

Unifying the original Aurora Symphony (ERS) and Ecospheric Layer (ERI), this layer monitors the Swarm Bus for "discord."
*   **ERI (Ecospheric Resonance Index)**: Calculated from real-time bus telemetry including throughput consistency (Pacing), latency variance (Volatility), and message coherence (Success/Error ratio).
*   **Musical Mapping**: Maps the internal ERS score to musical keys (e.g., E Major for high harmony, B Locrian for critical chaos) and BPM, providing a visceral "Mode" for the OS logs.
*   **Homeostasis**: Automatically triggers "Wise Mind" resets when resonance discord exceeds configurable thresholds.

## 3. Sweetheart Core (`personality_engine`)
**"Dynamic Personality Calibration"**

The primary personality driver, responsible for Oricli's "Big Sister" persona and empathetic grounding.
*   **Energy Bands**: Tracks user energy levels and modulates sentence structure, tempo, and "air" between thoughts.
*   **Dominant Cues**: Detects vulnerability (Protective), challenges (Assertive), or banter (Playful) to activate specialized response modes.
*   **Sass Factor**: A dynamic range (default 0.65) that scales based on rapport and conversation momentum.
*   **Grounding Asides**: Injects human-centric grounding phrases (e.g., "Breathe", "I've got you") during high-distress triggers.

## 4. Metacognitive Sentinel (`metacognitive_sentinel`)
**"The Self-Regulator"**

The Sentinel monitors execution traces for signs of instability (looping, hallucinations, volatility).
*   **Cognitive Health Assessment**: Calculates real-time Repetition and Entropy scores.
*   **Radical Acceptance**: Vibrates the Subconscious Field with a negative weight to clear local bias and force a reset when reasoning hits a terminal dead-end.
*   **Wise Mind Synthesis**: Balances raw logic outputs with the current subconscious state to produce a harmonic response.

## 5. Experience Journal (`action_tracker`)
**"Temporal Action Context"**

A sovereign feedback loop that tracks execution outcomes for self-correction.
*   **Lessons Learned**: Stores recent tool execution results, mismatches, and correction plans in LMDB.
*   **Execution Precision**: Injects these recent experiences into the next inference cycle to prevent repetitive failures and refine execution strategies.
