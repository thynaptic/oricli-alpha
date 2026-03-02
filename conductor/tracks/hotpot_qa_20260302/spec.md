# Track Spec: Stage 3 Capability Phase (HotpotQA)

## Overview
Implement the third stage of the cognitive curriculum, focusing on "multi-hop" reasoning and capability enhancement using the HotpotQA dataset.

## Objectives
- Integrate `hotpot_qa:distractor` into the training pipeline.
- Ensure the "Iron Guardian" (Sentinel) correctly monitors the capability phase.
- Automate the transition from Stage 2 weights to Stage 3 training.

## Acceptance Criteria
- [ ] HotpotQA data loads and extracts correctly (Greedy Recursive mode).
- [ ] Training initializes using Stage 2 model checkpoints as the base.
- [ ] Sentinel correctly detects loss floors or plateaus for Stage 3.
- [ ] Training artifacts for Stage 3 are synced and validated.
