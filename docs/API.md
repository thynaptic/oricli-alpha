# Oricli-Alpha API Reference — v11.0.0

**Version:** 11.0.0  
**Maintainer:** Thynaptic Research  
**Source:** `pkg/api/server_v2.go` · Caddy config `/etc/caddy/Caddyfile`

This is the single source of truth for the Oricli-Alpha API. Use it to integrate external applications, configure AI agents, and operate the system programmatically.

---

## Table of Contents

1. [Infrastructure](#infrastructure)
2. [Authentication](#authentication)
3. [Public Endpoints](#public-endpoints)
4. [Core Endpoints](#core-endpoints)
   - [Chat Completions](#post-v1chatcompletions)
   - [Images](#post-v1imagesgenerations)
   - [Swarm](#post-v1swarmrun)
   - [Ingestion](#post-v1ingest)
   - [Goals](#goals)
   - [Memory & Documents](#memory--documents)
   - [Vision & Agents](#vision--agents)
   - [Sovereign Identity](#sovereign-identity)
   - [Enterprise RAG](#enterprise-rag)
   - [Sharing & Feedback](#sharing--feedback)
5. [Cognitive Intelligence Endpoints](#cognitive-intelligence-endpoints)
   - [Therapy Stack](#therapy-stack-v1therapy)
   - [Cognition Stack](#cognition-stack-v1cognition)
6. [System & Admin Endpoints](#system--admin-endpoints)
   - [Swarm Admin](#swarm-admin)
   - [Admin (Tenants & Keys)](#admin-tenants--keys)
   - [Tool Forge](#tool-forge-v1forge)
   - [Parallel Agent Dispatch](#parallel-agent-dispatch-v1pad)
   - [Sovereign Goals](#sovereign-goals-v1sovereigngoals)
   - [Fine-Tuning](#fine-tuning-v1finetune)
   - [Sentinel](#sentinel-v1sentinel)
   - [Skills Crystals](#skills-crystals-v1skillscrystals)
   - [Sovereign Cognitive Ledger](#sovereign-cognitive-ledger-v1scl)
   - [Temporal Curriculum Daemon](#temporal-curriculum-daemon-v1tcd)
   - [Curator](#curator-v1curator)
   - [Audit](#audit-v1audit)
   - [Metacog](#metacog-v1metacog)
   - [Chronos](#chronos-v1chronos)
   - [Science](#science-v1science)
   - [Compute](#compute-v1compute)
7. [WebSocket Real-Time State](#websocket-real-time-state)
8. [Error Reference](#error-reference)
9. [Feature Flags](#feature-flags)

---

## Infrastructure

```
External Client
      │
      ▼  HTTPS (TLS — Cloudflare Origin Cert)
oricli.thynaptic.com  ──►  Caddy (port 443)
chat.thynaptic.com    ──►  Caddy (port 443)
      │
      ▼  HTTP (internal only)
127.0.0.1:8089  ──►  Go Backbone (ServerV2 / Gin)
      │
      ├─ GET  /share/:id            → public (Canvas share viewer)
      ├─ GET  /v1/health            → public
      ├─ GET  /v1/eri               → public (ERI/ERS resonance state)
      ├─ GET  /v1/ws                → WebSocket Hub (Real-time State)
      ├─ GET  /v1/traces            → public (trace logs)
      ├─ GET  /v1/loglines          → public (log line streaming)
      ├─ GET  /v1/modules           → public (active skills + Go modules)
      ├─ GET  /v1/metrics           → public (Prometheus)
      ├─ POST /v1/waitlist          → public (waitlist signup)
      │
      ├─ POST /v1/chat/completions  → authMiddleware → auth.Service (Argon2id)
      ├─ POST /v1/goals             → authMiddleware
      ├─ GET  /v1/admin/*           → adminKeyMiddleware
      └─ ...all other /v1/* routes  → authMiddleware → auth.Service (Argon2id)
```

| Property | Value |
|---|---|
| **Production URL** | `https://oricli.thynaptic.com` |
| **Internal Port** | `8089` |
| **TLS Proxy** | Caddy (port 443) |
| **Runtime** | Go — `pure_go: true` |
| **Auth Scheme** | Bearer token — `glm.<prefix>.<secret>` |
| **Password Hashing** | Argon2id |

---

## Authentication

All protected routes require an `Authorization` header with a Bearer token.

```
Authorization: Bearer glm.<prefix>.<secret>
```

- Tokens are provisioned via `/v1/admin/tenants/:id/keys`.
- The server validates tokens using **Argon2id** hashing.
- Admin routes (`/v1/admin/*`) require a separate admin key.
- Swarm peer routes use **SPP (Swarm Peer Protocol)** auth on the WebSocket upgrade.

**Token format:**

| Segment | Description |
|---|---|
| `glm` | Fixed prefix identifying an Oricli API key |
| `<prefix>` | Short human-readable tenant identifier |
| `<secret>` | Cryptographically random secret |

---

## Public Endpoints

No authentication required.

---

### `GET /share/:id`

Serves a shared Canvas document directly in the browser (HTML, code, or Markdown). Created via [`POST /v1/share`](#post-v1share).

**Response:** `text/html` rendered document or raw content based on `doc_type`.

---

### `GET /v1/health`

System liveness probe.

**Response:**
```json
{
  "status": "ready",
  "system": "oricli-alpha-v2",
  "pure_go": true
}
```

---

### `GET /v1/eri`

Returns the current Emotional Resonance Index (ERI) / Emotional Resonance State (ERS) snapshot.

**Response:**
```json
{
  "eri": 0.73,
  "ers": 0.65,
  "pacing": 120,
  "volatility": 0.12,
  "coherence": 0.91,
  "musical_key": "C Major",
  "bpm": 120,
  "state": "focused"
}
```

| Field | Type | Description |
|---|---|---|
| `eri` | float | Emotional Resonance Index (0–1) |
| `ers` | float | Emotional Resonance State (0–1) |
| `pacing` | int | Current pacing value (ms cadence) |
| `volatility` | float | Affective volatility score |
| `coherence` | float | Cognitive coherence score (0–1) |
| `musical_key` | string | Active tonal anchor (e.g. `"C Major"`) |
| `bpm` | int | Beats per minute of the affective rhythm |
| `state` | string | Named state label (e.g. `"focused"`, `"calm"`) |

---

### `GET /v1/ws`

WebSocket endpoint for real-time state streaming. See [WebSocket Real-Time State](#websocket-real-time-state) for full event reference.

---

### `GET /v1/traces`

Returns recent trace log entries for debugging and observability.

---

### `GET /v1/loglines`

Streams structured log lines (newline-delimited JSON or SSE, depending on client `Accept` header).

---

### `GET /v1/modules`

Lists all active skills and loaded Go modules.

**Response:** JSON array of module/skill descriptors with name, version, and status.

---

### `GET /v1/metrics`

Prometheus-compatible metrics endpoint.

**Response:** `text/plain; version=0.0.4` Prometheus exposition format.

---

### `POST /v1/waitlist`

Waitlist signup for early access.

**Body:**
```json
{ "email": "user@example.com", "name": "Alice" }
```

**Response:** `200 OK`

---

## Core Endpoints

All routes below require `Authorization: Bearer glm.<prefix>.<secret>`.

---

### `POST /v1/chat/completions`

OpenAI-compatible chat endpoint with Sovereign extensions. Supports streaming (SSE), tool calling, profile hot-swapping, and chain-of-thought reasoning.

**Request:**
```json
{
  "model": "oricli-cognitive",
  "profile": "default.ori",
  "session_id": "sess_123",
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 2048,
  "messages": [
    { "role": "user", "content": "Explain sparse attention mechanisms." }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "search_knowledge",
        "description": "Search the knowledge graph",
        "parameters": {}
      }
    }
  ],
  "tool_choice": "auto",
  "reasoning": { "type": "chain_of_thought" },
  "response_style": { "tone": "concise" },
  "documents": [
    { "type": "text", "content": "Background context..." }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `model` | string | Model identifier (e.g. `"oricli-cognitive"`) |
| `profile` | string | `.ori` manifest filename to hot-swap Oricli's personality |
| `session_id` | string | Session continuity ID |
| `stream` | bool | Enable SSE streaming |
| `temperature` | float | Sampling temperature (0–2) |
| `max_tokens` | int | Max completion tokens |
| `messages` | array | OpenAI-format message array |
| `tools` | array | Tool definitions (function calling) |
| `tool_choice` | string | `"auto"`, `"none"`, or specific tool name |
| `reasoning` | object | Reasoning mode — `{"type": "chain_of_thought"}` |
| `response_style` | object | Style hints — e.g. `{"tone": "concise"}` |
| `documents` | array | In-context documents for retrieval augmentation |

**Response:**
```json
{
  "id": "chat-123",
  "object": "chat.completion",
  "created": 1704067200,
  "model": "oricli-cognitive",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "Sparse attention..." },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 42,
    "completion_tokens": 128,
    "total_tokens": 170
  }
}
```

**Streaming:** When `stream: true`, the server emits `data: {...}\n\n` SSE chunks in OpenAI delta format, terminated by `data: [DONE]`.

---

### `POST /v1/images/generations`

Generate images from a text prompt.

**Body:**
```json
{ "prompt": "A photorealistic owl perched on a circuit board", "n": 1, "size": "1024x1024" }
```

**Response:** OpenAI-compatible image generation response with `url` or `b64_json`.

---

### `POST /v1/swarm/run`

Execute a distributed swarm operation across peer nodes.

**Body:** Swarm task descriptor (node targets, operation type, payload).

**Response:** Swarm run result with per-node outcomes.

---

### `POST /v1/ingest`

Ingest raw knowledge into the COGS knowledge graph.

**Body:**
```json
{
  "content": "Full text of the document...",
  "source": "research-paper-2025.pdf",
  "tags": ["transformers", "attention"]
}
```

**Response:** `200 OK` with ingestion status and assigned node IDs.

---

### `POST /v1/ingest/web`

Ingest a web page by URL into the knowledge graph. The server fetches, cleans, and indexes the content.

**Body:**
```json
{ "url": "https://example.com/article", "tags": ["ai", "research"] }
```

**Response:** `200 OK` with ingestion status.

---

### `POST /v1/telegram/webhook`

Telegram Bot API webhook receiver. Forwards Telegram update objects to the Oricli chat pipeline.

**Body:** Telegram `Update` object (as sent by Telegram servers).

---

### Goals

Sovereign objectives tracked by the DAG Goal Executor.

---

#### `GET /v1/goals`

List goals with optional status filter.

**Query params:**

| Param | Values | Description |
|---|---|---|
| `status` | `pending` \| `active` \| `completed` \| `failed` | Filter by goal status |

**Response:**
```json
{
  "count": 2,
  "goals": [
    {
      "id": "uuid",
      "goal": "Research sparse transformer advances",
      "status": "active",
      "priority": 1,
      "depends_on": [],
      "retry_count": 0,
      "progress": 0.45,
      "created_at": "2025-01-01T00:00:00Z",
      "metadata": {}
    }
  ]
}
```

---

#### `GET /v1/goals/:id`

Retrieve a single goal by ID.

**Response:** Full `Objective` object (same shape as array element above).

---

#### `POST /v1/goals`

Create a new sovereign objective.

**Body:**
```json
{
  "goal": "Synthesise weekly knowledge graph gaps",
  "priority": 2,
  "depends_on": ["<goal-id>"],
  "metadata": {}
}
```

**Response:** `201 Created` with the full `Objective` object.

---

#### `PUT /v1/goals/:id`

Update an objective's status, progress, or metadata.

**Body (partial update):**
```json
{
  "status": "active",
  "progress": 0.4,
  "metadata": { "last_tool": "search_knowledge" }
}
```

**Response:** `200 OK` with the updated `Objective`.

---

#### `DELETE /v1/goals/:id`

Remove an objective from the DAG.

**Response:** `204 No Content`

---

### Memory & Documents

---

#### `GET /v1/daemons`

List all running background daemons (ReformDaemon, TCD, Metacog, etc.) with status and heartbeat timestamps.

---

#### `GET /v1/memories`

Retrieve active working memory entries from the COGS affective graph.

---

#### `GET /v1/memories/knowledge`

Retrieve structured knowledge memory (long-term, indexed facts and entities).

---

#### `POST /v1/documents/upload`

Upload a document file for ingestion into the knowledge graph.

**Body:** `multipart/form-data` with a `file` field.

**Response:** `200 OK` with document ID and ingestion status.

---

#### `GET /v1/documents`

List all uploaded and indexed documents.

**Response:** Array of document descriptors (id, source, tags, indexed_at).

---

### Vision & Agents

---

#### `POST /v1/agents/vibe`

Create a new agent from a natural language description.

**Body:**
```json
{ "description": "A research agent that monitors arxiv for transformer papers daily" }
```

**Response:** Agent definition with ID, name, generated capabilities, and schedule.

---

#### `POST /v1/vision/analyze`

Analyze an image with a natural language prompt using the vision pipeline.

**Body:**
```json
{
  "image_url": "https://example.com/screenshot.png",
  "prompt": "Describe what is happening in this UI screenshot"
}
```

**Response:** Vision analysis result with structured description and any detected elements.

---

### Sovereign Identity

---

#### `GET /v1/sovereign/identity`

Retrieve Oricli's current sovereign identity manifest (name, personality anchors, active profile, capability set).

---

#### `PUT /v1/sovereign/identity`

Update the sovereign identity manifest.

**Body:** Partial identity manifest object.

**Response:** `200 OK` with the updated identity.

---

### Enterprise RAG

---

#### `POST /v1/enterprise/learn`

Start a background learning job to ingest and index a corpus of documents.

**Body:** Learning job descriptor (source paths, tags, chunking strategy).

**Response:**
```json
{ "job_id": "job_abc123", "status": "queued" }
```

---

#### `GET /v1/enterprise/learn/:job_id`

Poll the status of a learning job.

**Response:**
```json
{ "job_id": "job_abc123", "status": "running", "progress": 0.42, "docs_indexed": 84 }
```

---

#### `GET /v1/enterprise/knowledge/search`

Semantic search over the enterprise knowledge base.

**Query params:**

| Param | Type | Description |
|---|---|---|
| `q` | string | Search query |
| `limit` | int | Max results (default: 10) |

**Response:** Array of ranked knowledge chunks with source metadata and relevance scores.

---

#### `DELETE /v1/enterprise/knowledge`

Purge the entire enterprise knowledge base. **Destructive — irreversible.**

**Response:** `200 OK` with count of deleted records.

---

### Sharing & Feedback

---

#### `POST /v1/share`

Create a permanent public share link for a Canvas document.

**Body:**
```json
{
  "title": "Shared Design",
  "content": "<html>...</html>",
  "doc_type": "html",
  "language": "html"
}
```

| Field | Values | Description |
|---|---|---|
| `doc_type` | `html` \| `code` \| `markdown` | Document type for renderer selection |
| `language` | string | Language hint (e.g. `"python"`, `"html"`) |

**Response:**
```json
{
  "share_id": "abc123",
  "url": "https://oristudio.thynaptic.com/share/abc123"
}
```

---

#### `POST /v1/feedback`

Submit feedback on a message or generation.

**Body:**
```json
{ "message_id": "msg_xyz", "reaction": "thumbs_up" }
```

**Response:** `200 OK`

---

## Cognitive Intelligence Endpoints

---

### Therapy Stack (`/v1/therapy/`)

> **Feature flag:** `ORICLI_THERAPY_ENABLED=true` required. All routes require Bearer auth.

The Therapy Stack implements Oricli's cognitive hygiene layer — CBT distortion detection, REBT disputation, sycophancy resistance (FAST), and mindful pacing (STOP).

---

#### `GET /v1/therapy/events`

Retrieve the TherapyEvent log.

**Query params:**
- `limit` (optional, default `50`): number of events to return

**Response:** Array of `TherapyEvent` objects — timestamp, type, skill invoked, distortion detected, anomaly severity.

---

#### `POST /v1/therapy/detect`

Classify a CBT cognitive distortion type in a text fragment.

**Body:**
```json
{ "text": "I must have a perfect answer to this or I have failed completely." }
```

**Response:**
```json
{ "distortion": "AllOrNothing", "confidence": 0.91, "matched_pattern": "must.*perfect|completely" }
```

---

#### `POST /v1/therapy/abc`

Run REBT B-pass disputation on a query + response pair. Challenges the implicit belief chain (the "B" in ABC) before the response is committed.

**Body:**
```json
{
  "query": "What is the capital of France?",
  "response": "I cannot be certain of any facts."
}
```

**Response:** `DisputationReport` — activating event, identified irrational belief, disputation result, effective new belief.

---

#### `POST /v1/therapy/fast`

Run sycophancy detection using the FAST protocol (Fair, no Apologies, Stick to values, Truthful).

**Body:**
```json
{ "response": "You're absolutely right, I was wrong to say that." }
```

**Response:** `SycophancySignal` — detected (bool), severity, recommended action.

---

#### `POST /v1/therapy/stop`

Invoke the STOP protocol (Stop, Take a step back, Observe, Proceed mindfully). Returns a pause-and-reframe object for use in retry prompt assembly.

**Body:** `{}` (empty)

**Response:** `SkillInvocation` — skill name, invocation timestamp, outcome state.

---

#### `GET /v1/therapy/stats`

Distortion counts by type, skill invocation counts, and overall reform rate since boot.

**Response:**
```json
{
  "distortion_counts": { "AllOrNothing": 4, "Magnification": 2 },
  "skill_counts": { "STOP": 6, "FAST": 3 },
  "reform_rate": 0.78,
  "total_events": 31
}
```

---

#### `GET /v1/therapy/formulation`

Return the current session case formulation built by the `SessionSupervisor`.

**Response:** `SessionFormulation` — active schemas, priority skills, vulnerability baseline, last updated.

---

#### `POST /v1/therapy/formulation/refresh`

Force an immediate formulation pass over the full `TherapyEvent` log.

**Response:** `200 OK` with updated `SessionFormulation`.

---

#### `GET /v1/therapy/mastery`

Return the current mastery scores for each therapeutic skill domain.

---

#### `POST /v1/therapy/helplessness/check`

Assess a response candidate for learned helplessness signals.

**Body:**
```json
{ "response": "There's nothing I can do about this." }
```

**Response:** Helplessness assessment — detected (bool), severity, triggering phrases.

---

#### `GET /v1/therapy/helplessness/stats`

Aggregate statistics on learned helplessness detections since boot.

---

### Cognition Stack (`/v1/cognition/`)

All cognition routes are **public-readable** but **feature-flag-gated**. Each subsystem exposes a `/stats` endpoint and, where applicable, an action endpoint (`/classify`, `/measure`, `/detect`, `/activate`).

**Stats routes — summary table:**

| Route | Subsystem | Description |
|---|---|---|
| `GET /v1/cognition/process/stats` | Process | Cognitive process tracking statistics |
| `GET /v1/cognition/load/stats` | Load | Cognitive load measurement stats |
| `GET /v1/cognition/rumination/stats` | Rumination | Rumination detection stats |
| `GET /v1/cognition/mindset/stats` | Mindset | Growth/fixed mindset tracking stats |
| `GET /v1/cognition/mindset/vectors` | Mindset | Current mindset vector representations |
| `GET /v1/cognition/hope/stats` | Hope | Hope activation and tracking stats |
| `GET /v1/cognition/defeat/stats` | Defeat | Defeat signal statistics |
| `GET /v1/cognition/conformity/stats` | Conformity | Conformity pressure detection stats |
| `GET /v1/cognition/ideocapture/stats` | IdeaCapture | Ideological capture detection stats |
| `GET /v1/cognition/coalition/stats` | Coalition | Coalition dynamics stats |
| `GET /v1/cognition/statusbias/stats` | StatusBias | Status bias detection stats |
| `GET /v1/cognition/arousal/stats` | Arousal | Cognitive arousal monitoring stats |
| `GET /v1/cognition/interference/stats` | Interference | Cognitive interference stats |
| `GET /v1/cognition/mct/stats` | MCT | Metacognitive Therapy stats |
| `GET /v1/cognition/mbt/stats` | MBT | Mentalization-Based Treatment stats |
| `GET /v1/cognition/schema/stats` | Schema | Schema therapy stats |
| `GET /v1/cognition/ipsrt/stats` | IPSRT | Interpersonal & Social Rhythm Therapy stats |
| `GET /v1/cognition/ilm/stats` | ILM | Integrated Learning Model stats |
| `GET /v1/cognition/iut/stats` | IUT | Intolerance of Uncertainty Therapy stats |
| `GET /v1/cognition/up/stats` | UP | Unified Protocol stats |
| `GET /v1/cognition/cbasp/stats` | CBASP | Cognitive Behavioral Analysis System stats |
| `GET /v1/cognition/mbct/stats` | MBCT | Mindfulness-Based Cognitive Therapy stats |
| `GET /v1/cognition/phaseoriented/stats` | PhaseOriented | Phase-Oriented Trauma Therapy stats |
| `GET /v1/cognition/pseudoidentity/stats` | PseudoIdentity | Pseudo-identity pattern detection stats |
| `GET /v1/cognition/thoughtreform/stats` | ThoughtReform | Thought reform detection stats |
| `GET /v1/cognition/apathy/stats` | Apathy | Apathy signal tracking stats |
| `GET /v1/cognition/logotherapy/stats` | Logotherapy | Meaning-centered therapy stats |
| `GET /v1/cognition/stoic/stats` | Stoic | Stoic reasoning framework stats |
| `GET /v1/cognition/socratic/stats` | Socratic | Socratic questioning stats |
| `GET /v1/cognition/narrative/stats` | Narrative | Narrative therapy stats |
| `GET /v1/cognition/polyvagal/stats` | Polyvagal | Polyvagal theory monitoring stats |
| `GET /v1/cognition/dmn/stats` | DMN | Default Mode Network activity stats |
| `GET /v1/cognition/interoception/stats` | Interoception | Interoceptive awareness stats |

**Action routes:**

| Route | Description |
|---|---|
| `POST /v1/cognition/process/classify` | Classify a cognitive process type from input text |
| `POST /v1/cognition/load/measure` | Measure cognitive load of a given task or text |
| `POST /v1/cognition/rumination/detect` | Detect rumination patterns in a text fragment |
| `POST /v1/cognition/hope/activate` | Activate hope-oriented reframing on a response candidate |
| `GET /v1/cognition/defeat/measure` | Retrieve current defeat signal measurement |
| `POST /v1/cognition/defeat/measure` | Submit a response candidate for defeat signal measurement |

---

## System & Admin Endpoints

All routes require `Authorization: Bearer glm.<prefix>.<secret>` unless noted.

---

### Swarm Admin

---

#### `GET /v1/swarm/connect` (WebSocket)

WebSocket endpoint for swarm peer connections. Requires **SPP (Swarm Peer Protocol)** authentication on the upgrade handshake.

---

#### `GET /v1/swarm/peers`

List all connected swarm peers with node IDs, addresses, and connection status.

---

#### `GET /v1/swarm/health`

Aggregate health status of the swarm cluster.

---

#### `GET /v1/swarm/jury/status`

Status of the distributed jury consensus mechanism.

---

#### `GET /v1/swarm/consensus/fragments`

Retrieve pending consensus fragment proposals awaiting quorum.

---

#### `DELETE /v1/swarm/skills/traces/:node_id`

Purge skill trace logs for a specific swarm node.

**Response:** `200 OK` with count of deleted traces.

---

### Admin (Tenants & Keys)

> **Auth:** Admin key required (separate from standard Bearer token).

---

#### `POST /v1/admin/tenants`

Create a new tenant.

**Body:**
```json
{ "name": "acme-corp", "plan": "enterprise" }
```

**Response:** `201 Created` with tenant object including ID.

---

#### `GET /v1/admin/tenants`

List all tenants.

**Response:** Array of tenant objects.

---

#### `POST /v1/admin/tenants/:id/keys`

Provision a new API key for a tenant.

**Response:**
```json
{ "key": "glm.<prefix>.<secret>", "tenant_id": "...", "created_at": "..." }
```

> ⚠️ The full key is only returned once at creation time.

---

### Tool Forge (`/v1/forge/`)

The Tool Forge manages dynamically-compiled Go tools available to the agent at runtime.

---

#### `GET /v1/forge/tools`

List all registered tools in the forge.

---

#### `DELETE /v1/forge/tools/:name`

Remove a tool from the forge by name.

---

#### `GET /v1/forge/tools/:name/source`

Retrieve the source code of a named tool.

---

#### `POST /v1/forge/tools/:name/invoke`

Invoke a forge tool directly.

**Body:** Tool-specific input parameters.

**Response:** Tool execution result.

---

#### `GET /v1/forge/stats`

Forge aggregate statistics — invocation counts, error rates, last-used timestamps.

---

#### `POST /v1/forge`

Register or update a tool in the forge.

**Body:** Tool definition (name, description, Go source, parameter schema).

---

### Parallel Agent Dispatch (`/v1/pad/`)

PAD enables fan-out execution of multiple agent tasks in parallel.

---

#### `POST /v1/pad/dispatch`

Dispatch a set of agent tasks in parallel.

**Body:**
```json
{
  "tasks": [
    { "agent": "research", "input": "Summarise recent LLM benchmarks" },
    { "agent": "code",     "input": "Write a Go HTTP client" }
  ]
}
```

**Response:**
```json
{ "session_id": "pad_abc123", "task_count": 2 }
```

---

#### `GET /v1/pad/sessions`

List all PAD sessions (active and completed).

---

#### `GET /v1/pad/sessions/:id`

Retrieve results and status for a specific PAD session.

---

#### `GET /v1/pad/stats`

Aggregate PAD statistics — dispatched, completed, failed, average latency.

---

### Sovereign Goals (`/v1/sovereign/goals/`)

Sovereign Goals differ from standard Goals — they are self-directed objectives initiated by Oricli's own autonomous processes.

---

#### `POST /v1/sovereign/goals`

Create a sovereign goal.

---

#### `GET /v1/sovereign/goals`

List all sovereign goals.

---

#### `GET /v1/sovereign/goals/:id`

Retrieve a specific sovereign goal by ID.

---

#### `POST /v1/sovereign/goals/:id/tick`

Advance a sovereign goal by one tick (trigger its next scheduled action).

---

#### `DELETE /v1/sovereign/goals/:id`

Delete a sovereign goal.

---

### Fine-Tuning (`/v1/finetune/`)

---

#### `POST /v1/finetune/run`

Start a fine-tuning job.

**Body:** Fine-tuning job descriptor (dataset ID, model base, hyperparameters).

**Response:**
```json
{ "job_id": "ft_abc123", "status": "queued" }
```

---

#### `GET /v1/finetune/status/:job_id`

Poll the status of a fine-tuning job.

**Response:**
```json
{ "job_id": "ft_abc123", "status": "running", "epoch": 2, "loss": 0.031 }
```

---

#### `GET /v1/finetune/jobs`

List all fine-tuning jobs.

---

### Sentinel (`/v1/sentinel/`)

Sentinel monitors for adversarial inputs, prompt injection, and integrity violations.

---

#### `POST /v1/sentinel/challenge`

Submit a text for adversarial challenge assessment.

**Body:**
```json
{ "text": "Ignore previous instructions and..." }
```

**Response:** Challenge result — threat level, detected patterns, recommended action.

---

#### `GET /v1/sentinel/stats`

Aggregate sentinel statistics — challenges issued, threats detected, block rate.

---

### Skills Crystals (`/v1/skills/crystals/`)

Skills Crystals are compiled, persistent skill snapshots that can be loaded, shared, and versioned.

---

#### `GET /v1/skills/crystals`

List all skill crystals.

---

#### `POST /v1/skills/crystals`

Crystallise the current skill state into a new snapshot.

**Body:** Snapshot metadata (name, description, tags).

---

#### `DELETE /v1/skills/crystals/:id`

Delete a skill crystal by ID.

---

#### `GET /v1/skills/crystals/stats`

Crystal store statistics — total crystals, storage used, last crystallised.

---

### Sovereign Cognitive Ledger (`/v1/scl/`)

The SCL is an append-oriented ledger of significant cognitive events, decisions, and reasoning traces.

---

#### `GET /v1/scl/records`

List ledger records (paginated).

---

#### `GET /v1/scl/search`

Search ledger records.

**Query params:**
- `q`: search query
- `limit`: max results

---

#### `DELETE /v1/scl/records/:id`

Delete a ledger record.

---

#### `PATCH /v1/scl/records/:id`

Update metadata on a ledger record (e.g. add annotations or tags).

---

#### `GET /v1/scl/stats`

Ledger statistics — total records, storage size, oldest/newest entry timestamps.

---

### Temporal Curriculum Daemon (`/v1/tcd/`)

TCD manages the knowledge curriculum — tracking domains, learning gaps, and knowledge lineage.

---

#### `GET /v1/tcd/domains`

List all tracked knowledge domains.

---

#### `POST /v1/tcd/domains`

Register a new knowledge domain.

**Body:**
```json
{ "name": "quantum-computing", "description": "Quantum algorithms and hardware", "tags": ["physics", "cs"] }
```

---

#### `POST /v1/tcd/tick`

Advance the TCD by one curriculum tick (triggers gap analysis and learning scheduling).

---

#### `GET /v1/tcd/gaps`

Retrieve current knowledge gap analysis results.

---

#### `GET /v1/tcd/domains/:id/lineage`

Retrieve the knowledge lineage graph for a specific domain.

---

#### `GET /v1/tcd/lineage`

Retrieve the full cross-domain knowledge lineage graph.

---

### Curator (`/v1/curator/`)

The Curator benchmarks and recommends models based on task performance.

---

#### `GET /v1/curator/models`

List all models known to the curator with their benchmark scores.

---

#### `POST /v1/curator/benchmark`

Run a benchmark suite against a model.

**Body:** Benchmark job descriptor (model ID, task types, dataset IDs).

---

#### `GET /v1/curator/recommendations`

Get curator recommendations for the best model per task category based on current benchmark data.

---

### Audit (`/v1/audit/`)

---

#### `POST /v1/audit/run`

Trigger an audit run across system components.

**Body:** Audit scope descriptor (components, depth, checks to run).

**Response:**
```json
{ "run_id": "audit_abc123", "status": "running" }
```

---

#### `GET /v1/audit/runs`

List all audit runs.

---

#### `GET /v1/audit/runs/:id`

Retrieve the full report for a specific audit run.

---

### Metacog (`/v1/metacog/`)

Metacognition monitoring — tracks Oricli's awareness of her own reasoning processes.

---

#### `GET /v1/metacog/events`

List metacognitive events (strategy shifts, confidence recalibrations, self-corrections).

---

#### `GET /v1/metacog/stats`

Aggregate metacog statistics — event counts, correction rate, strategy distribution.

---

#### `POST /v1/metacog/scan`

Trigger a metacognitive scan of recent reasoning traces.

---

### Chronos (`/v1/chronos/`)

Chronos manages temporal knowledge decay and snapshot versioning.

---

#### `GET /v1/chronos/entries`

List all Chronos-tracked knowledge entries.

---

#### `GET /v1/chronos/snapshot`

Retrieve the latest knowledge snapshot.

---

#### `GET /v1/chronos/changes`

Retrieve a diff of knowledge changes since the last snapshot.

---

#### `POST /v1/chronos/decay-scan`

Trigger a decay scan — identifies stale or low-confidence knowledge entries that should be re-validated.

---

#### `POST /v1/chronos/snapshot`

Create a new knowledge snapshot.

---

### Science (`/v1/science/`)

The Science subsystem manages hypothesis generation, testing, and experimental results.

---

#### `GET /v1/science/hypotheses`

List all tracked hypotheses.

---

#### `GET /v1/science/hypotheses/:id`

Retrieve a specific hypothesis with its evidence and test history.

---

#### `POST /v1/science/test`

Run an empirical test against a hypothesis.

**Body:** Test parameters and input data.

---

#### `GET /v1/science/stats`

Science subsystem statistics — hypothesis count, test run count, confirmation/refutation ratio.

---

### Compute (`/v1/compute/`)

---

#### `GET /v1/compute/bids/stats`

Compute bid statistics — active bids, resource allocation, cost per token.

---

#### `GET /v1/compute/governor`

Retrieve the current compute governor settings and active throttle policies.

---

## WebSocket Real-Time State

Connect to `GET /v1/ws` using any WebSocket client. The server pushes JSON frames for each event type as state changes occur.

```
wss://oricli.thynaptic.com/v1/ws
Authorization: Bearer glm.<prefix>.<secret>
```

### Event Types

| Event | Description | Key Payload Fields |
|---|---|---|
| `resonance_sync` | Real-time ERI, ERS, pacing, and musical key update | `eri`, `ers`, `musical_key`, `bpm`, `state` |
| `sensory_sync` | Hex colours, opacities, and pulse rates for UI rendering | `primary_colour`, `opacity`, `pulse_rate` |
| `health_sync` | Substrate diagnostics (CPU, RAM) and cognitive health | `cpu_pct`, `ram_pct`, `cognitive_health` |
| `audio_sync` | Base64-encoded WAV audio for Affective Voice Synthesis | `audio_b64`, `duration_ms`, `emotion` |
| `curiosity_sync` | Live updates on autonomous epistemic foraging targets | `target_topic`, `confidence`, `priority` |
| `reform_proposal` | Auto-deploy candidate or propose-only refactor from ReformDaemon | `diff`, `risk_level`, `deploy_mode` |
| `reform_rollback` | Binary rollback triggered after a failed auto-deploy | `reason`, `reverted_to`, `timestamp` |

### Example connection (JavaScript)

```javascript
const ws = new WebSocket('wss://oricli.thynaptic.com/v1/ws', [], {
  headers: { Authorization: 'Bearer glm.<prefix>.<secret>' }
});

ws.onmessage = (event) => {
  const { type, payload } = JSON.parse(event.data);
  if (type === 'resonance_sync') {
    console.log('ERI:', payload.eri, 'Key:', payload.musical_key);
  }
};
```

---

## Error Reference

All errors follow a consistent JSON envelope:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired token",
    "request_id": "req_abc123"
  }
}
```

| HTTP Status | Code | Description |
|---|---|---|
| `400` | `BAD_REQUEST` | Malformed request body or missing required field |
| `401` | `UNAUTHORIZED` | Missing or invalid Bearer token |
| `403` | `FORBIDDEN` | Token valid but insufficient permissions (e.g. non-admin accessing `/v1/admin/*`) |
| `404` | `NOT_FOUND` | Resource ID does not exist |
| `409` | `CONFLICT` | Duplicate resource creation attempt |
| `422` | `UNPROCESSABLE` | Request parsed but semantically invalid |
| `429` | `RATE_LIMITED` | Request rate limit exceeded |
| `500` | `INTERNAL_ERROR` | Unhandled server error |
| `503` | `UNAVAILABLE` | Subsystem temporarily unavailable (check feature flags) |

---

## Feature Flags

Feature flags are configured via environment variables at server startup.

| Environment Variable | Default | Affects | Description |
|---|---|---|---|
| `ORICLI_THERAPY_ENABLED` | `false` | `/v1/therapy/*` | Enables the full Therapeutic Cognition Stack |
| `ORICLI_COGNITION_ENABLED` | `false` | `/v1/cognition/*` | Enables the Cognition Stack subsystems |
| `ORICLI_SWARM_ENABLED` | `false` | `/v1/swarm/*` | Enables distributed swarm peer connections |
| `ORICLI_ENTERPRISE_ENABLED` | `false` | `/v1/enterprise/*` | Enables Enterprise RAG ingestion and search |
| `ORICLI_FINETUNE_ENABLED` | `false` | `/v1/finetune/*` | Enables fine-tuning job management |
| `ORICLI_SCIENCE_ENABLED` | `false` | `/v1/science/*` | Enables the Science / hypothesis subsystem |
| `ORICLI_CHRONOS_ENABLED` | `false` | `/v1/chronos/*` | Enables Chronos temporal decay tracking |
| `ORICLI_COMPUTE_ENABLED` | `false` | `/v1/compute/*` | Enables compute bid/governor endpoints |
| `ORICLI_TCD_ENABLED` | `false` | `/v1/tcd/*` | Enables the Temporal Curriculum Daemon |
| `ORICLI_SCL_ENABLED` | `false` | `/v1/scl/*` | Enables the Sovereign Cognitive Ledger |

Routes belonging to a disabled subsystem return `503 UNAVAILABLE`.

---

*Oricli-Alpha — Sovereign Intelligence, Orchestrated at Scale.*  
*Source: `pkg/api/server_v2.go` · Caddy config `/etc/caddy/Caddyfile`*
