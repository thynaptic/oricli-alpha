# Implementation Plan: The Dream Daemon (Synthetic Dreaming)

## Phase 1: Idle Detection
- [ ] Create `oricli_dream_daemon.py`.
- [ ] Implement system resource and API traffic monitoring to safely enter/exit "Dream Mode".

## Phase 2: Graph Analysis
- [ ] Add Cypher queries to `Neo4jService` to find "orphaned" nodes or low-confidence relationships.
- [ ] Implement an LLM prompt to generate curious research questions based on graph gaps.

## Phase 3: Autonomous Research
- [ ] Route the generated questions to the Swarm Bus.
- [ ] Trigger `web_ingestion_agent` to crawl the web for the answers and ingest the results.

## Phase 4: Dream Log API
- [ ] Add `GET /v1/dreams` endpoint to expose recent autonomous learning activity.
- [ ] Add `Dreams` namespace to `OricliAlphaClient`.

## Phase 5: Validation
- [ ] Seed the graph with a single obscure topic.
- [ ] Leave the system idle and verify it successfully researches and expands upon that topic.
