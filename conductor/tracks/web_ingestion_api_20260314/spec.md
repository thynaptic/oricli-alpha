# Specification: Sovereign Web Ingestion API (Crawler Bridge)

## Objective
To enable Oricli-Alpha to autonomously crawl and ingest online content (articles, blogs, documentation) via the Native API. This extends the existing RAG bridge to include dynamic web sources, allowing the Hive to ingest entire websites or specific articles for context.

## Background
Oricli-Alpha can currently ingest static files (PDF, TXT). Adding a web crawler allows for real-time knowledge acquisition from the open web. An external HUD should be able to provide a seed URL and a page limit, and Oricli will handle the crawling, extraction, and indexing.

## Requirements

### 1. Web Ingestion Agent Module (`web_ingestion_agent`)
A new brain module specialized in web crawling and data processing:
- **Crawling:** Breadth-first traversal starting from a seed URL.
- **Link Extraction:** Identifying internal links to follow, while staying within the same domain.
- **Content Extraction:** Using `readability-lxml` or `beautifulsoup4` to strip boilerplate (ads, navbars) and get clean text.
- **Pipeline Integration:** Feeding extracted text into the `ingestion_agent` for chunking, embedding, and storage.

### 2. REST API Endpoint (`POST /v1/ingest/web`)
A new endpoint in `server.py` that accepts:
- `url`: The seed URL to start crawling.
- `max_pages`: Total number of pages to ingest (default: 5).
- `max_depth`: Max clicks from the seed (default: 2).
- `metadata`: Tags, domain, and priority.

### 3. Pydantic Models
Add `WebIngestRequest` and `WebIngestResponse` to `models.py`.

### 4. Client Integration
Extend `OricliAlphaClient` with `client.knowledge.ingest_web()`.

## Success Criteria
- User provides a blog URL and Oricli successfully ingests the latest 5 posts.
- The content is indexed and searchable via `oricli-swarm` chat completions.
- The crawler respects domain boundaries and provides a summary of URLs processed.
