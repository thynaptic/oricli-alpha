# Implementation Plan: Hybrid Data Strategy

## Phase 1: Pandas Integration (Core Data)

### 1.1 `memory_processor` Refactor
- [ ] Implement Pandas-based memory cleaning and deduplication.
- [ ] Add vector-ready DataFrame export for RAG modules.

### 1.2 `memory_pipeline_service` Update
- [ ] Integrate Pandas into the processing threshold logic.
- [ ] Speed up bulk storage and recall using DataFrame operations.

## Phase 2: Neo4j Infrastructure (Knowledge Graph)

### 2.1 Neo4j Abstraction Layer
- [ ] Create `oricli_core/services/neo4j_service.py` to manage connection pooling and Cypher execution.
- [ ] Implement standard schema for Oricli entities and relationships (TEMPORAL, CAUSAL, SEMANTIC).

### 2.2 `memory_graph` Migration
- [ ] Refactor `MemoryGraph` to prioritize the Neo4j backend.
- [ ] Implement Cypher queries for `multi_hop_reasoning` and `traverse_memory`.

### 2.3 `knowledge_graph_builder` & `world_knowledge` Update
- [ ] Update these modules to sync extracted entities directly into Neo4j.

## Phase 3: Validation & Tooling

### 3.1 Setup Utilities
- [ ] Create `scripts/setup_neo4j.sh` to automate Docker-based deployment.
- [ ] Add `scripts/migrate_networkx_to_neo4j.py` to port existing graph state.

### 3.2 Performance Benchmarking
- [ ] Add a benchmark script to compare retrieval latency between the old NetworkX stack and the new Pandas/Neo4j stack.
