# Specification: Hybrid Data Strategy (Pandas & Neo4j Migration)

## Objective
To modernize Oricli-Alpha's data layer by migrating from in-memory NetworkX graphs to a hybrid strategy using **Pandas** for bulk data processing and **Neo4j** for persistent, scalable relationship management. This will improve system performance, RAG efficiency, and memory management for the 420k line codebase.

## Background
Currently, Oricli-Alpha relies heavily on NetworkX for relationship mapping and in-memory dicts for data processing. As the system scales toward "The Hive" (Distributed Swarm Intelligence), this approach becomes a bottleneck. NetworkX does not scale well to multi-million node graphs, and raw Python collections are inefficient for bulk RAG operations.

## Requirements

### 1. Pandas Integration (The "Data Lake")
- Implement a `DataProcessingService` that uses Pandas DataFrames for all bulk memory cleaning, clustering, and RAG preprocessing.
- Replace manual list/dict iterations in `memory_processor.py` and `memory_pipeline_service.py` with vectorized Pandas operations.

### 2. Neo4j Migration (The "Knowledge Vault")
- Transition `memory_graph`, `knowledge_graph_builder`, and `world_knowledge` to use a Neo4j backend.
- Support persistent storage of relationships, allowing Oricli-Alpha to "remember" state across restarts without rebuilding the graph from scratch.
- Implement Cypher-based multi-hop reasoning for complex queries.

### 3. Graceful Fallback
- Maintain a `NetworkX` and `Dict` fallback for environments where Neo4j is not available (e.g., lightweight local runs).
- Use an environment-aware `DataBackendManager` to select the best available stack.

### 4. Infrastructure Support
- Provide a `scripts/setup_neo4j.sh` or Docker-based setup for local Neo4j deployment.

## Success Criteria
- RAG retrieval speed improves for large memory sets.
- Relationship queries (multi-hop) are executed in constant time regardless of memory size.
- Memory graph persists across system restarts.
- System remains 100% functional in environments without Neo4j (via NetworkX fallback).
