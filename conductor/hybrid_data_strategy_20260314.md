# Implementation Plan: Oricli-Alpha Hybrid Data Strategy (Pandas & Neo4j)

## Objective
To improve system-wide data efficiency, RAG performance, and relationship management by migrating from in-memory NetworkX to a hybrid Pandas + Neo4j stack. This will better support the 420k line codebase and the "Hive" (Sovereign AGLI) vision.

## 1. Implement Neo4j Service Layer
- **File:** `oricli_core/services/neo4j_service.py`
- **Goal:** Create a singleton connection manager and high-level Cypher execution utility for all graph-based brain modules.
- **Key Features:** Connection pooling, basic node/relationship operations, shortest path finding, and neighbor traversal.

## 2. Refactor MemoryGraph for Neo4j Persistence
- **File:** `oricli_core/brain/modules/memory_graph.py`
- **Goal:** Shift the primary graph engine from NetworkX to Neo4j.
- **Implementation:**
    - Update `initialize` to prefer `get_neo4j_service()`.
    - Maintain `NetworkX` as a robust fallback for environments without a Neo4j server.
    - Implement Cypher queries for `multi_hop_reasoning` and `traverse_memory`.

## 3. Optimize MemoryProcessor with Vectorized Pandas
- **File:** `oricli_core/brain/modules/memory_processor.py`
- **Goal:** Replace slow `iterrows()` loops with vectorized string and set operations.
- **Key Refactors:**
    - `_score_relevance_to_query`: Use Pandas vectorized string contains/match.
    - `_generate_relationships`: Use vectorized set intersections or cross-joins for similarity calculation.

## 4. Provide Neo4j Infrastructure Script
- **File:** `scripts/setup_neo4j.sh`
- **Goal:** Provide a one-command Docker-based setup for local Neo4j deployment with data persistence.

## Verification & Testing
- **Unit Tests:** Verify `Neo4jService` can connect and execute basic Cypher.
- **Integration Test:** Verify `MemoryGraph` correctly stores and recalls nodes/edges in both Neo4j and NetworkX (fallback).
- **Performance Benchmark:** Run `memory_processor` on a large test dataset (1k+ memories) to compare processing time before and after vectorization.
