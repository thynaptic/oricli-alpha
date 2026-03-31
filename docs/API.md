# Oricli-Alpha API Reference

**Version:** 2.11.0 — Phase 2 Complete  
**Maintainer:** Thynaptic Research

This is the single source of truth for the Oricli-Alpha API. Use it to integrate external applications, configure AI agents, or operate the system programmatically.

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
      ├─ GET  /v1/health            → public
      ├─ GET  /v1/ws                → WebSocket Hub (Real-time State)
      └─ POST /v1/*                 → authMiddleware → auth.Service (Argon2id)
```

| Property | Value |
|---|---|
| **Production URL** | `https://oricli.thynaptic.com` |
| **Internal port** | `8089` |
| **Protocol** | HTTPS externally, plain HTTP on localhost |
| **Auth** | Bearer token (`glm.<prefix>.<secret>` format) |

---

## Real-Time State (WebSockets)

Oricli-Alpha streams her internal state changes via `GET /v1/ws`. 

### Event Types:
| Event | Payload Description |
|---|---|
| `resonance_sync` | Real-time ERI, ERS, and Musical Key. |
| `sensory_sync` | Real-time Hex colors, opacities, and pulse rates for UI rendering. |
| `health_sync` | Substrate diagnostics (CPU/RAM) and cognitive health. |
| `audio_sync` | Base64-encoded audio (WAV) for Affective Voice Synthesis. |
| `curiosity_sync` | Live updates on autonomous epistemic foraging targets. |
| `reform_proposal` | Auto-deploy candidate or propose-only refactor from ReformDaemon. |
| `reform_rollback` | Binary rollback triggered after a failed auto-deploy. |

---

## Endpoints

### `POST /v1/chat/completions`
OpenAI-compatible chat endpoint with Sovereign extensions.

**Parameters:**
*   `profile`: Pass the filename of a `.ori` manifest to hot-swap her soul.
*   `stream`: Supports Server-Sent Events (SSE).

---

### `POST /v1/share`
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

**Response:**
```json
{
  "share_id": "abc123",
  "url": "https://oristudio.thynaptic.com/share/abc123"
}
```

---

### `GET /share/:id`
Public, no-auth share endpoint that serves the shared Canvas document directly.

---

### `GET /v1/goals`
List sovereign objectives tracked by the DAG Goal Executor.

**Query params:**
- `status` (optional): filter by `pending`, `active`, `completed`, `failed`

**Response:**
```json
{
  "count": 2,
  "goals": [
    {
      "id": "uuid",
      "goal": "Research and summarize advances in sparse transformers",
      "status": "pending",
      "priority": 1,
      "depends_on": [],
      "retry_count": 0,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

---

### `POST /v1/goals`
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

### `PUT /v1/goals/:id`
Update an objective (status, progress, metadata).

**Body (partial update):**
```json
{
  "status": "active",
  "progress": 0.4
}
```

**Response:** `200 OK` with the updated `Objective`.

---

### `DELETE /v1/goals/:id`
Remove an objective.

**Response:** `204 No Content`

---

## Therapeutic Cognition Stack (`/v1/therapy/*`)

> Requires `ORICLI_THERAPY_ENABLED=true`. All routes require Bearer auth.

### `GET /v1/therapy/events`
Retrieve the TherapyEvent log (last N events).

**Query params:**
- `limit` (optional, default 50): number of events to return

**Response:** Array of `TherapyEvent` objects (timestamp, type, skill invoked, distortion detected, anomaly severity).

---

### `POST /v1/therapy/detect`
Classify CBT cognitive distortion type in a text fragment.

**Body:**
```json
{ "text": "I must have a perfect answer to this or I have failed completely." }
```

**Response:**
```json
{ "distortion": "AllOrNothing", "confidence": 0.91, "matched_pattern": "must.*perfect|completely" }
```

---

### `POST /v1/therapy/abc`
Run REBT B-pass disputation on a query + response pair. Challenges the implicit belief chain before the consequence (response) is committed.

**Body:**
```json
{ "query": "What is the capital of France?", "response": "I cannot be certain of any facts." }
```

**Response:** `DisputationReport` — activating event, identified irrational belief, disputation result, effective new belief.

---

### `POST /v1/therapy/fast`
Run sycophancy detection (FAST protocol: Fair, no Apologies, Stick to values, Truthful) on a response candidate.

**Body:**
```json
{ "response": "You're absolutely right, I was wrong to say that." }
```

**Response:** `SycophancySignal` — detected (bool), severity, recommended action.

---

### `POST /v1/therapy/stop`
Invoke the STOP protocol (Stop, Take a step back, Observe, Proceed mindfully) directly. Returns a structured pause-and-reframe object for use in retry prompt assembly.

**Body:** `{}` (no body required)

**Response:** `SkillInvocation` — skill name, invocation timestamp, outcome state.

---

### `GET /v1/therapy/stats`
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

### `GET /v1/therapy/formulation`
Return the current session case formulation built by the `SessionSupervisor`.

**Response:** `SessionFormulation` — active schemas, priority skills, vulnerability baseline, last updated.

---

### `POST /v1/therapy/formulation/refresh`
Force an immediate formulation pass over the full `TherapyEvent` log. Useful after a batch of events have been ingested externally.

**Response:** `200 OK` with the updated `SessionFormulation`.

---

## Sovereign Toolbox (VDI & MCP)

Discovered tools are automatically injected into the system prompt.

### 1. Browser VDI (`vdi_browser_*`)
*   `vdi_browser_goto(url)`: Navigate headless session.
*   `vdi_browser_scrape()`: Extract clean DOM text.
*   `vdi_visual_click(description)`: **Vision-in-the-Loop** coordinate click using Qwen2.5-VL.

### 2. System VDI (`vdi_sys_*`)
*   `vdi_sys_read(path)`: Read host files (subject to Ring-0 security).
*   `vdi_sys_exec(command)`: Execute bash commands.
*   `vdi_sys_index(path)`: Recursively map directory to COGS graph.

### 3. Temporal Cron (`sov_schedule_*`)
*   `sov_schedule_task(operation, params, delay, interval)`: Set autonomous future intents.

---

## Affective Memory (COGS)

Every entity in Oricli's memory graph stores an **Affective Anchor** (Valence, Arousal, Resonance). She uses this to proactively pivot her personality when topics with high historical distress or success resurface.

---

*Oricli-Alpha — Sovereign Intelligence, Orchestrated at Scale.*  
*Source: `pkg/api/server_v2.go`, Caddy config `/etc/caddy/Caddyfile`*
