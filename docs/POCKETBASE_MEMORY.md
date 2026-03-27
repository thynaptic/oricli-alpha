# PocketBase Long-Term Memory Bank

**Document Type:** Technical Reference  
**Version:** v1.0.0  
**Status:** Active  

---

## Overview

PocketBase serves as Oricli's **cold durable memory tier** — the layer that outlives every process restart, redeployment, and session boundary. It sits on a dedicated VPS (`https://pocketbase.thynaptic.com`, 200GB storage) in the same datacenter as the primary VPS, giving ~2ms round-trip latency.

```
Hot   →  chromem-go (WorkingMemoryGraph)   ns    — session-scoped
Warm  →  LMDB (Memory Bridge)              μs    — process-durable
Cold  →  PocketBase                        ~2ms  — survives reboots, cross-session
```

The integration is entirely non-blocking: writes fire-and-forget as goroutines. Reads (RAG queries) happen before each response but are capped at 10s timeout and fail silently if PocketBase is unreachable — the system degrades gracefully to no long-term recall rather than breaking inference.

---

## Identity: Oricli's Analyst Account

Oricli has her own PocketBase user account, distinct from the admin identity:

| Identity | Email | Role | Used for |
|---|---|---|---|
| Admin | `cass@thynaptic.com` | `commander` | Collection management, user creation, conversation/summary writes |
| Oricli | `oricli@thynaptic.com` | `analyst` | Curiosity findings, knowledge fragments, internal epistemic discoveries |

The analyst account is created automatically by `Bootstrap()` on first startup. Records written by Oricli carry `author: "oricli"` — visible in the PocketBase admin UI as records explicitly owned by her, not the system.

This is intentional: her curiosity research and epistemic findings are *her* intellectual output, not system artifacts.

---

## Collections

### `memories`
Conversation fragments and research snippets. The primary RAG source.

| Field | Type | Description |
|---|---|---|
| `content` | text | The memory content |
| `source` | text | `"conversation"` \| `"curiosity"` \| `"summary"` |
| `author` | text | `"oricli"` \| `"user"` \| `"system"` |
| `topic` | text | Extracted topic label for keyword search |
| `session_id` | text | Originating session |
| `importance` | number | 0.0–1.0 weight for retention scoring |
| `access_count` | number | How many times this memory was retrieved |
| `last_accessed` | text | ISO8601 timestamp of last retrieval |
| `provenance` | text | Origin quality: `user_stated` \| `web_verified` \| `seen` \| `conversation` \| `synthetic_l1` \| `synthetic_l2+` |
| `topic_volatility` | text | Decay class: `stable` \| `current` \| `ephemeral` |
| `lineage_depth` | number | Synthetic hops from ground truth (0=direct, 1=curiosity, 2+=derived) |
| `embedding` | json | float32 vector for semantic search (nomic-embed-text, 768-dim) |

### `knowledge_fragments`
CuriosityDaemon research findings. One entry per forged topic. Always authored by Oricli.

| Field | Type | Description |
|---|---|---|
| `topic` | text | The researched topic |
| `intent` | text | Classified intent type (DEFINITION, TECHNICAL, etc.) |
| `content` | text | Distilled 3–5 fact summary |
| `author` | text | Always `"oricli"` |
| `importance` | number | 0.7 default (curiosity-derived) |
| `access_count` | number | Retrieval count |
| `provenance` | text | Always `"synthetic_l1"` (curiosity-generated) |
| `topic_volatility` | text | Auto-inferred from topic keywords |
| `lineage_depth` | number | Always `1` (one hop from web data) |
| `embedding` | json | float32 vector for semantic search (nomic-embed-text, 768-dim) |

### `spend_ledger`
RunPod monthly spend per service. Survives daemon restarts.

| Field | Type | Description |
|---|---|---|
| `month` | text | Format: `"2026-03"` |
| `service` | text | `"inference"` \| `"imagegen"` |
| `amount` | number | Accumulated spend in USD |

### `conversation_summaries`
Compressed session summaries for long-horizon RAG.

| Field | Type | Description |
|---|---|---|
| `session_id` | text | Session identifier |
| `summary` | text | Compressed narrative of the session |
| `message_count` | number | Number of messages in the session |
| `topics` | json | Array of extracted topic strings |
| `embedding` | json | (Future) float32 vector |

### `canvas_shares`
Public share links for Canvas artifacts (served at `/share/:id`).

| Field | Type | Description |
|---|---|---|
| `share_id` | text | Public share identifier |
| `title` | text | Optional display title |
| `doc_type` | text | `html` \| `markdown` \| `code` \| `text` |
| `content` | text | Stored artifact content |
| `language` | text | Optional language (e.g., `html`, `js`) |

---

## RAG Injection

Before every chat response, the system performs a keyword/topic match against `memories`:

```go
frags, _ := MemoryBank.QuerySimilar(ctx, lastUserMsg, 5)
ragCtx  := FormatRAGContext(frags, 1200)
// → prepended to system prompt if non-empty
```

**Filter:** PocketBase filter syntax `topic ~ "query" || content ~ "query"`, pre-filters up to 50 candidates.

**Ranking pipeline:**
1. Cosine similarity re-rank via `nomic-embed-text` embeddings (falls back to `importance` if no embedding yet)
2. Provenance weight multiplied into score (`user_stated`=×1.5, `web_verified`=×1.2, `seen`=×1.0, `conversation`=×0.9, `synthetic_l1`=×0.85, `synthetic_l2+`=×0.6)
3. `user_stated` anchors receive an additional +10.0 — always surface first

Access counts bumped asynchronously after each retrieval.

**Injection format:**
```
## Relevant Memory Context
- [golang] Goroutine scheduler internals — work-stealing algorithm...
- [runpod] KoboldCpp idle timeout defaults to 15 minutes
---
<sovereign trace>
```

Capped at **1200 chars** to avoid context window bloat. Access counts are bumped asynchronously after each retrieval.

---

## Memory Recycling

When `memories` record count exceeds `PB_MEMORY_MAX_RECORDS` (default: 500,000), `Recycle()` prunes the bottom 10% by retention score:

```
retention_score = importance × log(1 + access_count) × e^(-age_days / half_life)
```

`half_life` is per-record based on `topic_volatility`: **stable=180d, current=30d, ephemeral=7d**. `user_stated` anchors return `+Inf` and are never pruned.

- High importance + high access = survives indefinitely
- Low importance + never accessed + old = pruned first
- Ephemeral topics (prices, news) decay out in 1–2 weeks without access

`Recycle()` is called as a goroutine — never blocks inference. Excludes `provenance = "user_stated"` records entirely.

→ Full rationale: **`docs/EPISTEMIC_HYGIENE.md`**

---

## Spend Ledger Flow

```
Backbone startup
    └── MemoryBank.LoadSpend(ctx, "inference", month)
        └── restores monthSpend in RunPodManager from PocketBase

RunPod pod active
    └── trackSpend tick (every minute)
        └── MemoryBank.PersistSpend("inference", month, spend)
            └── upserts spend_ledger record

Monthly cap guard
    └── RunPodManager.monthSpend vs monthlyCap
        └── now survives restarts ✓
```

---

## Bootstrap Sequence

`Bootstrap(ctx, adminClient)` runs as a goroutine in `NewServerV2()` with a 30-second timeout:

1. Check each collection → create if missing (idempotent)
2. Check for Oricli's user account by email → create if missing
3. Log each action; silent on repeat boots

```
[pb-bootstrap] created collection "memories"
[pb-bootstrap] created collection "knowledge_fragments"
[pb-bootstrap] created collection "spend_ledger"
[pb-bootstrap] created collection "conversation_summaries"
[pb-bootstrap] created collection "canvas_shares"
[pb-bootstrap] Created Oricli analyst account: oricli@thynaptic.com
```

---

## Authentication

**Critical:** PocketBase v0.23+ requires the raw token in the `Authorization` header — no `"Admin"` or `"Bearer"` prefix.

```
Authorization: <raw_token>
```

Two auth paths:
- **Admin**: `POST /api/admins/auth-with-password` → `NewClientFromEnv()`
- **User (Oricli)**: `POST /api/collections/users/auth-with-password` → `NewUserClient()`

Tokens are cached and refreshed automatically after 50 minutes. On 401, the client re-authenticates once and retries.

---

## Environment Variables

| Variable | Default | Required | Purpose |
|---|---|---|---|
| `PB_BASE_URL` | — | ✓ | PocketBase instance URL |
| `PB_ADMIN_EMAIL` | — | ✓ | Admin authentication email |
| `PB_ADMIN_PASSWORD` | — | ✓ | Admin authentication password |
| `PB_ORICLI_EMAIL` | `oricli@thynaptic.com` | — | Oricli's analyst account email |
| `PB_ORICLI_PASSWORD` | `OricliSovereign2026!` | — | Oricli's analyst account password |
| `PB_MEMORY_MAX_RECORDS` | `500000` | — | Recycle threshold for `memories` |

If `PB_BASE_URL` is unset, `MemoryBank` operates in disabled no-op mode — all writes are silently dropped, reads return empty. The system functions normally without PocketBase; it simply lacks cross-session recall.

---

## Go Package Reference

```
pkg/connectors/pocketbase/
├── client.go   — REST client (NewClientFromEnv, NewUserClient, CRUD ops)
└── setup.go    — Bootstrap, collection schemas, CreateOricliUser

pkg/service/
└── memory_bank.go — MemoryBank service (Write, QuerySimilar, Recycle,
                     WriteKnowledgeFragment, PersistSpend, LoadSpend,
                     SaveConversationSummary, FormatRAGContext)
```

### Key methods

```go
mb := service.NewMemoryBank()

// Bootstrap (call once at startup)
mb.Bootstrap(ctx)

// Write a memory (async, non-blocking)
mb.Write(MemoryFragment{Content: "...", Source: "conversation", Topic: "golang", Importance: 0.6})

// Curiosity finding (writes as oricli, async)
mb.WriteKnowledgeFragment("goroutines", "TECHNICAL", "3-5 fact summary...", 0.7)

// RAG query (synchronous, < 10s timeout)
frags, _ := mb.QuerySimilar(ctx, userMessage, 5)
ragCtx   := service.FormatRAGContext(frags, 1200)

// Spend tracking
mb.LoadSpend(ctx, "inference", "2026-03")  // → float64
mb.PersistSpend("inference", "2026-03", 4.72)  // async

// Recycle old memories (async)
mb.Recycle()
```
