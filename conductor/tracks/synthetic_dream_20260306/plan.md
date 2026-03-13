# Implementation Plan: Synthetic Dream State

## Phase 1: Infrastructure
- [ ] Create `oricli_core/data/synthetic_insights.jsonl`.
- [ ] Implement `oricli_core/services/insight_service.py` for thread-safe insight management.

## Phase 2: Dream Daemon Implementation
- [ ] Create `scripts/oricli_dream_daemon.py`.
- [ ] Implement idle-detection logic (checking last query time).
- [ ] Build the "Consolidation Loop":
    - [ ] Sample memory graph and JIT facts.
    - [ ] Call `analogical_reasoning`.
    - [ ] Score with `meta_evaluator`.

## Phase 3: S3 & Training Integration
- [ ] Update `runpod_bridge` watchdog to sync `synthetic_insights` to S3.
- [ ] Add support for training on synthetic insights in the RFAL or JIT pass.

## Phase 4: Verification
- [ ] Populate memory with two disparate facts.
- [ ] Manually trigger the dream daemon.
- [ ] Verify a novel insight is generated, scored, and recorded.
