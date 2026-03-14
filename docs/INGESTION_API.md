# Oricli-Alpha Sovereign Ingestion API (RAG Bridge)

## Overview
The **Sovereign Ingestion API** allows external systems to "feed" Oricli-Alpha new information from documents (PDF, MD, TXT) or raw text. Ingested data is automatically parsed, chunked, embedded, and indexed in her Knowledge Graph and Memory stores, making it instantly available for RAG (Retrieval-Augmented Generation) across all micro-agents in the Hive.

## 1. Using the REST API

Port: `8081` (default)

### Ingest a Document (Multipart Upload)
`POST /v1/ingest`

**Parameters:**
- `file`: (Optional) Multipart file upload (PDF, TXT, MD).
- `text`: (Optional) Raw text string (use if `file` is not provided).
- `source`: (Optional) String name of the source.
- `tags`: (Optional) JSON string of a list of tags (e.g., `["security", "report"]`).
- `domain`: (Optional) Knowledge domain.

**Example (cURL):**
```bash
curl -X POST http://localhost:8081/v1/ingest \
  -H "Authorization: Bearer test_key" \
  -F "file=@document.pdf" \
  -F "tags=[\"external\", \"research\"]" \
  -F "domain=genetics"
```

### Ingest Raw Text
`POST /v1/ingest`

**Example (cURL):**
```bash
curl -X POST http://localhost:8081/v1/ingest \
  -H "Authorization: Bearer test_key" \
  -F "text=The new fusion reactor was successfully tested in Switzerland." \
  -F "source=lab_report_01"
```

---

## 2. Using the Python Client

The `OricliAlphaClient` exposes the factory via the `knowledge.ingest()` method.

```python
from oricli_core.client import OricliAlphaClient

client = OricliAlphaClient(base_url="http://localhost:8081", api_key="your_key")

# Ingest a PDF file
res = client.knowledge.ingest(
    file_path="path/to/research.pdf",
    metadata={"tags": ["AI", "Paper"], "domain": "Science"}
)

# Ingest raw text
client.knowledge.ingest(
    text="Fact: Oricli uses a distributed swarm architecture.",
    metadata={"source": "manual_entry"}
)
```

---

## 3. Deployment & Retrieval
Once ingested, the content is automatically chunked into ~1000 character segments with overlap. These chunks are embedded and stored.

Any subsequent call to `client.chat.completions.create` using the `oricli-swarm` or `oricli-hive` models will automatically perform a semantic search over these chunks and inject relevant context into the model's prompt.

**Example Retrieval:**
```python
# The Hive will now know about the fusion reactor ingested earlier
response = client.chat.completions.create(
    model="oricli-swarm",
    messages=[{"role": "user", "content": "Tell me about the fusion test in Switzerland."}]
)
```
