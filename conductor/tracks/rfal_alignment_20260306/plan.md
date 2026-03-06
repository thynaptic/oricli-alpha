# Implementation Plan: Conversational RFAL Alignment

**Phase 1: RFAL Module & Conflict Detection**
Goal: Establish the base RFAL module and the logic to detect conversational conflicts.
- [ ] Task: Scaffold RFAL Module
    - [ ] Create `mavaia_core/brain/modules/rfal_engine.py`.
    - [ ] Implement `RFALEngine` class with `process_feedback`, `calculate_reward`, and `generate_dpo_pair` operations.
- [ ] Task: Implement Conflict Detection
    - [ ] Logic for keyword-based rejection detection.
    - [ ] Integration with basic sentiment analysis for frustration triggers.
    - [ ] Repetition detection logic in conversation history.
- [ ] Task: TDD - Conflict Logic
    - [ ] Write unit tests to verify conflict detection on synthetic conversation strings.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Conflict Detection' (Protocol in workflow.md)

**Phase 2: Reward Engine & Multi-Factor Scoring**
Goal: Build the scoring engine that combines HITL, Factual, and Tone signals.
- [ ] Task: Build Multi-Factor Scorer
    - [ ] Logic to cross-reference `world_knowledge` for factual scoring.
    - [ ] Logic to cross-reference `AdapterRouter` for tone alignment scoring.
    - [ ] Implementation of the weighted sum for the final Reward Scalar.
- [ ] Task: Experience Replay Integration
    - [ ] Create `mavaia_core/data/rfal_lessons.jsonl` persistence logic.
    - [ ] Logic to handle `[Prompt, Chosen, Rejected]` triplet generation.
- [ ] Task: TDD - Reward Accuracy
    - [ ] Verify that a hallucinated fact results in a negative weighted award.
    - [ ] Verify correct DPO pair generation from a user correction.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Reward Engine' (Protocol in workflow.md)

**Phase 3: Cognitive Loop Integration**
Goal: Wire the RFAL engine into the live generation pipeline without adding latency.
- [ ] Task: Background Processing Hook
    - [ ] Implement asynchronous hook in `cognitive_generator.py` or `MavaiaClient`.
    - [ ] Logic to send response + user feedback to `RFALEngine` in a background thread.
- [ ] Task: Interaction Buffer Management
    - [ ] Logic to track "Lesson Buffer" size.
    - [ ] CLI/API support for manually triggering a sync.
- [ ] Task: TDD - Loop Integration
    - [ ] Verify that RFAL processing does not block user response time.
    - [ ] Verify buffer increments after conflict interactions.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Loop Integration' (Protocol in workflow.md)

**Phase 4: Bridge Sync & DPO Training**
Goal: Update the RunPod bridge to consume RFAL lessons and update weights.
- [ ] Task: Bridge DPO Extension
    - [ ] Add `--train-rfal` flag to `scripts/runpod_bridge.py`.
    - [ ] Logic to sync `rfal_lessons.jsonl` to the remote pod.
- [ ] Task: Training Script Update
    - [ ] Update `scripts/train_neural_text_generator.py` to support a DPO training head for RFAL data.
- [ ] Task: TDD - Training Sync
    - [ ] Verify successful remote training job initiation using RFAL lessons.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Bridge & Training' (Protocol in workflow.md)
