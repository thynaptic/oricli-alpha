# Specification: Metacognitive Sentience Layer

## Objective
To provide Mavaia with internal self-regulation capabilities based on DBT (Dialectical Behavior Therapy) and CBT (Cognitive Behavioral Therapy), enabling her to detect and recover from cognitive volatility autonomously.

## Core Components

1. **The Cognitive Sentinel (`metacognitive_sentinel.py`)**:
   - The "Executive Function" that monitors execution traces and subconscious entropy.
   - Triggers self-regulation skills when volatility thresholds are exceeded.

2. **Emotional Ontology (`emotional_ontology.py`)**:
   - Maps raw system metrics (latency, token repetition, vector variance) to "Cognitive States" (Focused, Scattered, Looping, Stagnant).

3. **DBT/CBT Heuristics**:
   - **Radical Acceptance**: If a reasoning path fails or becomes circular, Mavaia accepts the state as a dead end, drops the current "un-useful" bias, and resets the reasoning node.
   - **Wise Mind Consensus**: A decision-making logic that balances the "Reasonable Mind" (pure logic/modules) with the "Emotional Mind" (subconscious bias/learned priors).
   - **Distress Tolerance (Resource Gating)**: Throttles execution or shifts to "Safety Templates" when entropy is too high.

4. **The Reset Trigger**:
   - A mechanism to "flush" recent noise from the Subconscious Field and force the Pathway Architect to generate a fresh, diverse DAG.

## Technical Architecture
- **Volatility Metrics**: Tracking repeated token bigrams, cosine similarity variance in thought chains, and recursive depth.
- **Heuristic Engine**: A rule-based and symbolic logic layer that modulates the `cognitive_generator` loop.

## Workflow
1. Mavaia begins generating a complex response.
2. The Sentinel detects high bigram repetition (looping) in the first 2 steps.
3. Skill Triggered: **Radical Acceptance**.
4. Action:
   - Current thought chain is truncated.
   - Subconscious bias associated with the loop is dampened.
   - `pathway_architect` is called with `volatility_flag=True` to build a new recovery path.
5. Mavaia resumes with a fresh perspective: "I realized I was over-analyzing that specific path; let's look at this from another angle..."
