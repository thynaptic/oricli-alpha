# Oricli-Alpha: Sovereign Agent OS

**By Thynaptic Research — v2.1.0**

---

## Abstract

Oricli-Alpha is a sovereign, local-first Agent OS built for proactive, autonomous intelligence. Unlike reactive prompt-response systems, Oricli-Alpha orchestrates a distributed swarm of 269+ specialized micro-agents (The Hive) to execute complex, multi-day goals without human supervision. The entire production system runs on a 100% Go-native backbone, delivering sub-millisecond internal routing and full utilization of multi-core hardware without Python GIL constraints.

---

## Architecture: The Hybrid Hive

Oricli-Alpha operates as a two-layer system:

```
┌──────────────────────────────────────────────────────┐
│                  Go-Native Backbone                  │
│  ┌─────────────┐  ┌────────────┐  ┌───────────────┐  │
│  │ Swarm Bus   │  │  Kernel    │  │  API Gateway  │  │
│  │ (Pub/Sub)   │  │  (Ring 0)  │  │  (ServerV2)   │  │
│  └──────┬──────┘  └─────┬──────┘  └───────┬───────┘  │
│         │               │                 │           │
│  ┌──────▼───────────────▼─────────────────▼───────┐  │
│  │           Sovereign Engine                      │  │
│  │  MCTS · CoT · ToT · RAG · Memory Bridge        │  │
│  │  Goals · Neo4j · LMDB · Chromem Vector DB      │  │
│  └─────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
                         ▲
                         │ gRPC
┌──────────────────────────────────────────────────────┐
│              Python Sidecar Mesh                     │
│  Vision · Symbolic Solvers · Training Pipelines      │
└──────────────────────────────────────────────────────┘
```

### Go-Native Backbone
The backbone (`bin/oricli-go-v2`) is a single binary that boots the entire Hive:

- **Swarm Bus**: A pub/sub message bus routing tasks between micro-agents at sub-millisecond latency.
- **Micro-Kernel (Ring 0)**: The master arbiter — manages processes, safety spend caps, autonomous scaling, and the Dream Daemon (idle memory consolidation).
- **Sovereign Engine**: Hosts the reasoning suite (CoT, ToT, MCTS), Memory Bridge (LMDB/Chronos), Knowledge Graph (Neo4j), and vector search (chromem-go).
- **API Gateway (ServerV2)**: Gin-based REST server on port `8089`. OpenAI-compatible. Proxied via Caddy to `oricli.thynaptic.com`.

### Python Sidecar Mesh
Specialized Python capabilities (vision transcription, symbolic solvers, LoRA training) run as gRPC services managed by the Go orchestrator. They are invoked on demand — not in the critical response path.

---

## Key Capabilities

| Capability | Implementation |
|---|---|
| **Sovereign Goals** | Multi-day objectives persisted in LMDB, resumed across restarts |
| **Hive Swarm** | 269+ micro-agents bid via Contract Net Protocol to handle queries |
| **RAG Memory** | chromem-go vector store + Neo4j graph for hybrid retrieval |
| **Web Ingestion** | Concurrent Go crawler → chunk → embed → index pipeline |
| **Multi-Modal** | Image ingestion transcribed by Ollama vision model before indexing |
| **Metacognition** | DBT/CBT-inspired sentinel detects and self-corrects cognitive loops |
| **Adversarial Audit** | Red-team pass on all execution plans before they run |
| **Dream Daemon** | Idle-time memory consolidation and novel insight synthesis |
| **OpenAI Compat** | Drop-in `/v1/chat/completions` — works with OpenAI SDK, Continue, OpenWebUI |

---

## Performance

Measured on AMD EPYC 7543P (32 cores, 32GB RAM):

- **Internal routing**: Sub-millisecond (Go channel-based Swarm Bus)
- **API response (simple)**: < 5 seconds (local Ollama + Go reasoning)
- **Idle RAM**: ~60% reduction vs. Python-only stack
- **Concurrency**: 32 cores fully utilized via goroutines — no GIL

---

## Quick Integration

```bash
# Health check
curl https://oricli.thynaptic.com/v1/health

# Chat (OpenAI SDK)
from openai import OpenAI
client = OpenAI(base_url="https://oricli.thynaptic.com/v1", api_key="<key>")
response = client.chat.completions.create(
    model="oricli-cognitive",
    messages=[{"role": "user", "content": "What can you do?"}]
)
```

---

## Further Reading

| Document | Contents |
|---|---|
| [`docs/API.md`](API.md) | Full API reference — all endpoints, auth, examples |
| [`docs/AGLI_VISION.md`](AGLI_VISION.md) | Strategic trajectory toward Artificial General Localized Intelligence |
| [`docs/HIVE_OS_KERNEL_HANDBOOK.md`](HIVE_OS_KERNEL_HANDBOOK.md) | Kernel Ring 0 internals |
| [`INSTALL.md`](../INSTALL.md) | Installation and systemd setup |
| [`conductor/tech-stack.md`](../conductor/tech-stack.md) | Full tech stack details |

---

*Oricli-Alpha is developed by Thynaptic Research. MIT License.*
