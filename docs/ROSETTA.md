# Oricli — Rosetta (1-page map)

> Read this first. Everything else in `/docs` is a deep-dive into one layer of this map.

---

## The Five Layers

```
  ┌─────────────────────────────────────────────────────────────────┐
  │  INFERENCE PIPELINE  (13 steps, request-scoped)                 │
  │  Step 1-2 → decode intent  Step 3 → Safety check               │
  │  Step 4-11 → memory + reasoning + tool use + generation         │
  │  Step 12-13 → CALI critique → revision → RFAL lesson log        │
  └─────────────────────────────────────────────────────────────────┘
             ↓ every request           ↑ revised response
  ┌──────────────────────┐  ┌──────────────────────────────────────┐
  │  KERNEL  (Ring 0-3)  │  │  SELF LAYER  (always-on affect)      │
  │  Ring 0 — Micro-Kernel   │  Subconscious Field — 256-dim vector  │
  │    process lifecycle,│  │    buffer that "colors" all inference │
  │    financial caps,   │  │  Resonance (ERI) — real-time mood    │
  │    Precog rate-limit │  │    derived from Swarm Bus telemetry  │
  │  Ring 1 — Sovereign  │  │  Sweetheart Core — personality &     │
  │    Engine: ERI + DAG │  │    user-energy calibration           │
  │    long-horizon goals│  │  Metacog Sentinel — loop/hallucina-  │
  │  Ring 2 — Substrate  │  │    tion detector; fires "Radical     │
  │    HAL, VDI, MCP,    │  │    Acceptance" to break deadlocks    │
  │    FS Indexer, cron  │  │  Experience Journal — last N tool    │
  │  Ring 3 — Swarm Bus  │  │    results injected next cycle       │
  │    pub/sub nervous   │  └──────────────────────────────────────┘
  │    system + Contract │
  │    Net (bid routing) │  ┌──────────────────────────────────────┐
  │  Gosh Sandbox        │  │  CALI  (Constitution + alignment)    │
  │    isolated Go bash  │  │  Safety Sentinel — pattern injection │
  │    for all agent     │  │    / extraction / distress detect    │
  │    code execution    │  │  Adversarial Auditor — zero-trust    │
  └──────────────────────┘    threat model pre-inference           │
                           │  SCAI — 2-pass runtime enforcer:     │
                           │    Critique → Revision → RFAL log    │
                           │  RFAL — violations → DPO triplets    │
                           │    → alignment_lessons.jsonl         │
                           │  Sovereign Constitution — 5 binding  │
                           │    principles (immutable, in-process)│
                           └──────────────────────────────────────┘
  ┌──────────────────────────────────────────────────────────────────┐
  │  MEMORY  (4-tier, hot → cold)                                    │
  │                                                                  │
  │  Working Graph (chromem-go) ── ns ── ephemeral session nodes     │
  │       ↓ high-confidence nodes promoted                          │
  │  Memory Bridge (LMDB) ─────── μs ── 8 named DBs: semantic,      │
  │    episodic, identity, skill, long_term_state, reflection_log,  │
  │    vector_index, temporal_index                                  │
  │       ↓ retention-scored after session                          │
  │  Knowledge Graph (Neo4j) ──── ms ── entity + MetaEvent nodes,   │
  │    multi-hop reasoning, temporal edges                           │
  │       ↓ cold storage                                            │
  │  Memory Bank (PocketBase) ─── 2ms ─ memories, knowledge_frags,  │
  │    spend_ledger, conversation_summaries  (200 GB, survives boot) │
  │                                                                  │
  │  Provenance tags: user_stated (immortal) > synthetic_l1          │
  │    (Curiosity-sourced, reduced RAG weight) > synthetic_l2+       │
  └──────────────────────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────────────────────────┐
  │  DAEMONS  (background goroutines, Swarm Bus only — never inline) │
  │                                                                  │
  │  JIT Librarian ────── RFAL lessons → LoRA fine-tune (≥5 new)    │
  │  Dream Daemon ──────── idle 1h+ → LMDB consolidation + Neo4j    │
  │  Curiosity Forager ─── gap-score Working Graph → SearXNG → VDI  │
  │                         → PocketBase knowledge_fragments         │
  │  Reform Daemon ─────── trace bottlenecks → Code Constitution     │
  │                         LLM → 4-stage verifier → auto-deploy    │
  │  Metacog Daemon ─────── trace anomaly scan + pre-flight Precog   │
  │  Tool Daemon ──────────  correction events → tool LoRA (≥10)    │
  │  Goal Executor ────────  DAG sovereign goals, 30s poll interval  │
  │  Autonomic Scaling ──── Swarm Bus >500ms → SysAllocGPU (RunPod) │
  └──────────────────────────────────────────────────────────────────┘
```

---

## How the layers wire together

| From | Signal | To | Effect |
|---|---|---|---|
| Inference Step 13 | RFAL lesson | JIT Daemon | LoRA patch queued |
| SCAI Critique | Violation event | RFAL | DPO triplet written to `alignment_lessons.jsonl` |
| Swarm Bus telemetry | Throughput / latency / success | ERI (Self Layer) | Musical-key mood mapping → Sweetheart tone shift |
| Working Graph | Low-context nodes | Curiosity Daemon | Web forage triggered |
| Curiosity Daemon | `knowledge_fragments` | PocketBase → Memory Bridge | Promoted to warm memory with `synthetic_l1` tag |
| Dream Daemon | Gosh traces (last 24h) | LMDB → Neo4j | Session consolidated, ephemeral nodes pruned |
| Metacog Sentinel | Repetition / entropy scores | Subconscious Field | "Radical Acceptance" negative-weight reset |
| Reform Daemon | Code bottleneck proposal | Kernel Ring-2 cron | Auto-deploy if 4-stage verifier passes |
| Goal Executor | DAG next action | ActionRouter → inference | Sovereign step executed |
| Autonomic Scaling | `SysAllocGPU` syscall | Kernel Ring-0 → HAL | Ghost Cluster (RunPod GPU) provisioned |

---

## DEFCON quick-ref

| DEFCON | State | Hard limits |
|---|---|---|
| 5 | Normal | Full swarm + auto-scaling |
| 4 | Restricted | No auto-scale; ≤ 10 PIDs |
| 3 | Shielded | No new GPU; ≤ 5 PIDs |
| 2 | Quarantine | All agents suspended |
| 1 | Panic | Kernel locked, global shutdown |

---

## Sovereign Stack (supporting services)

| Service | Port | Used by |
|---|---|---|
| SearXNG | `127.0.0.1:8080` | Curiosity Daemon |
| Browserless | `127.0.0.1:3000` | VDI Manager (visual forage) |
| MinIO | `127.0.0.1:9000` | JIT / Dream → RunPod artefacts |
| Neo4j | `0.0.0.0:7474/7687` | Knowledge Graph reads + MetaEvent writes |
| Prometheus / Grafana | `9091 / 9093` | Swarm Bus + backbone metrics |

---

## One-sentence layer summary

| Layer | One sentence |
|---|---|
| **Kernel** | The OS — runs agents in sandboxes, routes tasks by bid, manages rings of trust and compute. |
| **CALI** | The conscience — every response runs through a live critique-revision loop tied to a hard Constitutional charter. |
| **Memory** | The brain's storage — four tiers from nanosecond in-process graph to cold 200 GB PocketBase, with provenance decay. |
| **Self Layer** | The affect — continuous mood, personality calibration, and loop-detection that shape *how* Oricli thinks, not just *what* it thinks. |
| **Daemons** | The metabolism — background processes that consolidate memory, self-improve via LoRA, forage knowledge, and provision GPU — all without blocking inference. |

---

*Deep-dives: [`HIVE_OS_KERNEL_HANDBOOK.md`](HIVE_OS_KERNEL_HANDBOOK.md) · [`CALI.md`](CALI.md) · [`MEMORY_ARCHITECTURE.md`](MEMORY_ARCHITECTURE.md) · [`SELF_LAYER.md`](SELF_LAYER.md) · [`DAEMONS.md`](DAEMONS.md) · [`SOVEREIGN_STACK.md`](SOVEREIGN_STACK.md)*
