# Oricli-Alpha API Documentation (v0.5.0-alpha)

Complete API documentation for the Oricli-Alpha Sovereign Agent OS. The API is powered by a high-performance Go-native backbone optimized for 32-core EPYC environments.

## Base URL

- Production: `https://oricli.thynaptic.com`
- Local: `http://localhost:8089`

## Authentication

API key authentication is configurable. Configure via:

- Environment variable: `MAVAIA_API_KEY` - Set the API key
- Header: `Authorization: Bearer <api-key>` - Provide API key in request header

## 🚀 Sovereign Hive Endpoints

### Swarm Run (Direct Execution)

Execute a task across the swarm with automated micro-agent selection and bidding.

**Endpoint:** `POST /v1/swarm/run`

**Request:**
```json
{
  "operation": "reason",
  "params": {
    "query": "How does the AMD EPYC 7543P optimize for Go-native concurrency?",
    "complexity": 0.8
  }
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "swarm_task_1773685691",
  "result": {
    "answer": "The EPYC 7543P provides 32 high-performance cores that the Go backbone utilizes through native Goroutines...",
    "confidence": 0.98,
    "agent_id": "mcts_reasoning_go"
  }
}
```

### Swarm Inject (Manual Message)

Inject a custom message directly into the Swarm Bus.

**Endpoint:** `POST /v1/swarm/inject`

**Request:**
```json
{
  "topic": "tasks.cfp",
  "protocol": "broadcast",
  "payload": {
    "task_id": "manual_123",
    "operation": "analyze_code"
  }
}
```

## 🎯 Sovereign Goals

### List Goals

Retrieve all persistent sovereign goals.

**Endpoint:** `GET /v1/goals`

### Create Goal

Initialize a new autonomous goal for the system.

**Endpoint:** `POST /v1/goals`

**Request:**
```json
{
  "title": "Migrate core logic to Go",
  "description": "Port 250+ Python modules to the Go backbone for 32-core optimization.",
  "priority": 10
}
```

## 🤖 Agent Factory

### List Agents

List all active agent profiles and their specialized skills.

**Endpoint:** `GET /v1/agents`

### Create Agent

Register a new specialized micro-agent profile.

**Endpoint:** `POST /v1/agents`

## 🧠 Intelligence Services

### Code Review

Analyze code for quality, performance, and security.

**Endpoint:** `POST /v1/code/review`

### Document Analysis

Perform deep analysis and summarization of text documents.

**Endpoint:** `POST /v1/documents/analyze`

**Request:**
```json
{
  "text": "Full document text here...",
  "file_name": "architecture_v2.md"
}
```

## 🔍 System Introspection

### Detailed Health

Get detailed status, uptime, and performance metrics for all Go-native and Python sidecar modules.

**Endpoint:** `GET /v1/health/detailed`

### System Metrics

Retrieve real-time execution counts, latencies, and success rates for the entire swarm.

**Endpoint:** `GET /v1/metrics`

### Execution Traces

Access the high-speed Go ring-buffer of recent task execution traces.

**Endpoint:** `GET /v1/traces`

## 🧪 Stress Testing

### Scream Test

Fire 100 parallel orchestrated tasks across the swarm to verify 32-core EPYC saturation.

**Endpoint:** `POST /v1/stress/scream`

##  OpenAI-Compatible Endpoints

Oricli-Alpha maintains compatibility with existing AI tooling via OpenAI-style aliases.

- `POST /v1/chat/completions` -> Routes to `GoAgentService`
- `POST /v1/embeddings` -> Routes to `EmbeddingEngine` (Go-proxied to Ollama)
- `GET /v1/models` -> Returns active Hive model list

## Error Responses

Errors return standard HTTP status codes and a JSON error body:

```json
{
  "success": false,
  "error": "Internal server error: GIL contention detected in Python sidecar",
  "code": 500
}
```

---
*Oricli-Alpha: Intelligence, Orchestrated.*
