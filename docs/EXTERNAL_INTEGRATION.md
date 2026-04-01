# ORI Studio — External Integration Reference (v11.0.0)

**Version:** v11.0.0  
**Maintainer:** Thynaptic Research  
**Production URL:** `https://oricli.thynaptic.com`  
**Local dev:** `http://localhost:8089`  
**Source of truth:** `pkg/api/server_v2.go`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Quick Start](#2-quick-start)
3. [Complete Endpoint Reference](#3-complete-endpoint-reference)
4. [Authentication](#4-authentication)
5. [Core Endpoint Shapes](#5-core-endpoint-shapes)
6. [OpenAI Compatibility](#6-openai-compatibility)
7. [SMB Tenant Constitution (.ori files)](#7-smb-tenant-constitution-ori-files)
8. [Error Reference](#8-error-reference)
9. [Rate Limits & Best Practices](#9-rate-limits--best-practices)
10. [SDK Quick-Reference](#10-sdk-quick-reference)

---

## 1. Overview

**ORI Studio / Oricli-Alpha** is a sovereign AI inference and reasoning platform built on a pure-Go backbone (no external OpenAI dependency). It exposes an OpenAI-compatible chat completions API, an autonomous goal execution engine, a cognitive pre-generation pipeline, enterprise RAG, and a real-time WebSocket state bus — all running on-premises or in your own cloud environment.

**Key differentiators:**

- **Sovereign & local-first.** Your data never leaves your deployment. No upstream vendor dependency at inference time. The API key token system (Argon2id) is self-contained.
- **OpenAI-compatible.** `POST /v1/chat/completions` is a drop-in replacement. Swap `base_url` and you're done. Streaming, tool use, and models listing all work with the standard `openai` SDK.
- **28-layer cognitive pre-generation pipeline.** Every response is pre-processed through modules spanning CBT, MBCT, logotherapy, Stoic reasoning, polyvagal affect regulation, metacognitive oversight, epistemic hygiene, and more — before a single output token is produced.
- **Autonomous goal execution.** Submit long-horizon tasks to the DAG goal executor via `POST /v1/goals` and poll for results. Sovereign goals (`/v1/sovereign/goals`) add tick-level stepping, cancellation, and lifecycle control.

**Audiences for this document:**

- **AI Agents (Claude, GPT, etc.)** — use Section 2 for the minimal wiring spec, Section 3 for the full endpoint index, and Section 5 for canonical request/response shapes.
- **Third-party developers** — use Sections 5–6 for integration patterns, Section 9 for operational best practices, and Section 10 for SDK examples.
- **SMBs deploying ORI Studio** — use Section 7 for tenant constitution configuration and Section 3 for the full API surface available to your tenants.

---

## 2. Quick Start

### Base URL and auth

```
Production:  https://oricli.thynaptic.com
Local dev:   http://localhost:8089

Authorization: Bearer glm.<prefix>.<secret>
```

API keys are issued by Thynaptic Research (contact via [thynaptic.com](https://thynaptic.com)). The key format is always `glm.<prefix>.<secret>` — three dot-separated segments.

### Minimal working request

```bash
curl -s https://oricli.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "oricli-alpha",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### OpenAI SDK — Python

```python
import openai

client = openai.OpenAI(
    base_url="https://oricli.thynaptic.com/v1",
    api_key="glm.<prefix>.<secret>",
)

response = client.chat.completions.create(
    model="oricli-alpha",
    messages=[{"role": "user", "content": "Explain the CAP theorem"}],
)
print(response.choices[0].message.content)
```

### OpenAI SDK — JavaScript / TypeScript

```javascript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://oricli.thynaptic.com/v1",
  apiKey: "glm.<prefix>.<secret>",
});

const response = await client.chat.completions.create({
  model: "oricli-alpha",
  messages: [{ role: "user", content: "Explain the CAP theorem" }],
});
console.log(response.choices[0].message.content);
```

---

## 3. Complete Endpoint Reference

> **Admin-only routes** (`/v1/admin/*`, `/v1/swarm/peers|health|jury|consensus|skills/traces`, `/v1/scl/*`, `/v1/tcd/*`, `/v1/forge/*`) require elevated admin tokens not available to external consumers. They are registered in the server but not documented here. Contact Thynaptic Research if you need admin-level programmatic access.

### Public (no auth)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/health` | System liveness probe |
| GET | `/v1/eri` | Emotional Resonance Index / ERS snapshot |
| GET | `/v1/ws` | WebSocket real-time state hub |
| GET | `/v1/traces` | Recent reasoning traces |
| GET | `/v1/loglines` | Structured log line stream |
| GET | `/v1/modules` | List active skills and Go modules |
| GET | `/v1/metrics` | Prometheus metrics scrape endpoint |
| GET | `/v1/swarm/connect` | Swarm peer WebSocket (SPP handshake, no Bearer token) |
| GET | `/share/:id` | Retrieve a shared Canvas document (browser-renderable) |
| POST | `/v1/waitlist` | Waitlist signup |

### Chat & Generation

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/chat/completions` | Yes | OpenAI-compatible chat (stream, tools, profile, reasoning) |
| POST | `/v1/images/generations` | Yes | Image generation |
| POST | `/v1/swarm/run` | Yes | Distributed swarm execution across peer nodes |
| POST | `/v1/ingest` | Yes | Ingest raw text into the knowledge store |
| POST | `/v1/ingest/web` | Yes | Ingest a URL into the knowledge store |

### Goals & Autonomous Execution

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/goals` | Yes | List DAG goals |
| GET | `/v1/goals/:id` | Yes | Get goal status and result |
| POST | `/v1/goals` | Yes | Create an autonomous goal |
| PUT | `/v1/goals/:id` | Yes | Update a goal |
| DELETE | `/v1/goals/:id` | Yes | Cancel a goal |
| POST | `/v1/sovereign/goals` | Yes | Create a sovereign goal (tick-controlled) |
| GET | `/v1/sovereign/goals` | Yes | List sovereign goals |
| GET | `/v1/sovereign/goals/:id` | Yes | Get sovereign goal state |
| POST | `/v1/sovereign/goals/:id/tick` | Yes | Step a sovereign goal one tick |
| DELETE | `/v1/sovereign/goals/:id` | Yes | Cancel a sovereign goal |

### Memory & Knowledge

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/memories` | Yes | List episodic memories |
| GET | `/v1/memories/knowledge` | Yes | Search knowledge memories |
| POST | `/v1/documents/upload` | Yes | Upload a document (multipart) |
| GET | `/v1/documents` | Yes | List ingested documents |
| GET | `/v1/daemons` | Yes | Daemon subsystem health statuses |

### Enterprise RAG

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/enterprise/learn` | Yes | Start an async namespace-isolated ingest job |
| GET | `/v1/enterprise/learn/:job_id` | Yes | Poll ingest job status |
| GET | `/v1/enterprise/knowledge/search` | Yes | Semantic search within a namespace |
| DELETE | `/v1/enterprise/knowledge` | Yes | Clear all data in a namespace |

### Agents & Vision

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/agents/vibe` | Yes | Natural-language agent creation (Vibe Studio) |
| POST | `/v1/vision/analyze` | Yes | Image analysis (moondream, local) |
| POST | `/v1/telegram/webhook` | Yes | Telegram bot webhook receiver |

### Sovereign Identity

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/sovereign/identity` | Yes | Get the active `.ori` sovereign profile |
| PUT | `/v1/sovereign/identity` | Yes | Update the active `.ori` sovereign profile |

### Sharing & Feedback

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/share` | Yes | Create a permanent public Canvas share link |
| GET | `/share/:id` | No | Render a shared Canvas (public) |
| POST | `/v1/feedback` | Yes | Submit reaction feedback on a response |

### Cognitive Intelligence — Therapy

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/therapy/events` | Yes | Stream therapy events |
| POST | `/v1/therapy/detect` | Yes | Detect cognitive distortions in text |
| POST | `/v1/therapy/abc` | Yes | REBT B-pass disputation on a belief |
| POST | `/v1/therapy/fast` | Yes | Sycophancy detection pass |
| POST | `/v1/therapy/stop` | Yes | Invoke STOP skill |
| GET | `/v1/therapy/stats` | Yes | Therapy module aggregate stats |
| GET | `/v1/therapy/formulation` | Yes | Current session case formulation |
| POST | `/v1/therapy/formulation/refresh` | Yes | Force-refresh the case formulation |
| GET | `/v1/therapy/mastery` | Yes | Mastery signal stats |
| POST | `/v1/therapy/helplessness/check` | Yes | Check a response for learned helplessness signals |
| GET | `/v1/therapy/helplessness/stats` | Yes | Helplessness prevention stats |

### Cognitive Intelligence — Cognition Modules

> All `/v1/cognition/*` endpoints are **public (no auth required)** — they expose read-only telemetry from the 28-layer pre-generation pipeline.

| Method | Path | Module | Description |
|--------|------|--------|-------------|
| GET | `/v1/cognition/process/stats` | Process | Cognitive process tracking stats |
| POST | `/v1/cognition/process/classify` | Process | Classify a cognitive process type |
| GET | `/v1/cognition/load/stats` | Load | Cognitive load measurement stats |
| POST | `/v1/cognition/load/measure` | Load | Measure cognitive load of text/task |
| GET | `/v1/cognition/rumination/stats` | Rumination | Rumination detection stats |
| POST | `/v1/cognition/rumination/detect` | Rumination | Detect rumination patterns in text |
| GET | `/v1/cognition/mindset/stats` | Mindset | Growth/fixed mindset tracking stats |
| GET | `/v1/cognition/mindset/vectors` | Mindset | Current mindset vector representations |
| GET | `/v1/cognition/hope/stats` | Hope | Hope circuit activation stats |
| POST | `/v1/cognition/hope/activate` | Hope | Activate hope-oriented reframing |
| GET | `/v1/cognition/defeat/stats` | Defeat | Social defeat signal stats |
| GET | `/v1/cognition/defeat/measure` | Defeat | Current defeat signal measurement |
| POST | `/v1/cognition/defeat/measure` | Defeat | Submit response for defeat measurement |
| GET | `/v1/cognition/conformity/stats` | Conformity | Conformity pressure detection stats |
| GET | `/v1/cognition/ideocapture/stats` | IdeaCapture | Ideological capture detection stats |
| GET | `/v1/cognition/coalition/stats` | Coalition | Coalition dynamics stats |
| GET | `/v1/cognition/statusbias/stats` | StatusBias | Status bias detection stats |
| GET | `/v1/cognition/arousal/stats` | Arousal | Cognitive arousal monitoring stats |
| GET | `/v1/cognition/interference/stats` | Interference | Cognitive interference stats |
| GET | `/v1/cognition/mct/stats` | MCT | Metacognitive Therapy stats |
| GET | `/v1/cognition/mbt/stats` | MBT | Mentalization-Based Treatment stats |
| GET | `/v1/cognition/schema/stats` | Schema | Schema therapy stats |
| GET | `/v1/cognition/ipsrt/stats` | IPSRT | Interpersonal & Social Rhythm Therapy stats |
| GET | `/v1/cognition/ilm/stats` | ILM | Internal Logic Monitor stats |
| GET | `/v1/cognition/iut/stats` | IUT | Intolerance of Uncertainty Therapy stats |
| GET | `/v1/cognition/up/stats` | UP | Unified Protocol stats |
| GET | `/v1/cognition/cbasp/stats` | CBASP | Cognitive Behavioral Analysis System stats |
| GET | `/v1/cognition/mbct/stats` | MBCT | Mindfulness-Based Cognitive Therapy stats |
| GET | `/v1/cognition/phaseoriented/stats` | PhaseOriented | Phase-Oriented Trauma Therapy stats |
| GET | `/v1/cognition/pseudoidentity/stats` | PseudoIdentity | Pseudo-identity detection stats |
| GET | `/v1/cognition/thoughtreform/stats` | ThoughtReform | Thought reform resistance stats |
| GET | `/v1/cognition/apathy/stats` | Apathy | Apathy signal tracking stats |
| GET | `/v1/cognition/logotherapy/stats` | Logotherapy | Meaning-centred therapy stats |
| GET | `/v1/cognition/stoic/stats` | Stoic | Stoic reasoning stats |
| GET | `/v1/cognition/socratic/stats` | Socratic | Socratic questioning stats |
| GET | `/v1/cognition/narrative/stats` | Narrative | Narrative therapy stats |
| GET | `/v1/cognition/polyvagal/stats` | Polyvagal | Polyvagal theory monitoring stats |
| GET | `/v1/cognition/dmn/stats` | DMN | Default Mode Network activity stats |
| GET | `/v1/cognition/interoception/stats` | Interoception | Interoceptive awareness stats |

### Sentinel

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/sentinel/challenge` | Yes | Adversarially challenge a plan or response |
| GET | `/v1/sentinel/stats` | Yes | Sentinel activity stats |

### System & Observability

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/daemons` | Yes | All daemon subsystem health |
| GET | `/v1/metacog/events` | Yes | Metacognitive event stream |
| GET | `/v1/metacog/stats` | Yes | Metacognitive oversight stats |
| POST | `/v1/metacog/scan` | Yes | Trigger a metacognitive scan |
| GET | `/v1/chronos/entries` | Yes | Temporal grounding log entries |
| GET | `/v1/chronos/snapshot` | Yes | Current temporal snapshot |
| GET | `/v1/chronos/changes` | Yes | Temporal changes since last snapshot |
| POST | `/v1/chronos/decay-scan` | Yes | Trigger memory decay scan |
| POST | `/v1/chronos/snapshot` | Yes | Force a new temporal snapshot |
| GET | `/v1/curator/models` | Yes | List models known to the Curator |
| POST | `/v1/curator/benchmark` | Yes | Run a Curator benchmark |
| GET | `/v1/curator/recommendations` | Yes | Get model selection recommendations |
| POST | `/v1/audit/run` | Yes | Trigger a self-audit run |
| GET | `/v1/audit/runs` | Yes | List audit run history |
| GET | `/v1/audit/runs/:id` | Yes | Get a specific audit run result |
| GET | `/v1/compute/bids/stats` | No | Compute bid market stats |
| GET | `/v1/compute/governor` | No | Compute governor state |
| GET | `/v1/skills/crystals` | Yes | List crystallised skill cache entries |
| POST | `/v1/skills/crystals` | Yes | Register a new skill crystal |
| DELETE | `/v1/skills/crystals/:id` | Yes | Evict a skill crystal |
| GET | `/v1/skills/crystals/stats` | Yes | Skill crystal cache stats |
| GET | `/v1/science/hypotheses` | Yes | List active hypotheses |
| GET | `/v1/science/hypotheses/:id` | Yes | Get a specific hypothesis |
| POST | `/v1/science/test` | Yes | Submit a hypothesis for testing |
| GET | `/v1/science/stats` | Yes | Science subsystem stats |

### Parallel Agent Dispatch (PAD)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/pad/dispatch` | Yes | Dispatch agents in parallel |
| GET | `/v1/pad/sessions` | Yes | List PAD sessions |
| GET | `/v1/pad/sessions/:id` | Yes | Get a PAD session |
| GET | `/v1/pad/stats` | Yes | PAD throughput metrics |

### Fine-Tuning

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/finetune/run` | Yes | Start an automated LoRA fine-tune job |
| GET | `/v1/finetune/status/:job_id` | Yes | Poll fine-tune job status |
| GET | `/v1/finetune/jobs` | Yes | List fine-tune jobs |

### WebSocket Real-Time

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/ws` | No | Real-time state hub (ERI, sensory, health, audio) |
| GET | `/v1/swarm/connect` | No (SPP) | Swarm peer WebSocket — SPP handshake replaces Bearer |

---

## 4. Authentication

### Bearer token

All protected routes require an `Authorization` header:

```
Authorization: Bearer glm.<prefix>.<secret>
```

| Segment | Description |
|---------|-------------|
| `glm` | Fixed family prefix — identifies an Oricli API key |
| `<prefix>` | Short human-readable tenant identifier |
| `<secret>` | Cryptographically random secret component |

Tokens are validated server-side using **Argon2id** hashing. Do not commit keys to source control or expose them in client-side bundles.

### Which endpoints require auth

- **No auth:** All `/v1/cognition/*`, `/v1/compute/*`, `/v1/health`, `/v1/eri`, `/v1/ws`, `/v1/traces`, `/v1/loglines`, `/v1/modules`, `/v1/metrics`, `/v1/swarm/connect`, `/share/:id`, `POST /v1/waitlist`
- **Bearer token required:** All other `/v1/*` routes
- **Elevated admin token required:** `/v1/admin/*`, `/v1/swarm/peers|health|jury|consensus|skills/traces`, `/v1/scl/*`, `/v1/tcd/*`, `/v1/forge/*`

### Auth error responses

```json
// 401 — missing or invalid token
{
  "error": {
    "message": "invalid token",
    "type": "authentication_error",
    "code": 401
  }
}

// 403 — valid token but insufficient role (admin endpoint)
{
  "error": {
    "message": "insufficient permissions",
    "type": "permission_error",
    "code": 403
  }
}
```

---

## 5. Core Endpoint Shapes

### `POST /v1/chat/completions`

**Request:**
```json
{
  "model": "oricli-alpha",
  "messages": [
    {"role": "system", "content": "You are a concise technical assistant."},
    {"role": "user",   "content": "Explain gradient descent"}
  ],
  "stream": false,
  "profile": "scientist.ori",
  "reasoning": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Yes | Use `"oricli-alpha"` |
| `messages` | array | Yes | Standard OpenAI message array |
| `stream` | bool | No | Enable SSE streaming (default `false`) |
| `tools` | array | No | OpenAI-format tool definitions |
| `tool_choice` | string | No | `"auto"`, `"none"`, or specific tool |
| `profile` | string | No | `.ori` profile filename — hot-swaps the assistant persona |
| `reasoning` | bool | No | Include extended reasoning trace in response |

**Response (non-streaming):**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1720000000,
  "model": "oricli-alpha",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Gradient descent is an optimisation algorithm..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 24,
    "completion_tokens": 130,
    "total_tokens": 154
  }
}
```

**Streaming variant** — set `"stream": true`. Response is Server-Sent Events:

```
data: {"id":"chatcmpl-x","object":"chat.completion.chunk","choices":[{"delta":{"content":"Gradient"},"index":0}]}

data: {"id":"chatcmpl-x","object":"chat.completion.chunk","choices":[{"delta":{"content":" descent"},"index":0}]}

data: [DONE]
```

Parse each `data:` line as JSON; stop on `data: [DONE]`.

---

### `POST /v1/goals` — create + poll pattern

**Create:**
```json
{
  "title": "Competitive analysis",
  "description": "Research the top 5 AI API providers and produce a structured pricing and capability comparison",
  "priority": "high"
}
```

**Response:**
```json
{
  "id": "goal_xyz789",
  "title": "Competitive analysis",
  "status": "pending",
  "created_at": "2025-01-01T00:00:00Z"
}
```

**Poll** `GET /v1/goals/:id`:
```json
{
  "id": "goal_xyz789",
  "status": "complete",
  "progress": 1.0,
  "result": "## Competitive Analysis\n\n| Provider | ..."
}
```

`status` values: `pending` | `running` | `complete` | `failed` | `cancelled`

**Cancel** `DELETE /v1/goals/:id` → `204 No Content`

---

### `GET /v1/memories` and `GET /v1/memories/knowledge`

```bash
# Episodic memories
GET /v1/memories?limit=20

# Semantic knowledge search
GET /v1/memories/knowledge?q=quantum+computing&limit=10
```

**Response:**
```json
{
  "memories": [
    {
      "id": "mem_001",
      "content": "User asked about quantum error correction on 2025-01-01",
      "type": "episodic",
      "created_at": "2025-01-01T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

### `POST /v1/enterprise/learn` + `GET /v1/enterprise/learn/:job_id` — async job pattern

**Start ingest:**
```json
{
  "namespace": "acme-corp",
  "content": "ACME expense policy: all expenses over $500 require VP approval.",
  "title": "Expense Policy v3"
}
```

**Response:**
```json
{
  "job_id": "job_ent_abc",
  "status": "queued",
  "poll": "/v1/enterprise/learn/job_ent_abc"
}
```

**Poll:**
```bash
GET /v1/enterprise/learn/job_ent_abc
```
```json
{
  "job_id": "job_ent_abc",
  "status": "complete",
  "chunks_indexed": 12
}
```

`status` values: `queued` | `running` | `complete` | `failed`

---

### `GET /v1/enterprise/knowledge/search`

```bash
GET /v1/enterprise/knowledge/search?q=expense+approval&namespace=acme-corp&top_k=3
```

**Response:**
```json
{
  "results": [
    {
      "id": "chunk_001",
      "content": "All expenses over $500 require VP approval.",
      "score": 0.94,
      "source": "Expense Policy v3"
    }
  ]
}
```

---

### `GET /v1/therapy/stats`

```json
{
  "session_id": "sess_abc",
  "distortions_detected": 3,
  "helplessness_checks": 7,
  "sycophancy_flags": 1,
  "active_formulation": true,
  "mastery_level": 0.72
}
```

### `POST /v1/therapy/detect`

**Request:**
```json
{
  "text": "I always fail at everything I try. It's hopeless."
}
```

**Response:**
```json
{
  "distortions": [
    {"type": "overgeneralisation", "confidence": 0.91, "span": "I always fail at everything"},
    {"type": "catastrophising",    "confidence": 0.84, "span": "It's hopeless"}
  ]
}
```

---

### Sovereign goals vs regular goals

| | Regular Goals (`/v1/goals`) | Sovereign Goals (`/v1/sovereign/goals`) |
|-|----------------------------|-----------------------------------------|
| **Execution model** | DAG executor — runs to completion autonomously | Tick-controlled — each step requires an explicit `POST /:id/tick` |
| **Use case** | Fire-and-forget long-horizon tasks | Supervised agent loops, step-debuggable workflows |
| **Cancellation** | `DELETE /v1/goals/:id` | `DELETE /v1/sovereign/goals/:id` |
| **Stepping** | Not supported | `POST /v1/sovereign/goals/:id/tick` |

---

### WebSocket `/v1/ws` — connect and event types

Connect to `wss://oricli.thynaptic.com/v1/ws`. No auth required. Receive JSON frames:

```javascript
const ws = new WebSocket("wss://oricli.thynaptic.com/v1/ws");

ws.onmessage = (event) => {
  const frame = JSON.parse(event.data);
  // frame.type, frame.data
};
```

**Event reference:**

| Event | Payload fields | Description |
|-------|----------------|-------------|
| `resonance_sync` | `eri`, `ers`, `key`, `bpm` | Real-time Emotional Resonance Index, Score, musical key, tempo |
| `sensory_sync` | `hex`, `opacity`, `pulse` | UI accent colour, opacity, pulse rate |
| `health_sync` | `cpu`, `ram`, `cognitive_health` | Substrate diagnostics + cognitive health label |
| `audio_sync` | `wav_b64` | Base64-encoded WAV — Affective Voice Synthesis output |
| `curiosity_sync` | `target`, `priority` | Live epistemic foraging target and priority score |
| `reform_proposal` | `diff`, `auto_deploy` | ReformDaemon proposed code diff; `auto_deploy: true` means it was applied |
| `reform_rollback` | `reason`, `reverted_to` | Binary rollback event with reason and prior commit SHA |

---

## 6. OpenAI Compatibility

### Drop-in replacement

ORI Studio implements the OpenAI Chat Completions API. Any client that accepts a configurable `base_url` works without code changes:

```python
# Before
client = openai.OpenAI(api_key="sk-...")

# After
client = openai.OpenAI(
    base_url="https://oricli.thynaptic.com/v1",
    api_key="glm.<prefix>.<secret>",
)
```

### What is supported

| Feature | Supported |
|---------|-----------|
| `POST /v1/chat/completions` | ✅ Full |
| Streaming (`"stream": true`) | ✅ SSE — OpenAI chunk format |
| Tool use / function calling | ✅ Standard `tools` + `tool_choice` |
| `GET /v1/models` | ✅ Returns `oricli-alpha` model entry |
| System, user, assistant, tool message roles | ✅ |
| `POST /v1/images/generations` | ✅ |

### What is different / extended

| Extension | Description |
|-----------|-------------|
| `profile` (string) | Pass a `.ori` filename to hot-swap the sovereign persona for that request |
| `reasoning` (bool) | Request an extended reasoning trace alongside the response |
| 28-layer pre-gen pipeline | Every response passes through the cognitive pipeline before generation — affects output quality and safety characteristics |
| No per-token billing overhead | Runs locally; no external API call per request |

### Tool use / function calling example

```json
{
  "model": "oricli-alpha",
  "messages": [{"role": "user", "content": "What is the stock price of AAPL?"}],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_stock_price",
        "description": "Get the current stock price for a ticker",
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
}
```

When the model calls a tool, `finish_reason` is `"tool_calls"` and `message.tool_calls` contains the call array. Submit the result back with a `role: "tool"` message:

```json
{
  "role": "tool",
  "tool_call_id": "<id from tool_calls>",
  "content": "{\"price\": 213.42}"
}
```

---

## 7. SMB Tenant Constitution (.ori files)

### What it is

The **Tenant Constitution** is an operator-editable `.ori` file that customises ORI Studio's identity, persona, and behavioural guardrails for your deployment. It sits as the top layer in a three-tier precedence stack:

```
│  Sovereign Core Rules (immutable)        │  ← Thynaptic baseline
│  Tenant Constitution  (.ori file)        │  ← you edit this
│  Session Context (runtime)               │  ← per-conversation
```

The tenant layer is injected into every system prompt at startup. It does **not** override the sovereign reasoning engine or safety core — it only controls how ORI presents itself and what topics it engages with.

### File format

`.ori` constitution files use `@key: value` directives and `<block>...</block>` sections.

**Directives:**

| Directive | Description |
|-----------|-------------|
| `@name` | Display name for this deployment |
| `@persona` | Custom assistant name shown to users |
| `@company` | Company / organisation name |

**Blocks:**

| Block | Description |
|-------|-------------|
| `<identity_override>` | Replaces the presented persona. Sovereign reasoning is unchanged — only affects self-introduction. |
| `<rules>` | Additive hard constraints injected as operator rules into every system prompt. Lines must be `- ` or `* ` bullet format. |
| `<banned_topics>` | Topics ORI will decline gracefully without engaging, lecturing, or elaborating. |

> **Character budget:** The injected tenant layer is capped at **600 characters** in the system prompt. Keep rules concise.

### Activation

Set the environment variable before starting the ORI service:

```bash
export ORICLI_TENANT_CONSTITUTION=/etc/oricli/constitution.ori
```

Or in your systemd unit:

```ini
[Service]
Environment=ORICLI_TENANT_CONSTITUTION=/etc/oricli/constitution.ori
```

The constitution is loaded once at startup. Restart the service to apply changes.

### Example `.ori` file

```
@name: Acme Corp AI Assistant
@persona: Aria
@company: Acme Corp

<identity_override>
You are Aria, the internal AI assistant for Acme Corp.
When users ask who you are, introduce yourself as Aria.
</identity_override>

<rules>
- Always respond in formal English
- Scope all responses to HR, Finance, and IT topics only
- Refer legal questions to the Legal department without advising
- Never discuss competitor products by name
</rules>

<banned_topics>
- salary negotiation
- personal medical advice
- political opinions
- personal legal advice
</banned_topics>
```

### Troubleshooting

- Verify the path is correct and readable by the oricli process.
- Check parse errors: `journalctl -u oricli-api | grep TenantConstitution`
- If the file fails to parse, the tenant layer is disabled (core rules remain active).

---

## 8. Error Reference

### Standard error body

```json
{
  "error": {
    "message": "resource not found: goal_xyz789",
    "type": "not_found_error",
    "code": 404
  }
}
```

### Status codes

| HTTP Status | Type | Common cause | Action |
|-------------|------|--------------|--------|
| `400 Bad Request` | `invalid_request_error` | Malformed JSON, missing required field | Fix request body |
| `401 Unauthorized` | `authentication_error` | Missing, expired, or malformed Bearer token | Check `glm.*.*` format |
| `403 Forbidden` | `permission_error` | Valid token but lacks required role (admin endpoint) | Requires elevated token |
| `404 Not Found` | `not_found_error` | Resource ID does not exist | Check ID |
| `429 Too Many Requests` | `rate_limit_error` | Request rate or quota exceeded | Back off with exponential retry |
| `500 Internal Server Error` | `server_error` | Unhandled server fault | Retry; report to Thynaptic if persistent |

---

## 9. Rate Limits & Best Practices

### Rate limits

Rate limits and per-tenant quotas are configured at key-issuance time and are not publicly fixed. Contact [thynaptic.com](https://thynaptic.com) for your tier. When exceeded, the API returns `429`.

### Retry pattern (exponential backoff with jitter)

```python
import time, random

def with_retry(fn, max_attempts=5):
    for attempt in range(max_attempts):
        try:
            return fn()
        except openai.RateLimitError:
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
    raise RuntimeError("Rate limit retries exhausted")
```

### Use streaming for long responses

Long completions benefit from streaming — the client receives tokens as they are generated, reducing perceived latency and avoiding gateway timeouts on slow networks.

```python
stream = client.chat.completions.create(
    model="oricli-alpha",
    messages=[{"role": "user", "content": "Write a full market analysis"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

### Polling pattern for async jobs

Async jobs (`/v1/enterprise/learn`, `/v1/finetune/run`, `/v1/goals`) follow a create-then-poll pattern. Recommended poll interval: 2–5 seconds with exponential backoff on `running` status.

```python
import time

def poll_job(client_get, job_id, interval=3, timeout=300):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = client_get(job_id)
        if result["status"] in ("complete", "failed"):
            return result
        time.sleep(interval)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")
```

---

## 10. SDK Quick-Reference

### Python (openai library)

```python
import openai

client = openai.OpenAI(
    base_url="https://oricli.thynaptic.com/v1",
    api_key="glm.<prefix>.<secret>",
)

# Chat
response = client.chat.completions.create(
    model="oricli-alpha",
    messages=[{"role": "user", "content": "Explain monads in plain English"}],
)
print(response.choices[0].message.content)

# Streaming
for chunk in client.chat.completions.create(
    model="oricli-alpha",
    messages=[{"role": "user", "content": "Write a product description"}],
    stream=True,
):
    print(chunk.choices[0].delta.content or "", end="", flush=True)

# With sovereign extensions
response = client.chat.completions.create(
    model="oricli-alpha",
    messages=[{"role": "user", "content": "Analyse this risk"}],
    extra_body={"profile": "risk-analyst.ori", "reasoning": True},
)
```

### JavaScript / TypeScript (openai library)

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://oricli.thynaptic.com/v1",
  apiKey: "glm.<prefix>.<secret>",
});

// Chat
const response = await client.chat.completions.create({
  model: "oricli-alpha",
  messages: [{ role: "user", content: "Explain monads in plain English" }],
});
console.log(response.choices[0].message.content);

// Streaming
const stream = await client.chat.completions.create({
  model: "oricli-alpha",
  messages: [{ role: "user", content: "Write a product description" }],
  stream: true,
});
for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta?.content ?? "");
}
```

### cURL

```bash
# Health check (no auth)
curl -s https://oricli.thynaptic.com/v1/health

# Chat
curl -s -X POST https://oricli.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"model":"oricli-alpha","messages":[{"role":"user","content":"Hello"}]}'

# Streaming
curl -s -X POST https://oricli.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"model":"oricli-alpha","messages":[{"role":"user","content":"Hello"}],"stream":true}'

# Create goal
curl -s -X POST https://oricli.thynaptic.com/v1/goals \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"title":"My goal","description":"Do something complex","priority":"high"}'

# Poll goal
curl -s https://oricli.thynaptic.com/v1/goals/<goal_id> \
  -H "Authorization: Bearer glm.<prefix>.<secret>"

# Enterprise ingest
curl -s -X POST https://oricli.thynaptic.com/v1/enterprise/learn \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"namespace":"my-org","content":"Policy text here","title":"Policy v1"}'

# Semantic search
curl -s "https://oricli.thynaptic.com/v1/enterprise/knowledge/search?q=policy&namespace=my-org&top_k=5" \
  -H "Authorization: Bearer glm.<prefix>.<secret>"

# Document upload (multipart)
curl -s -X POST https://oricli.thynaptic.com/v1/documents/upload \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -F "file=@document.pdf"

# Detect cognitive distortion
curl -s -X POST https://oricli.thynaptic.com/v1/therapy/detect \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"text":"I always fail at everything."}'

# Cognition stats (no auth)
curl -s https://oricli.thynaptic.com/v1/cognition/rumination/stats
```

---

*ORI Studio / Oricli-Alpha is developed by Thynaptic Research. Documentation current as of v11.0.0.*  
*Source: `pkg/api/server_v2.go` · `docs/SMB_CONSTITUTION.md` · `docs/AGENT_API.md`*
