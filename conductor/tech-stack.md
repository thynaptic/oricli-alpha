# Technology Stack: Oricli-Alpha Core

> Last updated: 2026-03-22 — reflects v2.2.0 Go-native architecture.
> **Before introducing a new stack-level dependency, update this file first.**

## Primary Language & Runtime

- **Go (1.25+)**: The primary language for all production services — API gateway, Swarm Bus, reasoning engines, memory, ingestion, and orchestration. Module: `github.com/thynaptic/oricli-go`.
- **Python (3.11+)**: Used for the UI proxy (`ui_app.py`), training pipelines, and optional cognitive sidecars exposed over gRPC.

## Go Core Libraries (`go.mod`)

| Package | Role |
|---|---|
| `github.com/gin-gonic/gin` | HTTP router for the Sovereign API Gateway (ServerV2) |
| `github.com/PowerDNS/lmdb-go` | High-speed persistent key-value store (Memory Bridge / Chronos) |
| `github.com/neo4j/neo4j-go-driver/v5` | Neo4j Knowledge Graph queries |
| `github.com/philippgille/chromem-go` | In-process vector store for semantic search / RAG |
| `github.com/ollama/ollama` | Ollama client for local LLM inference (prose generation) |
| `github.com/traefik/yaegi` | Go interpreter for dynamic gosh sandbox execution |
| `mvdan.cc/sh/v3` | Shell interpreter for script execution inside the Kernel |
| `github.com/google/uuid` | ID generation |
| `github.com/joho/godotenv` | `.env` loading |
| `google.golang.org/grpc` | gRPC transport for Python sidecar communication |
| `google.golang.org/protobuf` | Protobuf serialization |
| `github.com/PuerkitoBio/goquery` | HTML parsing for web ingestion |
| `github.com/quic-go/quic-go` | QUIC transport (future high-speed cluster comms) |

## Inference & Generation

- **Ollama**: Local LLM inference. Primary model: `qwen2.5-coder:3b` (via `oricli-backbone.service`). The Go backbone offloads all prose generation and light reasoning to Ollama, reserving native compute for orchestration and tool-use.
- **RunPod GPU Inference**: On-demand KoboldCpp pods for code and research tiers (`pkg/service/runpod_manager.go`). Model auto-selected from baked catalog (`pkg/connectors/runpod/inference.go` → `TierModels`) based on available GPU VRAM. Only `RUNPOD_ENABLED=true` required — no URL config.
- **RunPod Image Generation**: A1111 Stable Diffusion WebUI pods for image generation (`pkg/service/image_gen_manager.go`). Activated via `RUNPOD_IMAGEGEN_ENABLED=true`. Idle auto-terminates after 10 minutes. API-compatible with `POST /v1/images/generations`.
- **gRPC Sidecars**: Specialized Python cognitive modules (e.g., vision, symbolic solvers) are invoked via gRPC from the Go orchestrator when a capability requires a Python ML library.

## Storage

- **LMDB** (`lmdb-go`): Primary fast key-value store for the Memory Bridge and Chronos temporal index. Path: `/home/mike/Mavaia/.memory/lmdb`.
- **Neo4j**: Persistent graph database for the Knowledge Vault (entity/relationship storage). Accessed via Go driver.
- **chromem-go**: In-process vector store for RAG embeddings — no external vector DB required.
- **PocketBase**: External long-term memory bank on `https://pocketbase.thynaptic.com` (dedicated VPS, 200GB). Cold tier of the four-tier memory stack. Stores conversation memories, curiosity findings, spend ledger, and conversation summaries. Oricli has her own analyst account. Go connector at `pkg/connectors/pocketbase/`. Epistemic hygiene layer: provenance tracking, volatility-aware decay, novelty cap — see `docs/EPISTEMIC_HYGIENE.md`.
- **AWS S3 / RunPod S3**: Persistent storage for model checkpoints, training data archives, and cross-pod coordination state.

## API Gateway & Networking

- **Gin** (`gin-gonic/gin`): Go HTTP framework powering `ServerV2` on port `8089`.
- **Caddy**: TLS termination and reverse proxy. Routes `oricli.thynaptic.com` → `127.0.0.1:8089`. Config: `/etc/caddy/Caddyfile`.
- **Auth**: Argon2id key hashing via `pkg/core/auth`. Key format: `glm.<prefix>.<secret>`.

## Python Sidecar Stack

Used only for the UI proxy and optional cognitive sidecars. Not in the critical path.

- **Flask**: Lightweight UI proxy (`ui_app.py`) forwarding browser traffic to the Go API. Port 5000.
- **PyTorch / Transformers / PEFT**: Used in training pipelines and LoRA adapter management (`scripts/train_*.py`).
- **JAX & Flax**: Specific reasoning architecture experiments.
- **HTTPX / Requests**: Network communication in Python sidecars.
- **Black / Ruff / MyPy**: Python code formatting, linting, and type checking.

## Infrastructure & DevOps

- **systemd**: Service management. Key units: `oricli-backbone.service`, `oricli-ui.service`, `oricli-trainer.service`.
- **RunPod**: GPU-accelerated remote training (NVIDIA RTX 5090 / Blackwell). Async virtual clustering via S3 coordination.
- **Docker**: Containerization for sandboxed execution environments.

## Compute Targets

- **Primary VPS**: AMD EPYC 7543P (32 cores, 32GB RAM). Go backbone fully utilizes all cores via goroutines.
- **Remote GPU (RunPod)**: Training workloads and heavy ML inference offloaded via SSH tunnel / S3 bridge.
