# Epistemic Hygiene — Memory Sanity in a Self-Learning System

> **The Problem:** A system that writes its own memories, learns from those memories, and then writes more memories based on what it learned — will eventually reason entirely inside its own fiction. This document describes the defence layer that prevents that.

---

## Why This Matters (The "Insane from Synthetic Data" Problem)

Oricli writes memories from three self-generated sources:

| Source | Example |
|---|---|
| Curiosity findings | CuriosityDaemon summarises web results and stores them as `knowledge_fragments` |
| Conversation write-back | After each response, the exchange is persisted to `memories` |
| Future: Dream Daemon | Idle synthesis / reflection written back to memory |

Without guardrails, these sources create a compounding feedback loop:

```
Curiosity forages "quantum computing"
    → writes knowledge fragment (author: oricli, importance: 0.7)
    → next query: fragment hits RAG context
    → Oricli's reply is now influenced by her own synthetic summary
    → reply is written back as conversation memory
    → next curiosity burst: "quantum computing" already in seenKeys
    → ... but also re-reinforced by the conversation memory
    → Repeat 50 times → her "knowledge" of this topic is entirely self-referential
```

This is the **synthetic data collapse** problem studied in LLM training research, reproduced at inference-time through a memory loop.

Additionally:
- **Celebrity Memory**: `access_count` increases on retrieval → high-access memories rank higher → get accessed more often → a single early-written (possibly wrong) memory dominates RAG forever.
- **Temporal Misinformation**: A memory about "best AI models" written in March is stale by October — but with a flat 180-day decay it still scores above a fresh accurate memory.
- **Synthetic Lineage Depth**: A memory derived from another synthetic memory (`synthetic_l2+`) carries compounded uncertainty. Without tracking this, `synthetic_l2+` records are weighted identically to ground-truth user statements.

---

## The Epistemic Hygiene Layer

Three interlocking mechanisms implemented in `pkg/service/memory_bank.go` and `pkg/service/curiosity_daemon.go`.

---

## 1. Provenance Tracking

Every memory record carries a `provenance` field that declares the **origin quality** of the data.

### Provenance Levels

| Value | Meaning | RAG Weight | Recycled? |
|---|---|---|---|
| `user_stated` | User explicitly stated this as fact | **×1.5 + anchor bonus** | **Never** |
| `web_verified` | Retrieved directly from a live URL with timestamp | ×1.2 | Yes |
| `seen` | Image-derived description (vision inference) | ×1.0 | Yes |
| `conversation` | Inferred from a chat exchange | ×0.9 | Yes |
| `contrastive` | ACCEPTED/REJECTED emoji feedback pair (DPO) | ×1.3 | Yes |
| `solved` | Verified good response committed by CBR pipeline | ×1.4 | Yes |
| `gold` | 📌-bookmarked anchor (highest trust tier) | ×1.6 | **Never** |
| `synthetic_l1` | Curiosity summary of web results (one-hop from real data) | ×0.85 | Yes |
| `synthetic_l2+` | Derived from another synthetic memory | ×0.6 / lineage_depth | Yes |

### Anchor Memories (`user_stated` and `gold`)

`user_stated` and `gold` memories are **immortal anchors**:
- `retentionScore()` returns `+Inf` — excluded from all recycle passes
- RAG scoring adds `+10.0` to their cosine score — they always surface first regardless of topic match quality
- Capped at 2 anchors per RAG context window to prevent anchor flooding

📌 **Gold anchors** are bookmarked by the user via the memory browser. They share the same immortal retention behavior as `user_stated` but carry a higher RAG weight (×1.6 vs ×1.5).

These are the ground-truth bedrock of Oricli's world model. If you tell her something directly, it persists forever and outweighs any amount of synthetic learning.

### Lineage Depth

`lineage_depth` tracks synthetic generation hops from real data:

```
User states a fact         → lineage_depth: 0 (ground truth)
CuriosityDaemon web forage → lineage_depth: 1 (one-hop synthetic)
Memory derived from above  → lineage_depth: 2 (two-hop — reduced weight)
```

For `synthetic_l2+` records, the RAG weight is computed as `0.6 / max(lineage_depth, 1)`, so deeper chains receive progressively less influence.

### Implementation

```go
// Assign provenance when writing
MemoryBank.Write(MemoryFragment{
    Content:      combined,
    Source:       "conversation",
    Provenance:   ProvenanceConversation,
    Volatility:   InferVolatility(topic),
    LineageDepth: 0,
})

// WriteKnowledgeFragment always uses synthetic_l1 + lineage_depth=1
MemoryBank.WriteKnowledgeFragment(topic, intent, content, 0.7)
// internally: provenance="synthetic_l1", lineage_depth=1
```

---

## 2. Volatility-Aware Decay

Memories about different topic types have radically different natural lifespans. A single hardcoded 180-day decay was applying the same half-life to "the speed of light" and "current Bitcoin price".

### Volatility Classes

| Class | Half-Life | Auto-Assigned Topics |
|---|---|---|
| `stable` | 180 days | Science, mathematics, engineering fundamentals |
| `current` | 30 days | AI/ML, software, frameworks, APIs, cloud, crypto, tech news |
| `ephemeral` | 7 days | Market prices, current events, news, weather, election results, scores |

### Inference

`InferVolatility(topic string)` classifies by keyword patterns at write time:

```go
// ephemeral keywords: "price", "market", "stock", "news", "today", "breaking",
//                     "weather", "score", "event", "election", "earnings"
// current keywords:   "ai", "gpt", "llm", "model", "framework", "library",
//                     "api", "release", "version", "update", "software", "cloud",
//                     "crypto", "blockchain", "startup", "tech"
// default:            stable
```

### Retention Formula

```
retention_score = importance × log(1 + access_count) × e^(-age_days / half_life)
```

Where `half_life` is 7, 30, or 180 depending on `topic_volatility`. `user_stated` anchors return `+Inf` and are exempt.

**Practical impact:** An "AI model comparison" memory written 45 days ago with `topic_volatility=current` (30d half-life) scores ~22% of its original importance — far below a fresh `stable` memory at the same importance. Previously it would have been ~78%.

---

## 3. Novelty Cap (Anti-Obsession)

The CuriosityDaemon can only write **3 knowledge fragments per topic across all sessions**. On the 4th attempt to forage the same topic, it is silently skipped.

### Why 3?

- 1 fragment: initial research pass
- 2 fragments: confirms / enriches with a second source
- 3 fragments: third independent synthesis (diminishing returns begin)
- 4+: reinforcement, not learning — this is where synthetic drift begins

### Implementation

```go
// In forageTopic() — fires before any web search is attempted
if d.MemoryBank != nil {
    count := d.MemoryBank.KnowledgeCount(ctx, topic)
    if count >= 3 {
        log.Printf("[CuriosityDaemon] skipping %q — already has %d fragments (novelty cap)", topic, count)
        return
    }
}
```

`KnowledgeCount(ctx, topic)` queries PocketBase with a `topic ~ "..."` filter and returns `TotalItems`. The cap is enforced across sessions — not just within the current burst — because the count comes from the persistent PocketBase store.

This forces the CuriosityDaemon to continuously expand into new territory rather than deepening its own synthetic knowledge wells.

---

## 4. Schema Fields

The three epistemic hygiene fields are present on both `memories` and `knowledge_fragments` collections.

| Field | Type | Values |
|---|---|---|
| `provenance` | text | `user_stated` \| `web_verified` \| `seen` \| `conversation` \| `contrastive` \| `solved` \| `gold` \| `synthetic_l1` \| `synthetic_l2+` |
| `topic_volatility` | text | `stable` \| `current` \| `ephemeral` |
| `lineage_depth` | number | `0` (ground truth) → `1` (synthetic_l1) → `2+` (synthetic chain) |

### Live Migration

`MigrateEpistemicFields(ctx, c *Client)` is called inside `Bootstrap()` on every startup. It patches existing collections to add the three fields if they don't already exist. This means:

- **Zero downtime** — the migration runs idempotently whether PB has 0 or 500,000 records
- **Legacy records** get the fields added with empty/zero values
- Legacy `provenance = ""` is treated as `synthetic_l1` in `QuerySimilar` (safest assumption)

---

## 5. RAG Query Flow (Updated)

The full `QuerySimilar` flow with epistemic hygiene:

```
1. Keyword pre-filter (topic ~ "..." || content ~ "...") → up to 50 candidates
2. Generate query embedding via nomic-embed-text
3. For each candidate:
   a. base_score = cosine_similarity(query_vec, doc_vec)
              OR  frag.importance  (if no embedding yet)
   b. prov_weight = provenanceWeight[provenance]   (0.6–1.5)
   c. final_score = base_score × prov_weight
   d. if provenance == "user_stated": final_score += 10.0
4. Sort descending by final_score
5. Return top N fragments
6. Bump access_count asynchronously for each returned record
```

**Result:** A deeply-cached `synthetic_l1` fragment about "golang goroutines" (cosine: 0.87, weight: 0.85) scores **0.74**. A fresh `user_stated` fact about the same topic (cosine: 0.72, weight: 1.5 + anchor) scores **11.08**. The anchor wins every time.

---

## 6. Summary — What We Prevented

| Risk | Mechanism | Status |
|---|---|---|
| Synthetic echo chamber | Novelty cap (≥3 fragments → skip topic) | ✅ |
| Celebrity memory domination | Provenance weights penalise old synthetic records | ✅ |
| Temporal misinformation | Volatility-aware decay (7/30/180d half-lives) | ✅ |
| User truth being overwritten | `user_stated` anchors are immortal and score +10 | ✅ |
| Deep synthetic lineage drift | `lineage_depth` field + 0.6/depth weight reduction | ✅ |
| Stale schema on existing PB | Live `MigrateEpistemicFields()` migration | ✅ |

---

## References

- Implementation: `pkg/service/memory_bank.go` — `Provenance`, `Volatility`, `InferVolatility`, `retentionScore`, `QuerySimilar`, `Recycle`
- Novelty cap: `pkg/service/curiosity_daemon.go` — `forageTopic()`
- PB migration: `pkg/connectors/pocketbase/setup.go` — `MigrateEpistemicFields`
- Schema patch: `pkg/connectors/pocketbase/client.go` — `PatchCollectionSchema`
- Context: `docs/MEMORY_ARCHITECTURE.md` §7, `docs/POCKETBASE_MEMORY.md`, `docs/DAEMONS.md` §5
