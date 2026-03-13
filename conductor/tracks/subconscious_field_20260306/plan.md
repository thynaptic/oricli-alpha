# Implementation Plan: Persistent Memory Subconscious

## Phase 1: Infrastructure & Core Module
- [ ] Implement `oricli_core/brain/modules/subconscious_field.py`.
- [ ] Build the `VectorBuffer` logic (circular buffer for embeddings).
- [ ] Implement the `get_mental_state` operation (vector aggregation).

## Phase 2: Cognitive Integration
- [ ] Update `oricli_core/brain/modules/cognitive_generator.py` to query the `subconscious_field` during intent detection.
- [ ] Use the mental state to influence module ranking and weightings.

## Phase 3: Feedback Loop
- [ ] Implement `vibrate` operation in `subconscious_field.py`.
- [ ] Update `AgentPipelineModule` to "vibrate" successful, verified results back into the subconscious field.

## Phase 4: Persistence & Sync
- [ ] Implement `save_state` and `load_state` for the field.
- [ ] Update `runpod_bridge` to include subconscious state in the S3 cluster sync.

## Phase 5: Verification
- [ ] Teach Oricli-Alpha a unique fact via JIT.
- [ ] Verify that subsequent unrelated queries are tonally or logically influenced by that fact without it being in the immediate prompt context.
