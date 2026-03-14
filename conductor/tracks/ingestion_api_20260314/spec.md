# Specification: Sovereign Ingestion API (RAG Bridge)

## Objective
To enable Oricli-Alpha to ingest external knowledge sources (PDFs, Markdown, Text files) via the Native API. This data will be parsed, chunked, embedded, and stored in her Knowledge Graph and Memory stores, making it instantly accessible to all micro-agents in The Hive.

## Background
Oricli-Alpha has powerful retrieval capabilities but lacks a unified gateway for external data ingestion. Currently, "World Knowledge" is mostly static or manually added. This API bridge allows a HUD or external process to "feed" Oricli new information dynamically.

## Requirements

### 1. Ingestion Agent Module (`ingestion_agent`)
A new brain module responsible for the ingestion pipeline:
- **Parsing:** Extracting clean text from multiple formats (PDF, MD, TXT).
- **Chunking:** Semantic or recursive character-based splitting to maintain context.
- **Embedding:** Generating vector representations for each chunk via the internal `embeddings` module.
- **Storage:**
    - Sync chunks to `MemoryBridgeService` (LMDB).
    - Sync facts/entities to `world_knowledge`.
    - Link relationships in `MemoryGraph` (Neo4j).

### 2. REST API Endpoint (`POST /v1/ingest`)
A new endpoint in `server.py` that accepts:
- `file`: Multipart upload for documents.
- `text`: Direct text string ingestion.
- `metadata`: Source name, tags, and domain context.

### 3. Pydantic Models
Add `IngestRequest`, `IngestResponse`, and `IngestChunk` models to `models.py`.

### 4. Client Integration
Extend `OricliAlphaClient` with `client.knowledge.ingest()` supporting both file paths and raw text.

## Success Criteria
- PDF files can be uploaded and their content becomes searchable via `client.chat.completions` (RAG).
- Multi-hop relationship queries in Neo4j reflect the ingested knowledge.
- Ingestion process provides a progress/summary response (chunks created, entities found).
