# RAG — consumer capsule (BM25 only)

Local retrieval for ori-capsule. **No chromem, PocketBase MemoryBank, Ollama embeds, or sync chat-path RAG.**

Those VPS paths (including the ≤8s MemoryBank retrieve) stay on the host. Capsule gets the **100% portable** slice: sectioning, incremental manifests, BM25, local SSRF URL policy, and `RagContentGuard` on ingest.

## Surface

| Endpoint | Role |
|---|---|
| `GET /v1/rag` | Stats + contract |
| `POST /v1/rag/ingest` | Index `text` or local `path` |
| `POST /v1/rag/ingest/file` | Multipart upload (`file`, optional `source` / `metadata` JSON); 2 MiB max |
| `POST /v1/rag/query` | BM25 hits + formatted context |

Chat inject is **opt-in** so default TTFT stays unchanged:

```
X-Ori-RAG: bm25
```

Without that header, chat never touches the BM25 index.

## Ingest

```bash
curl -s http://localhost:8089/v1/rag/ingest \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"source":"notes.md","text":"# Setup\nBM25 ranks by keywords.\n"}'
```

Or `{"path":"/absolute/or/container/path.txt"}`. Content is scanned with `RagContentGuard` before indexing. Chunks live under `$ORI_MEMORY_DIR/rag/chunks.json`.

### Multipart file

```bash
curl -s http://localhost:8089/v1/rag/ingest/file \
  -H "Authorization: Bearer $KEY" \
  -F "file=@./notes.md" \
  -F "source=notes.md" \
  -F 'metadata={"kind":"doc"}'
```

## Query

```bash
curl -s http://localhost:8089/v1/rag/query \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"BM25 keywords","top_k":5}'
```

## Helpers (library)

| Piece | Package | Notes |
|---|---|---|
| `ChunkText` / `InferChunkSections` | `internal/rag` | Markdown-aware windows |
| `IncrementalManifest` | `internal/rag` | Fingerprints for re-ingest tooling |
| `BM25Index` | `internal/rag` | Pure Go Okapi BM25 |
| `ValidateFetchURL` | `internal/rag` | Local SSRF policy (not urlscan.io) |

## Explicitly not here

- MemoryBank / PocketBase cold RAG (sync ≤8s chat path)
- Spaces chromem + Ollama query embeds
- Enterprise RAG / twins
- urlscan.io (needs API key) — use `ValidateFetchURL` only

## Env

Uses `ORI_MEMORY_DIR` for persistence (same volume as consumer memory). No extra RAG-specific env required for v0.
