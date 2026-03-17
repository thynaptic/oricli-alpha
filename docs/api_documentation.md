# Oricli-Alpha API Documentation (v2.1.0)

Complete API documentation for the Oricli-Alpha Sovereign Agent OS. The API is powered by a high-performance, 100% Go-native backbone optimized for 32-core EPYC environments and multi-modal GPU-accelerated inference.

## 🌐 External Access & Connectivity

To use Oricli-Alpha from outside the VPS, you must ensure the backbone port (`8089` by default) is accessible or proxied via Caddy/Nginx.

- **Base URL:** `http://<vps-ip>:8089` or `https://oricli.thynaptic.com`
- **Port:** `8089` (Native Go Gateway)

### Client Libraries
- **Python**: Use the `OricliClient` provided in `oricli_client.py`.
- **HTTP**: Any standard client (curl, requests, etc.) can interact with the JSON API.

## 🛡️ Authentication & Multi-Tenancy

Oricli v2.1.0 uses a hardened authentication layer based on the G-LM architecture.

- **Header**: `Authorization: Bearer <your-api-key>`
- **Header**: `X-Tenant-ID: <tenant-id>` (Defaults to `local`)

Example Header:
```http
Authorization: Bearer test_key
X-Tenant-ID: local
```

---

## 🚀 Swarm Execution (The Hive)

Execute specialized tasks across the distributed micro-agent swarm.

**Endpoint:** `POST /v1/swarm/run`

### Common Operations:

#### 1. `reason` (General Logic)
```json
{
  "operation": "reason",
  "params": {
    "query": "Analyze the impact of Go-native concurrency on agent latency.",
    "complexity": 0.9
  }
}
```

#### 2. `research_task` (Autonomous Research)
Triggers the `research_agent` to perform deep analysis and synthesis.
```json
{
  "operation": "research_task",
  "params": {
    "query": "Latest breakthroughs in multi-modal LLM quantization."
  }
}
```

#### 3. `solve_arc` (AGI Benchmarking)
Triggers the Go-native MCTS solver for ARC-AGI tasks.
```json
{
  "operation": "solve_arc",
  "params": {
    "task": { ...ARC JSON... }
  }
}
```

---

## 👁️ Multi-Modal Ingestion

Oricli-Alpha can "see" and "read" natively into its long-term memory.

### Web Ingestion (Crawl)
**Endpoint:** `POST /v1/ingest/web`
```json
{
  "url": "https://thynaptic.com",
  "max_pages": 5,
  "max_depth": 2
}
```

### File & Image Ingestion
**Endpoint:** `POST /v1/ingest`
- **Method**: `POST` (multipart/form-data)
- **Field**: `file` (Binary blob or Image)

*Note: If an image is uploaded, the `vision_agent` (Qwen2-VL) automatically transcribes it before indexing.*

---

## 🕰️ Chronological Memory & History

Every interaction is grounded in a Neo4j-backed temporal graph.

### Get History
**Endpoint:** `POST /v1/swarm/run`
```json
{
  "operation": "get_history",
  "params": {
    "limit": 10
  }
}
```

---

## 🎯 Sovereign Goals

### List Goals
**Endpoint:** `POST /v1/swarm/run`
```json
{
  "operation": "list_objectives",
  "params": { "status": "pending" }
}
```

### Add Goal
```json
{
  "operation": "add_objective",
  "params": {
    "goal": "Optimize Neo4j relationship traversal for temporal lookups.",
    "priority": 8
  }
}
```

---

## 🤖 OpenAI-Compatible Interface

Oricli-Alpha maintains drop-in compatibility for existing AI tooling.

### Chat Completions
**Endpoint:** `POST /v1/chat/completions`
```json
{
  "model": "oricli-cognitive",
  "messages": [{"role": "user", "content": "Explain the AGLI trajectory."}]
}
```

---

## 🔍 System Health

### Readiness Check
**Endpoint:** `GET /v1/health`
**Response:**
```json
{
  "status": "ready",
  "system": "oricli-alpha-v2",
  "pure_go": true
}
```

---
*Oricli-Alpha: Sovereign Intelligence, Orchestrated at Scale.*
