# ORI Studio Developer Guide

**Version:** v11.0.0 — Thynaptic Research  
**API Base URL:** `https://oricli.thynaptic.com`

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Your API Key](#2-getting-your-api-key)
3. [Base URLs](#3-base-urls)
4. [Authentication](#4-authentication)
5. [OpenAI Compatibility](#5-openai-compatibility)
6. [Core Use Cases](#6-core-use-cases)
7. [SDK Examples](#7-sdk-examples)
8. [Cognitive Intelligence Layer](#8-cognitive-intelligence-layer)
9. [PAD — Parallel Agent Dispatch](#9-pad--parallel-agent-dispatch)
10. [Sovereign Goals Engine](#10-sovereign-goals-engine)
11. [Metacognitive Sentience](#11-metacognitive-sentience)
12. [Chronos — Temporal Grounding](#12-chronos--temporal-grounding)
13. [Science Engine — Hypothesis Testing](#13-science-engine--hypothesis-testing)
14. [FineTune — LoRA Training](#14-finetune--lora-training)
15. [Forge — JIT Tool Forge](#15-forge--jit-tool-forge)
16. [Crystal Cache — Skill Crystallization](#16-crystal-cache--skill-crystallization)
17. [Curator — Sovereign Model Curation](#17-curator--sovereign-model-curation)
18. [Audit — Self-Audit Loop](#18-audit--self-audit-loop)
19. [SCL — Sovereign Cognitive Ledger](#19-scl--sovereign-cognitive-ledger)
20. [TCD — Temporal Curriculum Daemon](#20-tcd--temporal-curriculum-daemon)
21. [Compute](#21-compute)
22. [WebSocket Real-Time State](#22-websocket-real-time-state)
23. [Rate Limits & Quotas](#23-rate-limits--quotas)
24. [Error Reference](#24-error-reference)
25. [Support](#25-support)

---

## 1. Introduction

ORI Studio is a sovereign AI inference and reasoning system built on a pure-Go backbone. Unlike standard LLM APIs that proxy to a third-party service, ORI Studio runs its own 28-layer cognitive pre-generation pipeline before a single token is produced — incorporating therapy-grounded distortion detection, Socratic reasoning validation, polyvagal-informed affect modulation, metacognitive oversight, and epistemic hygiene checks.

**Key differentiators:**

- **Sovereign & local-first** — no external OpenAI dependency; your data never leaves the pipeline you configure.
- **OpenAI-compatible** — drop-in replacement for the OpenAI Chat Completions API; swap `base_url` and you're done.
- **28-layer cognitive pre-gen** — each response is pre-processed through modules spanning CBT, MBCT, logotherapy, Stoic philosophy, narrative therapy, polyvagal theory, and more.
- **Autonomous goal execution** — submit long-horizon goals via the DAG goal executor and poll for results.
- **Real-time state streaming** — subscribe to live resonance, sensory, and health events over WebSocket.
- **Enterprise RAG** — tenant-isolated knowledge ingestion and semantic search.

---

## 2. Getting Your API Key

API keys are issued by Thynaptic Research. To request access:

1. Visit [thynaptic.com](https://thynaptic.com) or email the team directly.
2. Provide your intended use case and expected volume.
3. You will receive a key in the format:

```
glm.<prefix>.<secret>
```

- `glm` — fixed key family identifier.
- `<prefix>` — short human-readable tenant/user identifier.
- `<secret>` — cryptographically random secret component.

**Keep your key confidential.** Do not commit it to source control or expose it in client-side code.

---

## 3. Base URLs

| Environment | URL |
|-------------|-----|
| Production | `https://oricli.thynaptic.com` |
| Local development | `http://localhost:8089` |

All endpoints are rooted at `/v1/`.

---

## 4. Authentication

Pass your key as a Bearer token in the `Authorization` header on every protected request:

```
Authorization: Bearer glm.<prefix>.<secret>
```

Public endpoints (health, ERI state, WebSocket, modules list) do not require authentication.

**Example:**
```bash
curl https://oricli.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer glm.myapp.abc123xyz" \
  -H "Content-Type: application/json" \
  -d '{"model":"oricli-alpha","messages":[{"role":"user","content":"Hello"}]}'
```

An invalid or missing token returns `401 Unauthorized`:
```json
{
  "error": {
    "message": "invalid token",
    "type": "authentication_error",
    "code": 401
  }
}
```

---

## 5. OpenAI Compatibility

`POST /v1/chat/completions` is a drop-in replacement for the OpenAI Chat Completions API. Any client that supports a configurable `base_url` works without code changes.

**Python (openai SDK):**
```python
import openai

client = openai.OpenAI(
    base_url="https://oricli.thynaptic.com/v1",
    api_key="glm.<prefix>.<secret>",
)

response = client.chat.completions.create(
    model="oricli-alpha",
    messages=[{"role": "user", "content": "Summarise the CAP theorem"}],
)
print(response.choices[0].message.content)
```

**JavaScript (openai SDK):**
```javascript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://oricli.thynaptic.com/v1",
  apiKey: "glm.<prefix>.<secret>",
});

const response = await client.chat.completions.create({
  model: "oricli-alpha",
  messages: [{ role: "user", content: "Summarise the CAP theorem" }],
});
console.log(response.choices[0].message.content);
```

**Sovereign extensions** beyond the OpenAI spec:

| Field | Type | Description |
|-------|------|-------------|
| `profile` | string | `.ori` manifest filename to hot-swap the AI's personality/soul configuration |
| `reasoning` | bool | Enable extended reasoning trace in the response |

---

## 6. Core Use Cases

### 6a. Chat

#### Basic chat

```bash
curl -s https://oricli.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "oricli-alpha",
    "messages": [
      {"role": "system", "content": "You are a concise technical assistant."},
      {"role": "user", "content": "What is gradient descent?"}
    ]
  }'
```

#### Streaming chat

Set `"stream": true`. The response is delivered as Server-Sent Events (SSE) in the OpenAI chunk format:

```bash
curl -s https://oricli.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "oricli-alpha",
    "messages": [{"role": "user", "content": "Write a haiku about distributed systems"}],
    "stream": true
  }'
```

Each SSE line:
```
data: {"id":"chatcmpl-x","object":"chat.completion.chunk","choices":[{"delta":{"content":"Nodes"},"index":0}]}
```

Terminal chunk:
```
data: [DONE]
```

#### Chat with tools (function calling)

```bash
curl -s https://oricli.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "oricli-alpha",
    "messages": [{"role": "user", "content": "What is the stock price of AAPL?"}],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_stock_price",
          "description": "Get the current stock price for a ticker symbol",
          "parameters": {
            "type": "object",
            "properties": {
              "ticker": {"type": "string", "description": "Stock ticker symbol"}
            },
            "required": ["ticker"]
          }
        }
      }
    ],
    "tool_choice": "auto"
  }'
```

When the model invokes a tool, `finish_reason` is `"tool_calls"` and the response includes a `tool_calls` array. Execute the function on your side and submit results back in a follow-up message with `role: "tool"`.

---

### 6b. Goal Management

The DAG goal executor accepts long-horizon goals and runs them autonomously. Poll for completion.

**Create a goal:**
```bash
curl -s -X POST https://oricli.thynaptic.com/v1/goals \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Competitive analysis report",
    "description": "Research the top 5 AI API providers and produce a structured comparison covering pricing, capabilities, and rate limits",
    "priority": "high"
  }'
```

**Response:**
```json
{
  "id": "goal_xyz789",
  "title": "Competitive analysis report",
  "status": "pending",
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Poll for completion:**
```bash
curl -s https://oricli.thynaptic.com/v1/goals/goal_xyz789 \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

```json
{
  "id": "goal_xyz789",
  "status": "complete",
  "progress": 1.0,
  "result": "## Competitive Analysis\n\n| Provider | ... |"
}
```

`status` values: `pending` | `running` | `complete` | `failed` | `cancelled`

**Cancel a goal:**
```bash
curl -s -X DELETE https://oricli.thynaptic.com/v1/goals/goal_xyz789 \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```
Returns `204 No Content`.

---

### 6c. Knowledge Ingestion

Ingest a document and retrieve it semantically.

**Upload a file:**
```bash
curl -s -X POST https://oricli.thynaptic.com/v1/documents/upload \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -F "file=@quarterly_report.pdf"
```

```json
{
  "document_id": "doc_a1b2c3",
  "filename": "quarterly_report.pdf",
  "status": "ingested"
}
```

**Ingest raw text:**
```bash
curl -s -X POST https://oricli.thynaptic.com/v1/ingest \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "ORI Studio v11 introduces the PAD parallel dispatch system...",
    "title": "v11 release notes"
  }'
```

**Ingest a web URL:**
```bash
curl -s -X POST https://oricli.thynaptic.com/v1/ingest/web \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

**Search knowledge:**
```bash
curl -s "https://oricli.thynaptic.com/v1/memories/knowledge?q=quarterly+revenue&limit=5" \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

```json
{
  "memories": [
    {
      "id": "mem_001",
      "content": "Q3 revenue was $4.2M, up 18% YoY.",
      "type": "knowledge",
      "created_at": "2025-01-01T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

### 6d. Vision Analysis

Send an image URL for moondream-powered visual description.

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/vision/analyze \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://example.com/diagram.png",
    "prompt": "Describe the architecture shown in this diagram"
  }'
```

```json
{
  "description": "The diagram shows a three-tier microservices architecture with an API gateway layer...",
  "model": "moondream"
}
```

---

### 6e. Enterprise RAG

Tenant-isolated knowledge base. Each namespace is siloed from all others.

**Ingest documents into a namespace:**
```bash
curl -s -X POST https://oricli.thynaptic.com/v1/enterprise/learn \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "acme-corp",
    "content": "ACME internal policy: all expenses over $500 require VP approval.",
    "title": "Expense Policy"
  }'
```

**Response:**
```json
{
  "job_id": "job_ent_abc",
  "status": "queued",
  "poll": "/v1/enterprise/learn/job_ent_abc"
}
```

**Poll job status:**
```bash
curl -s https://oricli.thynaptic.com/v1/enterprise/learn/job_ent_abc \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

**Semantic search within a namespace:**
```bash
curl -s "https://oricli.thynaptic.com/v1/enterprise/knowledge/search?q=expense+approval&namespace=acme-corp&top_k=3" \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

**Clear a namespace:**
```bash
curl -s -X DELETE "https://oricli.thynaptic.com/v1/enterprise/knowledge?namespace=acme-corp" \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

## 7. SDK Examples

### Python (openai SDK)

```python
import openai

client = openai.OpenAI(
    base_url="https://oricli.thynaptic.com/v1",
    api_key="glm.<prefix>.<secret>",
)

# Basic chat
response = client.chat.completions.create(
    model="oricli-alpha",
    messages=[{"role": "user", "content": "Explain monads in plain English"}],
)
print(response.choices[0].message.content)

# Streaming
stream = client.chat.completions.create(
    model="oricli-alpha",
    messages=[{"role": "user", "content": "Write a product description for a standing desk"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

### JavaScript (openai SDK)

```javascript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://oricli.thynaptic.com/v1",
  apiKey: "glm.<prefix>.<secret>",
});

// Basic chat
const response = await client.chat.completions.create({
  model: "oricli-alpha",
  messages: [{ role: "user", content: "Explain monads in plain English" }],
});
console.log(response.choices[0].message.content);

// Streaming
const stream = await client.chat.completions.create({
  model: "oricli-alpha",
  messages: [{ role: "user", content: "Write a product description for a standing desk" }],
  stream: true,
});
for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta?.content ?? "");
}
```

### Raw curl

```bash
# Health check (no auth)
curl -s https://oricli.thynaptic.com/v1/health

# Chat
curl -s -X POST https://oricli.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"model":"oricli-alpha","messages":[{"role":"user","content":"Hello"}]}'

# List goals
curl -s https://oricli.thynaptic.com/v1/goals \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

## 8. Cognitive Intelligence Layer

Every chat completion request passes through a **28-layer cognitive pre-generation pipeline** before the response is produced. This is not post-processing — it shapes the generation itself.

The pipeline draws from multiple disciplines:

| Layer Group | Modules |
|-------------|---------|
| **Cognitive-Behavioural** | CBT schema detection, MBCT mindfulness gating, CBASP interpersonal context, Unified Protocol (UP) |
| **Philosophical** | Socratic reasoning validation, Stoic virtue filtering, logotherapy meaning-coherence |
| **Neuroscience** | Polyvagal arousal regulation, Default Mode Network (DMN) dampening, interference detection |
| **Therapeutic** | REBT disputation (B-pass), STOP skill invocation, helplessness signal detection, sycophancy detection |
| **Metacognitive** | Rumination detection, metacognitive therapy (MCT), mindset vector projection, coalition coherence |
| **Epistemic** | Epistemic hygiene checks, IUT (Intolerance of Uncertainty), ILM (Internal Logic Monitor) |
| **Temporal** | IPSRT rhythmic stability, Chronos temporal decay, phase-oriented sequencing |
| **Identity** | Pseudo-identity stabilisation, thought-reform resistance, sovereign identity anchoring |

The result is responses that are structurally grounded, epistemically honest, and free from common AI failure modes (sycophancy, catastrophising, learned helplessness, status bias, ideological capture).

### Therapy Cognitive Stack

The therapy subsystem exposes its own endpoints for direct introspection and use in clinical-adjacent applications:

| Endpoint | Description |
|----------|-------------|
| `GET /v1/therapy/events` | Event log — timestamped stream of all therapy module activations |
| `POST /v1/therapy/detect` | Classify a cognitive distortion in arbitrary input text |
| `POST /v1/therapy/abc` | Run REBT B-pass disputation on a belief statement |
| `POST /v1/therapy/fast` | Sycophancy detection pass |
| `POST /v1/therapy/stop` | Invoke STOP skill |
| `GET /v1/therapy/stats` | Current session stats across all therapy modules |
| `GET /v1/therapy/formulation` | Current case formulation for the session |
| `POST /v1/therapy/formulation/refresh` | Force a refresh of the case formulation |
| `GET /v1/therapy/mastery` | Mastery tracker — skill acquisition metrics across therapy modules |
| `POST /v1/therapy/helplessness/check` | Submit text for learned helplessness signal detection |
| `GET /v1/therapy/helplessness/stats` | Session-level learned helplessness detection statistics |

### Cognition Module Stats

All 28+ cognitive modules expose a `GET /v1/cognition/<module>/stats` endpoint for telemetry:

```
/v1/cognition/process/stats
/v1/cognition/load/stats
/v1/cognition/rumination/stats
/v1/cognition/mindset/stats
/v1/cognition/hope/stats
/v1/cognition/defeat/stats
/v1/cognition/conformity/stats
/v1/cognition/ideocapture/stats
/v1/cognition/coalition/stats
/v1/cognition/statusbias/stats
/v1/cognition/arousal/stats
/v1/cognition/interference/stats
/v1/cognition/mct/stats
/v1/cognition/mbt/stats
/v1/cognition/schema/stats
/v1/cognition/ipsrt/stats
/v1/cognition/ilm/stats
/v1/cognition/iut/stats
/v1/cognition/up/stats
/v1/cognition/cbasp/stats
/v1/cognition/mbct/stats
/v1/cognition/phaseoriented/stats
/v1/cognition/pseudoidentity/stats
/v1/cognition/thoughtreform/stats
/v1/cognition/apathy/stats
/v1/cognition/logotherapy/stats
/v1/cognition/stoic/stats
/v1/cognition/socratic/stats
/v1/cognition/narrative/stats
/v1/cognition/polyvagal/stats
/v1/cognition/dmn/stats
```

---

## 9. PAD — Parallel Agent Dispatch

The PAD system fans a query out to multiple agent subtasks running concurrently, then aggregates results according to the chosen strategy. This is useful for tasks that benefit from independent reasoning paths — consensus voting, speed-optimised single-winner selection, or full multi-perspective output.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/pad/dispatch` | Dispatch a query to N concurrent agents |
| `GET` | `/v1/pad/sessions` | List all PAD sessions |
| `GET` | `/v1/pad/sessions/:id` | Retrieve session result |
| `GET` | `/v1/pad/stats` | Aggregate PAD stats |

### Dispatch a query

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/pad/dispatch \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key risks of deploying LLMs in healthcare?",
    "agent_count": 3,
    "strategy": "consensus"
  }'
```

```json
{
  "session_id": "pad_a1b2c3",
  "status": "running"
}
```

**`strategy` values:**

| Value | Behaviour |
|-------|-----------|
| `consensus` | All agents run; results are merged into a consensus answer |
| `fastest` | All agents run; the first to complete wins and others are cancelled |
| `all` | All agents run; full per-agent results are returned in the response |

### Poll for results

```bash
curl -s https://oricli.thynaptic.com/v1/pad/sessions/pad_a1b2c3 \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

```json
{
  "session_id": "pad_a1b2c3",
  "status": "complete",
  "results": [
    {"agent": 0, "answer": "Key risk 1: hallucination of clinical facts..."},
    {"agent": 1, "answer": "Primary concern is liability when..."},
    {"agent": 2, "answer": "Regulatory compliance under HIPAA..."}
  ]
}
```

---

## 10. Sovereign Goals Engine

Two goal systems exist in ORI Studio. The **legacy DAG goals** (`/v1/goals`, documented in §6b) handle structured task graphs. **Sovereign Goals** (`/v1/sovereign/goals`) are the Phase 10 upgrade: they have deeper integration with the Hive agent swarm and Chronos temporal memory, and support finer-grained execution control including manual tick-stepping for debugging.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/sovereign/goals` | Create a sovereign goal |
| `GET` | `/v1/sovereign/goals` | List all sovereign goals |
| `GET` | `/v1/sovereign/goals/:id` | Poll goal status and result |
| `POST` | `/v1/sovereign/goals/:id/tick` | Manually advance execution one cycle |
| `DELETE` | `/v1/sovereign/goals/:id` | Cancel goal — returns `204 No Content` |

### Create a goal

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/sovereign/goals \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Market sizing analysis",
    "description": "Estimate the TAM for AI-assisted code review tools in 2025",
    "priority": "high"
  }'
```

`priority` values: `high` | `medium` | `low`

### Poll status

```bash
curl -s https://oricli.thynaptic.com/v1/sovereign/goals/sgoal_xyz \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

```json
{
  "id": "sgoal_xyz",
  "status": "running",
  "progress": 0.7,
  "result": null
}
```

`status` values: `pending` | `running` | `complete` | `failed` | `cancelled`

### Manual tick (debug)

`POST /v1/sovereign/goals/:id/tick` advances execution by one cycle without waiting for the scheduler. Useful for debugging stalled goals or stepping through execution in a test environment.

---

## 11. Metacognitive Sentience

ORI Studio continuously monitors its own reasoning process for pathological patterns — reasoning loops, internal contradictions, confidence drift, and output quality degradation. When an anomaly is detected, the metacognitive layer intervenes before the response is finalised.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/metacog/events` | Recent metacognitive events (anomalies, corrections) |
| `GET` | `/v1/metacog/stats` | Session-level stats: loop count, interventions, health score |
| `POST` | `/v1/metacog/scan` | Force a metacognitive scan on arbitrary text |

### Scan arbitrary text

Submit any text for metacognitive analysis outside of a chat session — useful for auditing external content or pre-screening inputs.

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/metacog/scan \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"text": "We must always act decisively and never second-guess ourselves."}'
```

```json
{
  "issues": [
    {
      "type": "absolutist_language",
      "severity": "medium",
      "span": "must always act decisively and never second-guess"
    }
  ],
  "health": 0.72
}
```

`health` is a `[0, 1]` score where `1.0` is clean and lower values indicate detected reasoning pathologies.

---

## 12. Chronos — Temporal Grounding

Chronos maintains a timestamped semantic memory graph so ORI Studio can reason about how world-state has changed over time. It drives temporal decay of stale knowledge, detects state-change events, and provides a queryable snapshot of the current world-model.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/chronos/entries` | List temporal memory entries (`?limit=N&since=ISO8601`) |
| `GET` | `/v1/chronos/snapshot` | Current temporal snapshot — world-state summary |
| `GET` | `/v1/chronos/changes` | Recent state changes detected by Chronos |
| `POST` | `/v1/chronos/decay-scan` | Trigger a memory relevance decay scan |
| `POST` | `/v1/chronos/snapshot` | Force a new snapshot to be generated immediately |

### Query entries since a timestamp

```bash
curl -s "https://oricli.thynaptic.com/v1/chronos/entries?limit=20&since=2025-01-01T00:00:00Z" \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

### Trigger decay scan

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/chronos/decay-scan \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

Returns a summary of entries marked stale or evicted.

---

## 13. Science Engine — Hypothesis Testing

The Science Engine enables ORI Studio to behave as an active inference system: it proposes hypotheses, tests them against available evidence, and maintains a persistent store of confirmed, refuted, and in-progress claims. This underpins epistemic self-improvement over time.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/science/hypotheses` | List stored hypotheses |
| `GET` | `/v1/science/hypotheses/:id` | Get hypothesis detail |
| `POST` | `/v1/science/test` | Submit a hypothesis for testing |
| `GET` | `/v1/science/stats` | Engine stats: total hypotheses, confirmed rate, active tests |

### List hypotheses

```bash
curl -s https://oricli.thynaptic.com/v1/science/hypotheses \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

```json
[
  {
    "id": "hyp_a1",
    "claim": "Reducing context window size below 2k tokens degrades multi-step reasoning.",
    "status": "confirmed",
    "confidence": 0.91
  },
  {
    "id": "hyp_b2",
    "claim": "Temperature above 1.2 increases creative output without loss of coherence.",
    "status": "testing",
    "confidence": 0.54
  }
]
```

`status` values: `testing` | `confirmed` | `refuted`

### Submit a hypothesis

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/science/test \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "claim": "Structured prompting reduces hallucination rate by more than 30%",
    "evidence": "Internal eval: 500 prompts, structured vs free-form. Hallucination rate 4.2% vs 6.8%."
  }'
```

The engine queues the hypothesis for evaluation and returns a hypothesis ID for polling via `GET /v1/science/hypotheses/:id`.

---

## 14. FineTune — LoRA Training

ORI Studio exposes a JIT LoRA fine-tuning pipeline. Submit a training job with a base model and dataset, then poll until the adapter is ready. Fine-tuned adapters are hot-loaded at inference time.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/finetune/run` | Start a fine-tuning job |
| `GET` | `/v1/finetune/status/:job_id` | Poll job status and training metrics |
| `GET` | `/v1/finetune/jobs` | List all fine-tuning jobs |

### Start a job

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/finetune/run \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:1.5b",
    "dataset": "s3://my-bucket/training-data.jsonl",
    "epochs": 3
  }'
```

```json
{
  "job_id": "ft_x9z3",
  "status": "queued"
}
```

### Poll status

```bash
curl -s https://oricli.thynaptic.com/v1/finetune/status/ft_x9z3 \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

```json
{
  "job_id": "ft_x9z3",
  "status": "running",
  "progress": 0.4,
  "loss": 1.23
}
```

`status` values: `queued` | `running` | `complete` | `failed`

---

## 15. Forge — JIT Tool Forge

The Forge enables ORI Studio to create, hot-load, and invoke new tools at runtime from a natural-language spec. Forged tools are persisted and available to the agent immediately without a restart.

> **Admin key required** for all Forge endpoints.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/forge/tools` | List all forged tools |
| `DELETE` | `/v1/forge/tools/:name` | Delete a forged tool |
| `GET` | `/v1/forge/tools/:name/source` | Retrieve the source of a forged tool |
| `POST` | `/v1/forge/tools/:name/invoke` | Invoke a forged tool with params |
| `GET` | `/v1/forge/stats` | Forge stats (total tools, invocation counts) |
| `POST` | `/v1/forge/forge` | Forge a new tool from a natural-language spec |

### Forge a new tool

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/forge/forge \
  -H "Authorization: Bearer glm.<admin-key>" \
  -H "Content-Type: application/json" \
  -d '{"spec": "A tool that converts CSV input to a JSON array of objects"}'
```

```json
{
  "name": "csv_to_json",
  "status": "forged",
  "source": "func CsvToJson(input string) (string, error) { ... }"
}
```

### Invoke a forged tool

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/forge/tools/csv_to_json/invoke \
  -H "Authorization: Bearer glm.<admin-key>" \
  -H "Content-Type: application/json" \
  -d '{"params": {"input": "name,age\nAlice,30\nBob,25"}}'
```

---

## 16. Crystal Cache — Skill Crystallization

The Crystal Cache is a hot in-memory skill store for instant lookup of frequently-used skill definitions. Skills registered here bypass the full cognitive pipeline for skill-resolution steps, reducing latency for known capabilities.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/skills/crystals` | List all cached skills |
| `POST` | `/v1/skills/crystals` | Register a skill in the cache |
| `DELETE` | `/v1/skills/crystals/:id` | Evict a skill from the cache |
| `GET` | `/v1/skills/crystals/stats` | Cache hit/miss statistics |

### Register a skill

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/skills/crystals \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sql_query_builder",
    "skill": "Constructs parameterised SQL SELECT statements from a JSON schema description.",
    "ttl": 3600
  }'
```

`ttl` is in seconds. Omit for a non-expiring entry.

---

## 17. Curator — Sovereign Model Curation

The Curator evaluates locally available models and maintains per-task-category performance scores, so ORI Studio can route inference requests to the best available model for a given workload automatically.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/curator/models` | List all models with their current performance scores |
| `POST` | `/v1/curator/benchmark` | Run a benchmark for a model/task pair |
| `GET` | `/v1/curator/recommendations` | Get the recommended model per task category |

### Run a benchmark

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/curator/benchmark \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma3:1b", "task": "chat"}'
```

Returns task/model score metrics including latency, quality rating, and pass rate on the internal eval suite.

### Get recommendations

```bash
curl -s https://oricli.thynaptic.com/v1/curator/recommendations \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

```json
{
  "chat": "qwen2.5-coder:7b",
  "code": "qwen2.5-coder:1.5b",
  "reasoning": "deepseek-r1:7b",
  "vision": "moondream"
}
```

---

## 18. Audit — Self-Audit Loop

ORI Studio continuously audits its own output quality. The Audit system scores recent responses against internal quality criteria (accuracy, epistemic calibration, sycophancy signals, coherence) and surfaces findings for operator review.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/audit/run` | Trigger an audit over a window of recent responses |
| `GET` | `/v1/audit/runs` | List all audit runs |
| `GET` | `/v1/audit/runs/:id` | Get run detail with findings |

### Trigger an audit

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/audit/run \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"target": "last_n_responses", "n": 10}'
```

Returns a run ID for polling via `GET /v1/audit/runs/:id`. Findings include per-response quality flags and an overall session health rating.

---

## 19. SCL — Sovereign Cognitive Ledger

The SCL is an immutable append-only log of every cognitive decision made during inference — which modules fired, what overrides were applied, and why. Designed for operator auditing, compliance, and post-hoc reasoning review.

> **Admin key required** for all SCL endpoints.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/scl/records` | Browse records (`?limit=N&offset=N`) |
| `GET` | `/v1/scl/search` | Search records (`?q=<term>`) |
| `DELETE` | `/v1/scl/records/:id` | Delete a record |
| `PATCH` | `/v1/scl/records/:id` | Annotate or revise a record |
| `GET` | `/v1/scl/stats` | Ledger stats (total records, size, oldest entry) |

### Browse records

```bash
curl -s "https://oricli.thynaptic.com/v1/scl/records?limit=50&offset=0" \
  -H "Authorization: Bearer glm.<admin-key>"
```

### Search

```bash
curl -s "https://oricli.thynaptic.com/v1/scl/search?q=sycophancy+override" \
  -H "Authorization: Bearer glm.<admin-key>"
```

---

## 20. TCD — Temporal Curriculum Daemon

The TCD is a background daemon that manages ORI Studio's self-study curriculum. It tracks which knowledge domains have been studied, identifies gaps, and prioritises future ingestion tasks. Useful for operators who want visibility into — or control over — what ORI is learning.

> **Admin key required** for all TCD endpoints.

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/tcd/domains` | List all tracked knowledge domains |
| `POST` | `/v1/tcd/domains` | Add a domain to the curriculum |
| `POST` | `/v1/tcd/tick` | Manually trigger a TCD tick (scheduling cycle) |
| `GET` | `/v1/tcd/gaps` | Current knowledge gap analysis |
| `GET` | `/v1/tcd/domains/:id/lineage` | Concept lineage for a specific domain |
| `GET` | `/v1/tcd/lineage` | Full concept evolution tree across all domains |

### Add a domain

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/tcd/domains \
  -H "Authorization: Bearer glm.<admin-key>" \
  -H "Content-Type: application/json" \
  -d '{"name": "quantum-computing", "priority": 0.8}'
```

`priority` is a `[0, 1]` float; higher values cause the TCD to schedule study time sooner.

### Trigger a tick

```bash
curl -s -X POST https://oricli.thynaptic.com/v1/tcd/tick \
  -H "Authorization: Bearer glm.<admin-key>"
```

Useful for forcing immediate curriculum re-evaluation after adding domains or ingesting new knowledge.

---

## 21. Compute

Public routes for observing the sovereign compute layer.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/v1/compute/bids/stats` | Public | Sovereign compute bid statistics |
| `GET` | `/v1/compute/governor` | Public | Current compute governor state |

### Compute bid stats

```bash
curl -s https://oricli.thynaptic.com/v1/compute/bids/stats
```

Returns aggregate statistics on compute bids in the sovereign dispatch layer — useful for monitoring load distribution.

### Governor state

```bash
curl -s https://oricli.thynaptic.com/v1/compute/governor
```

Returns the current state of the compute governor: throttle level, active workers, queue depth, and scheduling policy in effect.

---

## 22. WebSocket Real-Time State

Connect to `wss://oricli.thynaptic.com/v1/ws` to receive a live stream of ORI Studio's internal state. No authentication is required.

```javascript
const ws = new WebSocket("wss://oricli.thynaptic.com/v1/ws");

ws.onmessage = (event) => {
  const frame = JSON.parse(event.data);
  switch (frame.type) {
    case "resonance_sync":
      console.log("ERI:", frame.data.eri, "Key:", frame.data.key);
      break;
    case "health_sync":
      console.log("CPU:", frame.data.cpu, "RAM:", frame.data.ram);
      break;
    case "audio_sync":
      playWav(frame.data.wav_b64); // base64-encoded WAV
      break;
  }
};
```

### Event Reference

| Event | Payload Fields | Description |
|-------|----------------|-------------|
| `resonance_sync` | `eri`, `ers`, `key` | Real-time Emotional Resonance Index, Emotional Resonance Score, and musical key |
| `sensory_sync` | `hex`, `opacity`, `pulse` | Hex colour, opacity, and pulse rate for UI rendering |
| `health_sync` | `cpu`, `ram`, `cognitive_health` | Substrate diagnostics and cognitive health status |
| `audio_sync` | `wav_b64` | Base64-encoded WAV audio for Affective Voice Synthesis |
| `curiosity_sync` | `target`, `priority` | Live epistemic foraging target and its priority score |
| `reform_proposal` | `diff`, `auto_deploy` | ReformDaemon: proposed code change with auto-deploy flag |
| `reform_rollback` | `reason`, `reverted_to` | Binary rollback event with reason and previous commit SHA |

---

## 23. Rate Limits & Quotas

Rate limits and per-tenant quotas are configured at key issuance time and are not publicly fixed. Contact [thynaptic.com](https://thynaptic.com) for your tier details.

When a rate limit is exceeded the API returns `429 Too Many Requests`. Implement exponential backoff with jitter:

```python
import time, random

def chat_with_retry(client, **kwargs):
    for attempt in range(5):
        try:
            return client.chat.completions.create(**kwargs)
        except openai.RateLimitError:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
    raise RuntimeError("Rate limit retries exhausted")
```

---

## 24. Error Reference

| HTTP Status | Type | Common Cause |
|-------------|------|--------------|
| `400 Bad Request` | `invalid_request_error` | Malformed JSON, missing required field |
| `401 Unauthorized` | `authentication_error` | Missing, expired, or malformed Bearer token |
| `403 Forbidden` | `permission_error` | Token valid but lacks required role (e.g. admin endpoint) |
| `404 Not Found` | `not_found_error` | Resource ID does not exist |
| `429 Too Many Requests` | `rate_limit_error` | Request rate or quota exceeded |
| `500 Internal Server Error` | `server_error` | Unhandled server fault; retry and report if persistent |

**Standard error body:**
```json
{
  "error": {
    "message": "resource not found: goal_xyz789",
    "type": "not_found_error",
    "code": 404
  }
}
```

---

## 25. Support

- **Website:** [thynaptic.com](https://thynaptic.com)
- **API status & health:** `GET https://oricli.thynaptic.com/v1/health`
- **Key requests and billing:** Contact via thynaptic.com

---

*ORI Studio is developed by Thynaptic Research. Documentation current as of v11.0.0.*
