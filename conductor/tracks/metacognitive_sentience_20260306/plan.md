# Implementation Plan: Metacognitive Sentience Layer

## Phase 1: Emotional Ontology & Metrics
- [ ] Implement `mavaia_core/brain/modules/emotional_ontology.py`.
- [ ] Define the mapping between system telemetry (latency, entropy, repetition) and cognitive states.
- [ ] Implement the `assess_state` operation.

## Phase 2: The Cognitive Sentinel
- [ ] Implement `mavaia_core/brain/modules/metacognitive_sentinel.py`.
- [ ] Build the heuristic triggers for Radical Acceptance and Wise Mind.
- [ ] Implement the `apply_skill` operation.

## Phase 3: Cognitive Generator Integration
- [ ] Update `mavaia_core/brain/modules/cognitive_generator.py` to check with the Sentinel between reasoning steps.
- [ ] Implement the "Reset and Reroute" logic in the generator loop.

## Phase 4: Subconscious & Architect Integration
- [ ] Update `subconscious_field.py` to support "dampening" specific bias clusters.
- [ ] Update `pathway_architect.py` to support "Stability/Recovery" graph templates.

## Phase 5: Verification
- [ ] Force a "looping" state via a mock reasoning task.
- [ ] Verify the Sentinel detects the loop, applies Radical Acceptance, and successfully reroutes to a diverse path.
