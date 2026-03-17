# Implementation Plan: Sovereign Ingestion API Completion

This plan completes the Sovereign Ingestion API (RAG Bridge) by fixing Go-native file handling and enhancing the Python Ingestion Agent.

## Phase 1: Go API Fixes
- [ ] Modify `pkg/api/server.go`: Update `handleIngest` to read the actual file bytes from the multipart form.
  - Open the file using `file.Open()`.
  - Read all bytes using `io.ReadAll()`.
  - Pass the bytes to `params["file_data"]`.
- [ ] Rebuild Go backbone: `go build -o bin/oricli-go ./cmd/backbone`.

## Phase 2: Ingestion Agent Enhancements
- [ ] Update `oricli_core/brain/modules/ingestion_agent.py`:
  - Enhance `_parse_file` to support `PyPDF2` if `pypdf` is missing.
  - Implement a better `_recursive_character_splitter` that uses a list of separators (e.g., `["\n\n", "\n", ". ", " ", ""]`).
  - Improve `_process_chunks` to correctly track and link chunks in Neo4j.

## Phase 3: Infrastructure & Documentation
- [ ] Ensure `pypdf` or `PyPDF2` is installed in the environment.
- [ ] Review and update `docs/INGESTION_API.md` to reflect the latest capabilities.

## Phase 4: Validation
- [ ] Create `scripts/test_ingestion_rag.py`:
  - Ingest a specific unique text/PDF.
  - Ask a question that requires that specific knowledge.
  - Verify that the answer contains the ingested info.
- [ ] Test via `OricliAlphaClient` in both local and remote modes.
