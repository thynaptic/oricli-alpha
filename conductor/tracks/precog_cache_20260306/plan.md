# Implementation Plan: Pre-Cog Cache

## Phase 1: Cache Service
- [ ] Implement `oricli_core/services/precog_service.py`.
- [ ] Use a time-limited cache (TTL) to store speculative responses.
- [ ] Implement fuzzy-matching for queries.

## Phase 2: Speculation Logic
- [ ] Create `oricli_core/brain/modules/speculator.py`.
- [ ] Integrate with `hypothesis_generation` to predict follow-ups.
- [ ] Build the background execution thread.

## Phase 3: API Integration
- [ ] Update `oricli_core/api/server.py` to check the `precog_service` before standard execution.
- [ ] Ensure speculative results are correctly formatted for the API response.

## Phase 4: Verification
- [ ] Ask a question.
- [ ] Wait 10 seconds.
- [ ] Ask a predicted follow-up.
- [ ] Verify the response is delivered from the cache with zero processing latency.
