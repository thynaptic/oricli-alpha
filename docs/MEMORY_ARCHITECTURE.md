# Memory Architecture: The Sovereign Memory Stack

**Document Type:** Technical Reference  
**Version:** v2.1.0  
**Status:** Active  

---

## 1. Overview

Oricli-Alpha uses a **four-tier memory architecture**. Each tier is optimized for a different access pattern and data lifetime:

| Tier | Technology | Speed | Persistence | Purpose |
|---|---|---|---|---|
| **Working Memory Graph** | chromem-go (in-process) | ns reads | Ephemeral (session) | Live graph of active conversation nodes, gap detection |
| **Memory Bridge** | LMDB (PowerDNS/lmdb-go) | μs reads | Durable on-disk | Fast KV store for all memory categories + in-process vector search |
| **Knowledge Graph** | Neo4j (bolt://) | ms reads | Durable relational | Long-horizon relationships, entity context, temporal events |
| **Long-Term Memory Bank** | PocketBase (external VPS) | ~2ms reads | Durable, 200GB | Cross-session recall, curiosity findings, spend ledger, RAG injection |

Data flows upward: episodic events land in LMDB, the Knowledge Graph holds durable relationships, the Working Memory Graph provides real-time context during inference, and PocketBase serves as the cold durable layer for long-horizon recall — surviving process restarts and redeployments.

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

---

## 7. Long-Term Memory Bank (PocketBase)

**Implementation:** `pkg/service/memory_bank.go` → `MemoryBank`  
**Connector:** `pkg/connectors/pocketbase/` → `client.go`, `setup.go`  
**Backend:** PocketBase v0.23+ on `https://pocketbase.thynaptic.com` (dedicated VPS, 200GB storage, ~2ms latency from primary VPS — same datacenter)

The PocketBase tier is the **cold durable layer** — it outlives every process restart, redeployment, and session boundary. It provides cross-session recall for RAG, persistent curiosity findings, durable spend tracking, and compressed conversation history.

### 7.1 Memory Access Pattern

```
Hot   →  chromem-go (WorkingMemoryGraph)   ns reads, session-scoped
Warm  →  LMDB (Memory Bridge)              μs reads, process-durable
Cold  →  PocketBase                        ~2ms reads, survives reboots
```

### 7.2 Collections

| Collection | Owner | Purpose |
|---|---|---|
| `memories` | admin / oricli | Conversation fragments + curiosity snippets with topic/importance metadata |
| `knowledge_fragments` | oricli (analyst) | CuriosityDaemon research findings — one entry per forged topic |
| `spend_ledger` | admin | RunPod monthly spend per service — restored on daemon startup |
| `conversation_summaries` | admin | Compressed session summaries for long-horizon RAG |

### 7.3 Oricli's Identity

Oricli has her own PocketBase user account (`oricli@thynaptic.com`, role: `analyst`). All curiosity findings and internal epistemic discoveries are written under her user token — not as system/admin records. This means:

- In the PocketBase admin UI, her records are visibly hers
- `author = "oricli"` → curiosity findings, knowledge fragments
- `author = "user"` → conversation fragments, summaries

The account is auto-created by `Bootstrap()` on first startup if it doesn't already exist.

### 7.4 RAG Injection

Before every chat response, `MemoryBank.QuerySimilar(lastUserMsg, 5)` queries the `memories` collection. The retrieval pipeline is:

1. **Keyword pre-filter** — `topic ~ "..." || content ~ "..."` → up to 50 candidates
2. **Semantic re-ranking** — cosine similarity via `nomic-embed-text` embeddings
3. **Provenance weighting** — each result's score is multiplied by its `provenance` weight (see §7.9)
4. **Anchor injection** — `user_stated` memories are always surfaced first (score + 10.0 bonus)

Results are prepended to the system prompt as a `## Relevant Memory Context` block (capped at 1200 chars).

### 7.5 Memory Recycling

When record count in `memories` exceeds `PB_MEMORY_MAX_RECORDS` (default: 500,000), the bottom 10% by retention score is pruned. The retention formula uses a **per-record half-life** based on `topic_volatility`:

```
retention_score = importance × log(1 + access_count) × e^(-age_days / half_life)
```

| `topic_volatility` | Half-Life |
|---|---|
| `stable` | 180 days |
| `current` | 30 days |
| `ephemeral` | 7 days |

`user_stated` anchors return `+Inf` and are **never pruned**. See §7.9 for the full epistemic hygiene system.

### 7.6 Spend Ledger

`MemoryBank.LoadSpend(ctx, "inference", month)` is called on backbone startup to restore the current month's RunPod spend. `PersistSpend()` is called every minute during active pod sessions. This means the monthly cap guard works correctly even across daemon restarts.

### 7.7 Bootstrap

`MemoryBank.Bootstrap(ctx)` is called as a non-blocking goroutine during `NewServerV2()`. It:

1. Creates all 4 collections if they don't exist (idempotent)
2. Creates Oricli's analyst user account if it doesn't exist
3. Logs each action — silent on repeat boots
4. Runs `MigrateEpistemicFields()` — patches existing collections with epistemic hygiene fields (idempotent)

### 7.9 Epistemic Hygiene

A self-learning system that writes its own memories can develop a synthetic data feedback loop — reasoning increasingly within its own fiction. Three interlocking mechanisms prevent this:

**Provenance** — every memory record carries a `provenance` field declaring origin quality. `user_stated` memories are immortal anchors; `synthetic_l1` (curiosity findings) and `synthetic_l2+` (derived from another synthetic record) carry reduced RAG weights.

**Volatility-aware decay** — `topic_volatility` controls the decay half-life: 7 days for ephemeral topics (prices, news), 30 days for current tech, 180 days for stable fundamentals.

**Novelty cap** — CuriosityDaemon enforces a maximum of 3 knowledge fragments per topic across all sessions. A 4th forage attempt is silently skipped — Oricli must keep exploring new territory.

→ Full reference: **`docs/EPISTEMIC_HYGIENE.md`**

### 7.8 Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `PB_BASE_URL` | — | PocketBase instance URL (required) |
| `PB_ADMIN_EMAIL` | — | Admin auth email (required) |
| `PB_ADMIN_PASSWORD` | — | Admin auth password (required) |
| `PB_ORICLI_EMAIL` | `oricli@thynaptic.com` | Oricli's analyst account email |
| `PB_ORICLI_PASSWORD` | `OricliSovereign2026!` | Oricli's analyst account password |
| `PB_MEMORY_MAX_RECORDS` | `500000` | Recycle threshold for `memories` collection |
