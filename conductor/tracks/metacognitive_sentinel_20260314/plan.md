# Implementation Plan: The Metacognitive Sentinel

## Phase 1: Sentinel Observation
- [ ] Update `metacognitive_sentinel.py` to run as a daemon listener on the `SwarmBus`.
- [ ] Implement tracking for message repetitive n-grams and logical progression.

## Phase 2: Intervention Mechanics
- [ ] Add `INTERVENTION` to `MessageProtocol` in `swarm_bus.py`.
- [ ] Update `SwarmBroker` and `HiveNode` to respect intervention broadcasts (pause, reset context).

## Phase 3: DBT/CBT Heuristics
- [ ] Implement the specific psychological heuristic prompts to break AI looping (Cognitive Defusion).

## Phase 4: Validation
- [ ] Create an adversarial test script that forces a Swarm into a logic loop.
- [ ] Verify the Sentinel detects it, broadcasts an intervention, and successfully rescues the task.
