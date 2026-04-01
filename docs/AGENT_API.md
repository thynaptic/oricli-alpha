# ORI Studio API — Agent Reference (v11.0.0)

Sovereign AI API with OpenAI-compatible chat, autonomous goal execution, cognitive state streaming, and enterprise RAG. Go/Gin backbone.

---

## Base URL & Auth

```
BASE_URL  = https://oricli.thynaptic.com
AUTH      = Authorization: Bearer glm.<prefix>.<secret>
ADMIN     = Authorization: Bearer <admin-key>
VERSION   = v11.0.0
```

Three auth tiers:
- **No auth** — public endpoints, scrapers, WebSocket
- **Bearer `glm.*.*`** — standard user API key
- **Admin key** — elevated ops (admin/swarm-admin/SCL/TCD/Forge/etc.)

---

## Quick-Start: Minimal Chat

```bash
curl -s https://oricli.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ori",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

---

## Endpoint Index

### Public (no auth)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/share/:id` | Retrieve shared Canvas artifact (HTML) |
| GET | `/v1/health` | Readiness probe |
| GET | `/v1/eri` | ERI/ERS resonance state |
| GET | `/v1/ws` | WebSocket real-time state hub |
| GET | `/v1/traces` | Recent reasoning traces |
| GET | `/v1/loglines` | Recent log lines |
| GET | `/v1/modules` | List active modules/skills |
| GET | `/v1/metrics` | Prometheus metrics (scraper use) |
| GET | `/v1/swarm/connect` | SPP peer connection (SPP handshake auth) |
| POST | `/v1/waitlist` | Waitlist/SMB signup |
| GET | `/v1/compute/bids/stats` | Sovereign compute bid stats |
| GET | `/v1/compute/governor` | Compute governor state |
| GET | `/v1/cognition/process/stats` | Process cognition stats |
| POST | `/v1/cognition/process/classify` | Classify cognitive process |
| GET | `/v1/cognition/load/stats` | Cognitive load stats |
| POST | `/v1/cognition/load/measure` | Measure cognitive load |
| GET | `/v1/cognition/rumination/stats` | Rumination stats |
| POST | `/v1/cognition/rumination/detect` | Detect rumination |
| GET | `/v1/cognition/mindset/stats` | Mindset stats |
| GET | `/v1/cognition/mindset/vectors` | Mindset vectors |
| GET | `/v1/cognition/hope/stats` | Hope module stats |
| POST | `/v1/cognition/hope/activate` | Activate hope signal |
| GET | `/v1/cognition/defeat/stats` | Defeat module stats |
| GET/POST | `/v1/cognition/defeat/measure` | Measure defeat state |
| GET | `/v1/cognition/conformity/stats` | Conformity bias stats |
| GET | `/v1/cognition/ideocapture/stats` | Ideological capture stats |
| GET | `/v1/cognition/coalition/stats` | Coalition dynamics stats |
| GET | `/v1/cognition/statusbias/stats` | Status bias stats |
| GET | `/v1/cognition/arousal/stats` | Arousal regulation stats |
| GET | `/v1/cognition/interference/stats` | Cognitive interference stats |
| GET | `/v1/cognition/mct/stats` | MCT (metacognitive therapy) stats |
| GET | `/v1/cognition/mbt/stats` | MBT stats |
| GET | `/v1/cognition/schema/stats` | Schema therapy stats |
| GET | `/v1/cognition/ipsrt/stats` | IPSRT stats |
| GET | `/v1/cognition/ilm/stats` | ILM stats |
| GET | `/v1/cognition/iut/stats` | Intolerance of uncertainty stats |
| GET | `/v1/cognition/up/stats` | Unified Protocol stats |
| GET | `/v1/cognition/cbasp/stats` | CBASP stats |
| GET | `/v1/cognition/mbct/stats` | MBCT stats |
| GET | `/v1/cognition/phaseoriented/stats` | Phase-oriented therapy stats |
| GET | `/v1/cognition/pseudoidentity/stats` | Pseudo-identity stats |
| GET | `/v1/cognition/thoughtreform/stats` | Thought reform stats |
| GET | `/v1/cognition/apathy/stats` | Apathy stats |
| GET | `/v1/cognition/logotherapy/stats` | Logotherapy stats |
| GET | `/v1/cognition/stoic/stats` | Stoic cognition stats |
| GET | `/v1/cognition/socratic/stats` | Socratic method stats |
| GET | `/v1/cognition/narrative/stats` | Narrative therapy stats |
| GET | `/v1/cognition/polyvagal/stats` | Polyvagal theory stats |
| GET | `/v1/cognition/dmn/stats` | Default mode network stats |
| GET | `/v1/cognition/interoception/stats` | Interoception stats |

### Protected (Bearer `glm.*.*`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat/completions` | OpenAI-compatible chat (stream, tools, profile, reasoning) |
| POST | `/v1/images/generations` | Image generation |
| POST | `/v1/swarm/run` | Distributed swarm execution |
| POST | `/v1/ingest` | Knowledge ingestion (raw text) |
| POST | `/v1/ingest/web` | Web URL ingestion |
| POST | `/v1/telegram/webhook` | Telegram bot webhook |
| GET | `/v1/goals` | List DAG goals |
| GET | `/v1/goals/:id` | Get goal by ID |
| POST | `/v1/goals` | Create DAG goal |
| PUT | `/v1/goals/:id` | Update DAG goal |
| DELETE | `/v1/goals/:id` | Cancel DAG goal |
| POST | `/v1/sovereign/goals` | Create sovereign goal (Phase 10 engine) |
| GET | `/v1/sovereign/goals` | List sovereign goals |
| GET | `/v1/sovereign/goals/:id` | Get sovereign goal |
| POST | `/v1/sovereign/goals/:id/tick` | Manually tick sovereign goal execution |
| DELETE | `/v1/sovereign/goals/:id` | Cancel sovereign goal |
| GET | `/v1/daemons` | Daemon health statuses |
| GET | `/v1/memories` | Episodic memories (`?limit=N`) |
| GET | `/v1/memories/knowledge` | Knowledge memories (`?q=query&limit=N`) |
| POST | `/v1/documents/upload` | Multipart file upload |
| GET | `/v1/documents` | List documents |
| POST | `/v1/feedback` | Reaction feedback |
| POST | `/v1/share` | Create Canvas public share link |
| POST | `/v1/agents/vibe` | Natural-language agent creation |
| POST | `/v1/vision/analyze` | Image analysis (moondream) |
| GET | `/v1/sovereign/identity` | Get active .ori profile |
| PUT | `/v1/sovereign/identity` | Update .ori profile |
| POST | `/v1/enterprise/learn` | Start namespace-isolated RAG ingest job |
| GET | `/v1/enterprise/learn/:job_id` | Poll ingest job status |
| GET | `/v1/enterprise/knowledge/search` | Semantic search (`?q=&namespace=&top_k=`) |
| DELETE | `/v1/enterprise/knowledge` | Clear namespace (`?namespace=`) |
| POST | `/v1/pad/dispatch` | Dispatch parallel agents |
| GET | `/v1/pad/sessions` | List PAD sessions |
| GET | `/v1/pad/sessions/:id` | Get PAD session |
| GET | `/v1/pad/stats` | PAD metrics |
| POST | `/v1/finetune/run` | Start LoRA fine-tune job |
| GET | `/v1/finetune/status/:job_id` | Poll fine-tune status |
| GET | `/v1/finetune/jobs` | List fine-tune jobs |
| POST | `/v1/sentinel/challenge` | Adversarially challenge a plan/content |
| GET | `/v1/sentinel/stats` | Sentinel activity stats |
| GET | `/v1/skills/crystals` | List crystallized skills |
| POST | `/v1/skills/crystals` | Register crystallized skill |
| DELETE | `/v1/skills/crystals/:id` | Evict crystal |
| GET | `/v1/skills/crystals/stats` | Crystal cache stats |
| GET | `/v1/curator/models` | List curated models |
| POST | `/v1/curator/benchmark` | Run model benchmark |
| GET | `/v1/curator/recommendations` | Model recommendations |
| POST | `/v1/audit/run` | Run self-audit |
| GET | `/v1/audit/runs` | List audit runs |
| GET | `/v1/audit/runs/:id` | Get audit run detail |
| GET | `/v1/metacog/events` | Metacognitive events |
| GET | `/v1/metacog/stats` | Metacog stats |
| POST | `/v1/metacog/scan` | Trigger metacog scan |
| GET | `/v1/chronos/entries` | Temporal memory entries |
| GET | `/v1/chronos/snapshot` | Current temporal snapshot |
| GET | `/v1/chronos/changes` | Recent changes |
| POST | `/v1/chronos/decay-scan` | Trigger memory decay scan |
| POST | `/v1/chronos/snapshot` | Force snapshot |
| GET | `/v1/science/hypotheses` | List hypotheses |
| GET | `/v1/science/hypotheses/:id` | Get hypothesis |
| POST | `/v1/science/test` | Submit hypothesis for testing |
| GET | `/v1/science/stats` | Science engine stats |
| GET | `/v1/therapy/events` | Therapy event log |
| POST | `/v1/therapy/detect` | Detect cognitive distortion in text |
| POST | `/v1/therapy/abc` | REBT B-pass disputation |
| POST | `/v1/therapy/fast` | Sycophancy detection pass |
| POST | `/v1/therapy/stop` | Invoke STOP skill |
| GET | `/v1/therapy/stats` | Therapy stats |
| GET | `/v1/therapy/formulation` | Current case formulation |
| POST | `/v1/therapy/formulation/refresh` | Refresh formulation |
| GET | `/v1/therapy/mastery` | Learned mastery tracker |
| POST | `/v1/therapy/helplessness/check` | Check for learned helplessness signals |
| GET | `/v1/therapy/helplessness/stats` | Helplessness detection stats |

### Admin (admin-key required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/admin/tenants` | Create tenant |
| GET | `/v1/admin/tenants` | List tenants |
| POST | `/v1/admin/tenants/:id/keys` | Create API key for tenant |
| GET | `/v1/swarm/peers` | List swarm peers |
| GET | `/v1/swarm/health` | Swarm health |
| GET | `/v1/swarm/jury/status` | Hive Mind consensus jury status |
| GET | `/v1/swarm/consensus/fragments` | Consensus fragments |
| DELETE | `/v1/swarm/skills/traces/:node_id` | Purge skill traces for a node |
| GET | `/v1/scl/records` | Browse SCL records |
| GET | `/v1/scl/search` | Search SCL |
| DELETE | `/v1/scl/records/:id` | Delete SCL record |
| PATCH | `/v1/scl/records/:id` | Revise SCL record |
| GET | `/v1/scl/stats` | SCL stats |
| GET | `/v1/tcd/domains` | List knowledge domains |
| POST | `/v1/tcd/domains` | Add domain |
| POST | `/v1/tcd/tick` | Trigger manual TCD tick |
| GET | `/v1/tcd/gaps` | Knowledge gap analysis |
| GET | `/v1/tcd/domains/:id/lineage` | Concept lineage for domain |
| GET | `/v1/tcd/lineage` | Full evolution tree |
| GET | `/v1/forge/tools` | List forged tools |
| DELETE | `/v1/forge/tools/:name` | Delete forged tool |
| GET | `/v1/forge/tools/:name/source` | Get tool source code |
| POST | `/v1/forge/tools/:name/invoke` | Invoke forged tool |
| GET | `/v1/forge/stats` | Forge stats |
| POST | `/v1/forge/forge` | Attempt to forge a new tool from spec |

---

## Key Endpoint Shapes

### `POST /v1/chat/completions`

**Request:**
```json
{
  "model": "ori",
  "messages": [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Explain black holes"}
  ],
  "stream": false,
  "profile": "scientist.ori",
  "tools": [],
  "reasoning": true
}
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1720000000,
  "model": "ori",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Black holes are regions of spacetime..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 120,
    "total_tokens": 140
  }
}
```

---

### Goals CRUD (DAG executor)

**POST /v1/goals** — Create goal:
```json
{
  "title": "Research quantum computing trends",
  "description": "Summarise the last 6 months of arXiv papers on quantum error correction",
  "priority": "high"
}
```

**Response:**
```json
{
  "id": "goal_xyz789",
  "title": "Research quantum computing trends",
  "status": "pending",
  "created_at": "2025-01-01T00:00:00Z"
}
```

**GET /v1/goals/:id** — Poll status:
```json
{
  "id": "goal_xyz789",
  "status": "running",
  "progress": 0.4,
  "result": null
}
```
`status` values: `pending` | `running` | `complete` | `failed` | `cancelled`

**DELETE /v1/goals/:id** — Cancel; returns `204 No Content`.

---

### Sovereign Goals (Phase 10 engine)

Separate from DAG goals. The Phase 10 engine manages sovereign goal lifecycle with tick-based execution.

```bash
# Create sovereign goal
curl -X POST https://oricli.thynaptic.com/v1/sovereign/goals \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Monitor system health", "description": "...", "priority": "high"}'

# Manually tick execution
curl -X POST https://oricli.thynaptic.com/v1/sovereign/goals/<id>/tick \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

### `GET /v1/memories` & `GET /v1/memories/knowledge`

```
GET /v1/memories?limit=20
GET /v1/memories/knowledge?q=quantum&limit=10
```

**Response:**
```json
{
  "memories": [
    {
      "id": "mem_001",
      "content": "User asked about quantum computing on 2025-01-01",
      "type": "episodic",
      "created_at": "2025-01-01T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

### `POST /v1/documents/upload` & `GET /v1/documents`

**Upload:**
```bash
curl -X POST https://oricli.thynaptic.com/v1/documents/upload \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -F "file=@report.pdf"
```

**Response:**
```json
{
  "document_id": "doc_abc",
  "filename": "report.pdf",
  "status": "ingested"
}
```

**List:**
```
GET /v1/documents
```
```json
{
  "documents": [
    {"id": "doc_abc", "filename": "report.pdf", "created_at": "2025-01-01T00:00:00Z"}
  ]
}
```

---

### `GET /v1/health`

```json
{
  "status": "ready",
  "system": "ori-v2",
  "pure_go": true
}
```

---

### Enterprise RAG

```bash
# Start ingest
curl -X POST https://oricli.thynaptic.com/v1/enterprise/learn \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"text": "...", "namespace": "acme-corp"}'
# Returns: {"job_id": "job_abc"}

# Poll status
curl https://oricli.thynaptic.com/v1/enterprise/learn/job_abc \
  -H "Authorization: Bearer glm.<prefix>.<secret>"

# Semantic search
curl "https://oricli.thynaptic.com/v1/enterprise/knowledge/search?q=pricing&namespace=acme-corp&top_k=5" \
  -H "Authorization: Bearer glm.<prefix>.<secret>"

# Clear namespace
curl -X DELETE "https://oricli.thynaptic.com/v1/enterprise/knowledge?namespace=acme-corp" \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

### Admin

```bash
# Create tenant
curl -X POST https://oricli.thynaptic.com/v1/admin/tenants \
  -H "Authorization: Bearer <admin-key>" \
  -H "Content-Type: application/json" \
  -d '{"name": "acme-corp", "tier": "enterprise"}'

# Create API key for tenant
curl -X POST https://oricli.thynaptic.com/v1/admin/tenants/<id>/keys \
  -H "Authorization: Bearer <admin-key>"
```

---

### Swarm Admin

```bash
curl https://oricli.thynaptic.com/v1/swarm/peers       -H "Authorization: Bearer <admin-key>"
curl https://oricli.thynaptic.com/v1/swarm/health      -H "Authorization: Bearer <admin-key>"
curl https://oricli.thynaptic.com/v1/swarm/jury/status -H "Authorization: Bearer <admin-key>"
curl https://oricli.thynaptic.com/v1/swarm/consensus/fragments -H "Authorization: Bearer <admin-key>"

# Purge skill traces for a node
curl -X DELETE https://oricli.thynaptic.com/v1/swarm/skills/traces/<node_id> \
  -H "Authorization: Bearer <admin-key>"
```

---

### SCL — Sovereign Cognitive Ledger

Immutable append-log of Ori's cognitive events. Admin-only.

```bash
curl "https://oricli.thynaptic.com/v1/scl/records"       -H "Authorization: Bearer <admin-key>"
curl "https://oricli.thynaptic.com/v1/scl/search?q=goal" -H "Authorization: Bearer <admin-key>"
curl "https://oricli.thynaptic.com/v1/scl/stats"         -H "Authorization: Bearer <admin-key>"

curl -X PATCH https://oricli.thynaptic.com/v1/scl/records/<id> \
  -H "Authorization: Bearer <admin-key>" \
  -H "Content-Type: application/json" \
  -d '{"note": "annotation"}'

curl -X DELETE https://oricli.thynaptic.com/v1/scl/records/<id> \
  -H "Authorization: Bearer <admin-key>"
```

---

### TCD — Temporal Curriculum Daemon

Manages long-horizon knowledge domains and gap analysis. Admin-only.

```bash
curl https://oricli.thynaptic.com/v1/tcd/domains          -H "Authorization: Bearer <admin-key>"
curl https://oricli.thynaptic.com/v1/tcd/gaps             -H "Authorization: Bearer <admin-key>"
curl https://oricli.thynaptic.com/v1/tcd/lineage          -H "Authorization: Bearer <admin-key>"
curl https://oricli.thynaptic.com/v1/tcd/domains/<id>/lineage -H "Authorization: Bearer <admin-key>"

curl -X POST https://oricli.thynaptic.com/v1/tcd/domains \
  -H "Authorization: Bearer <admin-key>" \
  -H "Content-Type: application/json" \
  -d '{"name": "quantum-computing", "description": "..."}'

curl -X POST https://oricli.thynaptic.com/v1/tcd/tick \
  -H "Authorization: Bearer <admin-key>"
```

---

### Forge — JIT Tool Forge

Dynamically forges and invokes tools at runtime. Admin-only.

```bash
# List forged tools
curl https://oricli.thynaptic.com/v1/forge/tools -H "Authorization: Bearer <admin-key>"

# Forge a new tool from spec
curl -X POST https://oricli.thynaptic.com/v1/forge/forge \
  -H "Authorization: Bearer <admin-key>" \
  -H "Content-Type: application/json" \
  -d '{"spec": "A tool that fetches RSS feeds and summarises them"}'

# Invoke a forged tool
curl -X POST https://oricli.thynaptic.com/v1/forge/tools/<name>/invoke \
  -H "Authorization: Bearer <admin-key>" \
  -H "Content-Type: application/json" \
  -d '{"args": {"url": "https://example.com/rss"}}'

# Get tool source
curl https://oricli.thynaptic.com/v1/forge/tools/<name>/source -H "Authorization: Bearer <admin-key>"

# Delete tool
curl -X DELETE https://oricli.thynaptic.com/v1/forge/tools/<name> -H "Authorization: Bearer <admin-key>"
```

---

### PAD — Parallel Agent Dispatch

Dispatch multiple agents concurrently; poll session results.

```bash
curl -X POST https://oricli.thynaptic.com/v1/pad/dispatch \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{
    "agents": [
      {"role": "researcher", "task": "Find recent papers on LLM alignment"},
      {"role": "critic",     "task": "Evaluate the researcher output"}
    ]
  }'
# Returns: {"session_id": "pad_abc"}

curl https://oricli.thynaptic.com/v1/pad/sessions/pad_abc \
  -H "Authorization: Bearer glm.<prefix>.<secret>"

curl https://oricli.thynaptic.com/v1/pad/stats \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

### FineTune — LoRA Training

```bash
# Start job
curl -X POST https://oricli.thynaptic.com/v1/finetune/run \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "ds_abc", "base_model": "ori", "epochs": 3}'
# Returns: {"job_id": "ft_xyz"}

# Poll status
curl https://oricli.thynaptic.com/v1/finetune/status/ft_xyz \
  -H "Authorization: Bearer glm.<prefix>.<secret>"

# List jobs
curl https://oricli.thynaptic.com/v1/finetune/jobs \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

### Sentinel — Adversarial Auditor

Challenges plans, reasoning chains, and content for logical/ethical flaws.

```bash
curl -X POST https://oricli.thynaptic.com/v1/sentinel/challenge \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"content": "We should deploy this plan immediately...", "mode": "adversarial"}'

curl https://oricli.thynaptic.com/v1/sentinel/stats \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

### Skills / Crystal Cache

Crystallized skills are pre-compiled, reusable reasoning units.

```bash
curl https://oricli.thynaptic.com/v1/skills/crystals \
  -H "Authorization: Bearer glm.<prefix>.<secret>"

curl -X POST https://oricli.thynaptic.com/v1/skills/crystals \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"name": "summarise-arxiv", "description": "...", "code": "..."}'

curl -X DELETE https://oricli.thynaptic.com/v1/skills/crystals/<id> \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

### Curator — Sovereign Model Curation

```bash
curl https://oricli.thynaptic.com/v1/curator/models \
  -H "Authorization: Bearer glm.<prefix>.<secret>"

curl -X POST https://oricli.thynaptic.com/v1/curator/benchmark \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"model_id": "llama3-8b", "task": "reasoning"}'

curl https://oricli.thynaptic.com/v1/curator/recommendations \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

### Audit — Self-Audit Loop

```bash
curl -X POST https://oricli.thynaptic.com/v1/audit/run \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"scope": "reasoning", "depth": "full"}'
# Returns: {"run_id": "audit_abc"}

curl https://oricli.thynaptic.com/v1/audit/runs \
  -H "Authorization: Bearer glm.<prefix>.<secret>"

curl https://oricli.thynaptic.com/v1/audit/runs/audit_abc \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

### Metacog — Metacognitive Sentience

Monitors Ori's own reasoning patterns for meta-level anomalies.

```bash
curl https://oricli.thynaptic.com/v1/metacog/events -H "Authorization: Bearer glm.<prefix>.<secret>"
curl https://oricli.thynaptic.com/v1/metacog/stats  -H "Authorization: Bearer glm.<prefix>.<secret>"

curl -X POST https://oricli.thynaptic.com/v1/metacog/scan \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

### Chronos — Temporal Grounding

Temporal memory decay and snapshot management.

```bash
curl https://oricli.thynaptic.com/v1/chronos/entries  -H "Authorization: Bearer glm.<prefix>.<secret>"
curl https://oricli.thynaptic.com/v1/chronos/snapshot -H "Authorization: Bearer glm.<prefix>.<secret>"
curl https://oricli.thynaptic.com/v1/chronos/changes  -H "Authorization: Bearer glm.<prefix>.<secret>"

# Trigger memory decay scan
curl -X POST https://oricli.thynaptic.com/v1/chronos/decay-scan \
  -H "Authorization: Bearer glm.<prefix>.<secret>"

# Force snapshot
curl -X POST https://oricli.thynaptic.com/v1/chronos/snapshot \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

### Science — Hypothesis Testing

```bash
curl https://oricli.thynaptic.com/v1/science/hypotheses -H "Authorization: Bearer glm.<prefix>.<secret>"

curl -X POST https://oricli.thynaptic.com/v1/science/test \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"hypothesis": "Increasing context length improves reasoning accuracy", "method": "ab_test"}'
# Returns: {"hypothesis_id": "hyp_abc"}

curl https://oricli.thynaptic.com/v1/science/hypotheses/hyp_abc \
  -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

### Therapy

Full CBT/REBT/DBT cognitive toolkit applied to Ori's own reasoning stack.

```bash
# Detect cognitive distortion in text
curl -X POST https://oricli.thynaptic.com/v1/therapy/detect \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"text": "I always fail at this kind of task"}'

# REBT B-pass disputation
curl -X POST https://oricli.thynaptic.com/v1/therapy/abc \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"activating_event": "...", "belief": "...", "consequence": "..."}'

# Sycophancy detection pass
curl -X POST https://oricli.thynaptic.com/v1/therapy/fast \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"response": "<draft assistant response>"}'

# Invoke STOP skill (interrupt rumination)
curl -X POST https://oricli.thynaptic.com/v1/therapy/stop \
  -H "Authorization: Bearer glm.<prefix>.<secret>"

# Formulation
curl https://oricli.thynaptic.com/v1/therapy/formulation -H "Authorization: Bearer glm.<prefix>.<secret>"
curl -X POST https://oricli.thynaptic.com/v1/therapy/formulation/refresh -H "Authorization: Bearer glm.<prefix>.<secret>"

# Mastery & helplessness
curl https://oricli.thynaptic.com/v1/therapy/mastery -H "Authorization: Bearer glm.<prefix>.<secret>"

curl -X POST https://oricli.thynaptic.com/v1/therapy/helplessness/check \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -d '{"context": "last 10 interactions"}'

curl https://oricli.thynaptic.com/v1/therapy/helplessness/stats \
  -H "Authorization: Bearer glm.<prefix>.<secret>"

# Stats & event log
curl https://oricli.thynaptic.com/v1/therapy/stats  -H "Authorization: Bearer glm.<prefix>.<secret>"
curl https://oricli.thynaptic.com/v1/therapy/events -H "Authorization: Bearer glm.<prefix>.<secret>"
```

---

### Compute (public)

```bash
curl https://oricli.thynaptic.com/v1/compute/bids/stats
curl https://oricli.thynaptic.com/v1/compute/governor
```

---

### Cognition (public telemetry)

All cognition endpoints are public (no auth). The pattern is:

- `GET /v1/cognition/<module>/stats` — current stats snapshot
- `POST /v1/cognition/<module>/<action>` — trigger a measurement or classification

Modules: `process`, `load`, `rumination`, `mindset`, `hope`, `defeat`, `conformity`, `ideocapture`, `coalition`, `statusbias`, `arousal`, `interference`, `mct`, `mbt`, `schema`, `ipsrt`, `ilm`, `iut`, `up`, `cbasp`, `mbct`, `phaseoriented`, `pseudoidentity`, `thoughtreform`, `apathy`, `logotherapy`, `stoic`, `socratic`, `narrative`, `polyvagal`, `dmn`, `interoception`

```bash
curl https://oricli.thynaptic.com/v1/cognition/mindset/stats
curl https://oricli.thynaptic.com/v1/cognition/rumination/stats
curl -X POST https://oricli.thynaptic.com/v1/cognition/hope/activate \
  -H "Content-Type: application/json" \
  -d '{"intensity": 0.8}'
```

---

## Error Codes

| HTTP | Meaning | Action |
|------|---------|--------|
| 400 | Bad request / malformed JSON | Fix request body |
| 401 | Missing or invalid Bearer token | Check `glm.*.*` token format |
| 403 | Insufficient permissions (admin endpoint) | Requires elevated token |
| 404 | Resource not found | Check ID |
| 429 | Rate limited | Back off with exponential retry |
| 500 | Internal server error | Retry; report to Thynaptic if persistent |

**Error body:**
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

## Tool Use (Function Calling)

Pass tools in the standard OpenAI format:

```json
{
  "model": "ori",
  "messages": [{"role": "user", "content": "What's the weather in London?"}],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string", "description": "City name"}
          },
          "required": ["location"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

When the model calls a tool, `finish_reason` is `"tool_calls"` and `message.tool_calls` contains the call array. Submit results back with `role: "tool"` messages.

---

## Streaming (SSE)

Set `"stream": true` in the chat request body. The response is a standard OpenAI SSE stream:

```
data: {"id":"chatcmpl-x","object":"chat.completion.chunk","choices":[{"delta":{"content":"Hello"},"index":0}]}

data: {"id":"chatcmpl-x","object":"chat.completion.chunk","choices":[{"delta":{"content":" world"},"index":0}]}

data: [DONE]
```

Parse each `data:` line as JSON. Terminate on `data: [DONE]`.

```python
import openai
client = openai.OpenAI(base_url="https://oricli.thynaptic.com/v1", api_key="glm.<prefix>.<secret>")
for chunk in client.chat.completions.create(model="ori", messages=[...], stream=True):
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

---

## WebSocket

Connect to `wss://oricli.thynaptic.com/v1/ws` (no auth required). Receive JSON frames:

```json
{"type": "resonance_sync", "data": {"eri": 0.87, "ers": 0.72, "key": "D minor"}}
{"type": "sensory_sync",   "data": {"hex": "#3A1C71", "opacity": 0.9, "pulse": 1.2}}
{"type": "health_sync",    "data": {"cpu": 12.4, "ram": 68.1, "cognitive_health": "nominal"}}
{"type": "audio_sync",     "data": {"wav_b64": "UklGRi..."}}
{"type": "curiosity_sync", "data": {"target": "panpsychism", "priority": 0.91}}
{"type": "reform_proposal","data": {"diff": "...", "auto_deploy": false}}
{"type": "reform_rollback", "data": {"reason": "test_failure", "reverted_to": "abc123"}}
```

| Event | Description |
|-------|-------------|
| `resonance_sync` | Real-time ERI, ERS, musical key |
| `sensory_sync` | Hex colours, opacities, pulse rates for UI |
| `health_sync` | CPU/RAM substrate + cognitive health |
| `audio_sync` | Base64-encoded WAV (affective voice synthesis) |
| `curiosity_sync` | Live epistemic foraging targets |
| `reform_proposal` | Auto-deploy candidate or propose-only refactor |
| `reform_rollback` | Binary rollback after failed auto-deploy |
