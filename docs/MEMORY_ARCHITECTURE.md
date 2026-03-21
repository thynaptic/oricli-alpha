# Memory Architecture: The Sovereign Memory Stack

**Document Type:** Technical Reference  
**Version:** v2.1.0  
**Status:** Active  

---

## 1. Overview

Oricli-Alpha uses a three-tier memory architecture. Each tier is optimized for a different access pattern and data lifetime:

| Tier | Technology | Speed | Persistence | Purpose |
|---|---|---|---|---|
| **Memory Bridge** | LMDB (PowerDNS/lmdb-go) | μs reads | Durable on-disk | Fast KV store for all memory categories + in-process vector search |
| **Working Memory Graph** | chromem-go (in-process) | ns reads | Ephemeral (session) | Live graph of active conversation nodes, gap detection |
| **Knowledge Graph** | Neo4j (bolt://) | ms reads | Durable relational | Long-horizon relationships, entity context, temporal events |

Data flows upward: episodic events land in LMDB, the Knowledge Graph holds durable relationships, and the Working Memory Graph provides real-time context during inference.

---

## 2. Memory Bridge (LMDB)

**Implementation:** `pkg/service/memory.go` → `MemoryBridge`  
**Storage path:** `.memory/` (configurable, AES-256-GCM encrypted at rest)

### 2.1 Memory Categories

LMDB is organized into eight named databases, each accessed as a distinct category:

| Category | Purpose |
|---|---|
| `semantic` | Factual world knowledge nodes |
| `episodic` | Past conversation turns and events |
| `identity` | User relationship history and preferences |
| `skill` | Learned procedure and task templates |
| `long_term_state` | Persistent configuration and sovereign goal state |
| `reflection_log` | SCAI audit results and metacognitive notes |
| `vector_index` | Dense float32 vectors for similarity search |
| `temporal_index` | Records keyed by Unix timestamp for time-range queries |

### 2.2 Operations

```go
// Store any record
mb.Put(category, id, data, metadata)

// Retrieve by ID
mb.Get(category, id)

// Time-range scan (used by Dream Daemon)
mb.QueryTemporal(startUnix, endUnix)

// Cosine similarity search over vector_index
mb.VectorSearch(queryVector []float32, topK int, minScore float32)
```

`VectorSearch` is **in-process** — no external vector database required. All float32 vectors are stored in the LMDB `vector_index` database, loaded into memory at query time, and scored via cosine similarity. For the current scale (< 100K nodes), this is faster than a network-round-trip to a dedicated vector DB.

### 2.3 Encryption

All records are encrypted with **AES-256-GCM** before writing to LMDB. The key is derived from `MAVAIA_MEMORY_ENCRYPTION_KEY` (base64-encoded 32-byte key, set in the systemd unit). Reads decrypt transparently. Key rotation requires a re-encode migration pass.

---

## 3. Working Memory Graph

**Implementation:** `pkg/service/memory_graph.go` → `MemoryGraphService`  
**Backend:** `chromem-go` (embedded, in-process)

The Working Memory Graph maintains a live session-scoped graph of entities and their relationships. It is the primary input for:

- **CuriosityDaemon**: `FindGaps()` identifies nodes with low connectivity or low confidence score as foraging targets.
- **Inference pipeline**: Step 5 (Memory Retrieval) queries the working graph for relevant context before assembling the system prompt.

Nodes have a `confidence` float and an `embedding` vector. Edges carry a `relation_type` string. After a session ends, high-confidence nodes are promoted to the Neo4j Knowledge Graph by `MemoryGraphService.Consolidate()`.

---

## 4. Knowledge Graph (Neo4j)

**Implementation:** `pkg/service/graph.go` → `GraphService`  
**Connection:** `bolt://localhost:7687` (local Neo4j instance)

The Knowledge Graph is the long-term relational memory. It stores:

- **Entity nodes** with labels, attributes, and confidence scores
- **Temporal event nodes** (`MetaEvent`) created by the JIT and Dream daemons
- **Relationship edges** between entities (supports multi-hop reasoning)

The Dream Daemon queries it for orphaned nodes. The JIT Daemon writes `MetaEvent` nodes after each absorption cycle. The TemporalService (`pkg/service/temporal.go`) uses it to implement Sovereign Cron — persisting multi-day goal state as graph nodes.

### Key Cypher patterns

```cypher
-- Find low-context nodes (used by Dream Daemon)
MATCH (n) WHERE COUNT { (n)--() } < 2 RETURN n.id, labels(n) LIMIT 1

-- Create a meta-event (used by JIT Daemon)
CREATE (n:MetaEvent {id: $id, type: 'meta_event', content: $content, timestamp: $ts, importance: 0.9})
```

---

## 5. Memory Pipeline

**Implementation:** `pkg/service/memory_pipeline.go` → `MemoryPipelineService`

The pipeline coordinates all three tiers during inference:

1. **Encode**: Incoming user message is embedded via `EmbeddingEngineService`.
2. **Retrieve**: Cosine search against LMDB `vector_index` + Working Memory Graph lookup.
3. **Inject**: Top-K results are included in the composite instruction payload (Step 5).
4. **Write-back**: After response generation, new facts are written to LMDB `episodic` and the Working Memory Graph.
5. **Consolidate** (async): High-confidence working memory nodes are promoted to Neo4j.

---

## 6. Code Memory

**Implementation:** `pkg/service/code_memory.go` → `CodeMemoryService`

A specialized memory layer for the codebase itself. Indexes Go source files into LMDB with embeddings, enabling semantic code search (used by the ReformDaemon and CodeEngine module). Stored under `.memory/code/`.
