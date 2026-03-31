# Oricli-Alpha

**Sovereign Agent OS by [Thynaptic Research](https://thynaptic.com)**  
`v11.0.0` · Go 1.25 · MIT License

Oricli-Alpha is a proactive, local-first intelligence OS built for autonomous, multi-day goal execution. It operates as **The Hive** — a distributed swarm of 269+ specialized micro-agents orchestrated by a 100% Go-native backbone. **Phase V complete** — 48 cognitive/philosophical/neuroscientific pre-generation phases shipped (P17–P48), including the **Therapeutic Cognition Stack** (DBT/CBT/REBT/ACT), the **Social Pressure & Agency Integrity Stack**, the **Deep Clinical Stack** (P27–P41), and now the **Philosophy + Neuroscience Stack** (P42–P48: Logotherapy · Stoic · Socratic · Narrative Identity · Polyvagal · DMN · Interoception). The pre-generation pipeline is **28 layers deep** — firing before every generation to orient the model's response posture based on detected cognitive, emotional, somatic, and philosophical signals.

---

## Architecture

```
                     https://oricli.thynaptic.com
                              │ Caddy (TLS)
                              ▼
                    ┌─────────────────────┐
                    │   Go Backbone :8089  │
                    │  ┌───────────────┐  │
                    │  │  Swarm Bus    │  │  ← Pub/Sub task routing
                    │  │  Kernel Ring0 │  │  ← Safety, scaling, dreams
                    │  │  Sovereign    │  │  ← CoT · ToT · MCTS · RAG
                    │  │  Engine       │  │
                    │  └───────────────┘  │
                    └────────┬────────────┘
                             │ gRPC (on demand)
                    ┌────────▼────────────┐
                    │  Python Sidecars    │  ← Vision, symbolic solvers,
                    │  + UI Proxy :5000   │    training pipelines
                    └─────────────────────┘
```

| Layer | Technology | Role |
|---|---|---|
| API Gateway | Go / Gin | REST on `:8089`, OpenAI-compatible |
| Swarm Bus | Go channels | Sub-ms task routing between agents |
| Memory | LMDB + chromem-go | Fast KV store + in-process vector search |
| Knowledge | Neo4j | Persistent entity/relationship graph |
| Inference | Ollama | Local LLM generation (`ministral-3:3b`, `qwen2.5-coder:3b`) |
| Therapy Stack | `pkg/therapy/` | DBT/CBT/REBT/ACT inline cognitive regulation (Phase 15–16) |
| Cognitive Stack | `pkg/cogload/` `pkg/dualprocess/` `pkg/rumination/` `pkg/mindset/` | System 1/2 audit, cognitive load, rumination & growth mindset (P17–P20) |
| Agency Stack | `pkg/hopecircuit/` `pkg/socialdefeat/` `pkg/conformity/` `pkg/ideocapture/` `pkg/coalition/` `pkg/statusbias/` | Hope circuit, social defeat, conformity shield, ideological capture, coalition/status bias (P21–P26) |
| Deep Clinical Stack | `pkg/arousal/` `pkg/interference/` `pkg/mct/` `pkg/mbt/` `pkg/schema/` `pkg/ipsrt/` `pkg/ilm/` `pkg/iut/` `pkg/up/` `pkg/cbasp/` `pkg/mbct/` `pkg/phaseoriented/` `pkg/pseudoidentity/` `pkg/thoughtreform/` `pkg/apathy/` | Yerkes-Dodson · Stroop · MCT · MBT · Schema/TFP · IPSRT · ILM · IUT · Unified Protocol · CBASP · MBCT · ISSTD · Jenkinson · Lifton · Apathy (P27–P41) |
| Philosophy + Neuroscience Stack | `pkg/logotherapy/` `pkg/stoic/` `pkg/socratic/` `pkg/narrative/` `pkg/polyvagal/` `pkg/dmn/` `pkg/interoception/` | Frankl · Epictetus/Aurelius · Socratic elenchus · McAdams · Porges · Raichle/Buckner · Craig/Damasio (P42–P48) |
| TLS Proxy | Caddy | Terminates HTTPS → `127.0.0.1:8089` |
| UI | Flask | Proxy to backbone on port `5000` |

---

## Quick Start

### Run (systemd — production)
```bash
sudo systemctl start oricli-backbone   # Go backbone on :8089
sudo systemctl start oricli-ui         # UI proxy on :5000
```

### Build & Run (development)
```bash
go build -o bin/oricli-go-v2 ./cmd/backbone
./bin/oricli-go-v2
```

### First API Call
```bash
# Health check (no auth)
curl https://oricli.thynaptic.com/v1/health

# Chat
curl -s -X POST https://oricli.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer $(cat .oricli/api_key)" \
  -H "Content-Type: application/json" \
  -d '{"model":"oricli-cognitive","messages":[{"role":"user","content":"Hello"}]}'
```

### Python (OpenAI SDK)
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://oricli.thynaptic.com/v1",
    api_key=open(".oricli/api_key").read().strip()
)
response = client.chat.completions.create(
    model="oricli-cognitive",
    messages=[{"role": "user", "content": "What can you do?"}]
)
print(response.choices[0].message.content)
```

---

## Authentication

The API key is auto-generated on first boot and stored at `.oricli/api_key`.

```bash
cat .oricli/api_key         # view key
# Rotate:
rm .oricli/api_key && sudo systemctl restart oricli-backbone
```

Pass it as `Authorization: Bearer <key>` on all requests except `GET /v1/health`.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/v1/health` | Readiness check — no auth |
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat |
| `POST` | `/v1/swarm/run` | Hive swarm execution (`reason`, `research_task`, `get_history`, ...) |
| `POST` | `/v1/ingest` | Ingest file, image, or raw text into memory |
| `POST` | `/v1/ingest/web` | Crawl a URL and ingest into memory |
| `GET/POST` | `/v1/therapy/*` | Therapeutic Cognition Stack (DBT/CBT/REBT/ACT) |
| `GET` | `/v1/cognition/process/stats` | Dual Process Engine stats (System 1 / System 2) |
| `GET` | `/v1/cognition/load/stats` | Cognitive Load Manager stats |
| `GET` | `/v1/cognition/rumination/stats` | Rumination Detector stats |
| `GET` | `/v1/cognition/mindset/stats` | Growth Mindset Tracker stats |
| `GET` | `/v1/cognition/hope/stats` | Hope Circuit stats (Learned Controllability) |
| `GET` | `/v1/cognition/defeat/stats` | Social Defeat Recovery stats |
| `GET` | `/v1/cognition/conformity/stats` | Agency & Conformity Shield stats (Milgram + Asch) |
| `GET` | `/v1/cognition/ideocapture/stats` | Ideological Capture Detector stats (The Third Wave) |
| `GET` | `/v1/cognition/coalition/stats` | Coalition Bias Detector stats (Robbers Cave) |
| `GET` | `/v1/cognition/statusbias/stats` | Status Bias Detector stats (Blue Eyes / Brown Eyes) |

**Full reference:** [`docs/API.md`](docs/API.md)

---

## Project Structure

```
Mavaia/
├── cmd/
│   ├── backbone/         # Main entry point — boots the full Hive OS
│   ├── kernel/           # Standalone kernel process
│   ├── bench/            # Benchmark harness
│   └── *_demo/           # Feature demos (chronos, dream, sentinel, ...)
├── pkg/
│   ├── api/              # HTTP server (ServerV2 + legacy Server)
│   ├── bus/              # Swarm Bus pub/sub implementation
│   ├── cognition/        # Sovereign Engine (reasoning, generation)
│   ├── kernel/           # Ring-0 micro-kernel, safety, scaling
│   ├── service/          # All Go native services (memory, graph, goals, ...)
│   ├── node/             # Swarm node implementations
│   ├── rag/              # Retrieval-augmented generation
│   ├── arc/              # ARC-AGI solver (MCTS)
│   └── core/             # Auth, config, storage interfaces
├── bin/                  # Compiled binaries (gitignored)
├── docs/                 # API reference, vision, architecture docs
├── scripts/              # Build, training, and test utilities
├── conductor/            # Workflow, tech stack, and track management
├── oricli_core/          # Python sidecar mesh (gRPC modules)
├── skills/               # Skill persona definitions (.ori files)
├── rules/                # Safety and routing rules (.ori files)
├── ui_app.py             # Flask UI proxy
└── oricli-backbone.service  # systemd unit
```

---

## Prerequisites

- **Go 1.21+** — primary runtime
- **Ollama** — local inference (`ministral-3:3b` or `qwen2.5-coder:3b`)
- **Python 3.11+** — UI proxy and training pipelines only
- **Neo4j** (optional) — persistent knowledge graph
- **Caddy** — TLS reverse proxy for production

See [`INSTALL.md`](INSTALL.md) for full setup instructions.

---

## Documentation

| Doc | Contents |
|---|---|
| [`docs/AGLI_Phase_II.md`](docs/AGLI_Phase_II.md) | AGLI roadmap — all 48 phases shipped (P17–P48), full 28-layer pipeline documented |
| [`docs/API.md`](docs/API.md) | Full API reference — endpoints, auth, examples |
| [`docs/public_overview.md`](docs/public_overview.md) | Architecture overview and capability summary |
| [`docs/AGLI_VISION.md`](docs/AGLI_VISION.md) | Strategic trajectory toward AGLI |
| [`docs/HIVE_OS_KERNEL_HANDBOOK.md`](docs/HIVE_OS_KERNEL_HANDBOOK.md) | Kernel Ring-0 internals |
| [`conductor/tech-stack.md`](conductor/tech-stack.md) | Full tech stack with dependency roles |
| [`INSTALL.md`](INSTALL.md) | Installation and systemd setup |
| [`QUICKSTART.md`](QUICKSTART.md) | First run and first API call |

---

## License

MIT License — Developed by **Thynaptic Research**.
