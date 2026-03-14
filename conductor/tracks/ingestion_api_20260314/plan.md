# Implementation Plan: Sovereign Ingestion API

## Phase 1: Ingestion Agent Module
- [ ] Create `oricli_core/brain/modules/ingestion_agent.py`.
- [ ] Implement PDF parsing using `pypdf`.
- [ ] Implement recursive character text splitter.
- [ ] Implement `ingest_document` operation that handles the full pipeline (Parse -> Chunk -> Embed -> Store).
- [ ] Integrate with `world_knowledge` and `neo4j` for storage.

## Phase 2: API & Models
- [ ] Add `IngestRequest`, `IngestResponse` to `oricli_core/types/models.py`.
- [ ] Implement `POST /v1/ingest` in `oricli_core/api/server.py` using FastAPI's `UploadFile`.

## Phase 3: Client & Infrastructure
- [ ] Install dependencies: `pip install pypdf`.
- [ ] Update `OricliAlphaClient` with `ingest` method in `Knowledge` class.
- [ ] Create `docs/INGESTION_API.md`.

## Phase 4: Validation
- [ ] Write `scripts/test_ingestion_api.py` to verify PDF and text ingestion.
- [ ] Perform a RAG test to ensure the ingested data is retrieved during chat completions.
