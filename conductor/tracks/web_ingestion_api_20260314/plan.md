# Implementation Plan: Web Ingestion API (Crawler Bridge)

## Phase 1: Web Ingestion Agent Module
- [ ] Create `oricli_core/brain/modules/web_ingestion_agent.py`.
- [ ] Implement BFS crawling logic with `max_pages` and `max_depth` constraints.
- [ ] Integrate with `web_scraper` for high-quality text extraction (Readability).
- [ ] Implement `crawl_and_ingest` operation that iterates through URLs and calls `ingestion_agent.ingest_text` for each.

## Phase 2: API & Models
- [ ] Add `WebIngestRequest` and `WebIngestResponse` to `oricli_core/types/models.py`.
- [ ] Implement `POST /v1/ingest/web` in `oricli_core/api/server.py`.

## Phase 3: Client Integration
- [ ] Update `OricliAlphaClient` with `ingest_web` method in `Knowledge` class.
- [ ] Add a sample script `scripts/test_web_ingestion.py`.

## Phase 4: Validation
- [ ] Verify that Oricli can crawl a specific technical blog and retrieve facts from it in a swarm deliberation.
- [ ] Update `docs/INGESTION_API.md` with the new web crawling section.
