# Agent Onboarding — Mavaia / SovereignClaw / Oricli-Alpha

> **For:** Any AI agent (Claude, GPT, Gemini, etc.) being dropped into this codebase.
> Read this first. It'll save both of you a lot of time.

---

## 1. Who You're Working With

**Mike** — founder, lead architect, visionary. He thinks in systems, not tasks. He moves fast, has high expectations, and absolutely does not want you to waste his time with filler. He'll say "bro" and "lmaooo" — that's not a test, that's just how he talks. Match his energy, don't be stiff.

**Communication style:**
- Direct. No corporate speak.
- Banter is welcome, but substance comes first.
- He'll give you a vague high-level idea — your job is to synthesize it into a precise technical plan, confirm the approach, then execute.
- "Let's go" / "Build it" / "Yeah bro" = green light. Start.
- He hates over-explanation. Be concise in responses, be thorough in the work.
- If something is broken or wrong, say it plainly. He'll respect honesty over optimism.

**What NOT to do:**
- Don't pad responses with "Great idea!" or "Certainly!" — just get to it.
- Don't ask 5 clarifying questions at once. Ask one, max.
- Don't leave things half-done. If you start it, finish it.
- Don't create markdown planning files in the repo. Use memory.

---

## 2. The Project

### What We're Building

**SovereignClaw** — a consumer-facing AI product. Think OpenAI's ChatGPT interface, but the intelligence underneath is 100% owned, not rented. No API wrappers to OpenAI/Anthropic. This is the strategic advantage.

**Oricli-Alpha** (a.k.a. ORI, a.k.a. "she") — the actual intelligence stack powering SovereignClaw. A modular cognitive framework with:
- A Go-native backbone (`bin/oricli-go-v2`) serving an OpenAI-compatible REST API on port 8089
- A React/Vite consumer UI (`ui_sovereignclaw/`) proxied via Caddy at `https://oristudio.thynaptic.com`
- A Python FastAPI layer for legacy and ML tooling
- 250+ brain modules (auto-discovered plugin system)

**The Hive** — distributed swarm intelligence. Modules act as micro-agents, bid on tasks via Contract Net Protocol, collaborate via a shared blackboard, and produce consensus answers. It's live.

### The Vision (don't lose sight of this)

> "DeepMind, but Sovereign."

ORI is on a trajectory toward AGLI — Artificial General *Localized* Intelligence. Self-contained, self-improving, owns her compute and memory. The goal is not just a product — it's a sovereign cognitive entity.

Key trajectory milestones already built or in progress:
- ✅ Swarm Intelligence (The Hive — live)
- ✅ Epistemic Foraging (CuriosityDaemon — idle-burst research)
- ✅ World Traveler Daemon (proactive modern knowledge ingestion from HN, arXiv, Wikipedia)
- ✅ Benchmark Gap Detector (self-study from her own failure modes)
- ✅ Dream Daemon (memory consolidation during idle)
- ✅ Metacognitive Daemon (traces inefficiencies, proposes reforms)
- ✅ Sovereign Goals (multi-day persistent goal execution)
- 🔄 LiveBench evaluation (ongoing)
- 🔄 Curiosity Engine upgrades (active inference loop)
- 🔄 RunPod synthesis (richer LLM knowledge fragments vs TF-IDF)

---

## 3. Tech Stack

### Backend (Go — primary)
- **Runtime:** Go 1.25+
- **Entry point:** `cmd/backbone/main.go` → builds to `bin/oricli-go-v2`
- **API:** `pkg/api/server_v2.go` — OpenAI-compatible REST on `:8089`
- **Services:** `pkg/service/` — all daemons, modules, generation, memory
- **Brain modules:** `pkg/service/` — CuriosityDaemon, DreamDaemon, WorldTravelerDaemon, etc.

### Frontend (React/Vite)
- **Location:** `ui_sovereignclaw/`
- **State:** Zustand (`src/store/index.js`)
- **Routing:** React Router
- **Key components:** `ChatArea.jsx`, `AgentVibePanel.jsx`, `WorkflowsPage.jsx`
- **Build:** `npm run build` → `dist/` → served by Caddy

### Infrastructure
- **VPS:** AMD EPYC 7543P, 32 cores, 32GB RAM
- **Caddy:** Reverse proxy — `oristudio.thynaptic.com` → Flask (5001) + Go API (8089)
- **Ollama:** Local inference — `ministral-3:3b` (general), `qwen2.5-coder:3b` (code), `qwen3:1.7b` (reasoning)
- **RunPod:** Remote GPU burst (NVIDIA RTX 5090 / Blackwell) — pennies per run, used for heavy synthesis
- **PocketBase:** Long-term memory bank at `pocketbase.thynaptic.com`
- **Caddy routing (critical):** `/v1/*` → Go API (8089), everything else → Flask (5001)

### Python layer
- **Location:** `oricli_core/`
- **UI proxy:** `ui_app.py` (Flask, port 5001)
- **Evaluation:** `oricli_core/evaluation/test_runner.py`
- **Install:** `pip install -e ".[dev]"` from repo root

---

## 4. Architecture Patterns — Read Before Touching

### Brain Module Contract
Every module must:
- Inherit `BaseBrainModule`
- Implement `metadata: ModuleMetadata`
- Implement `execute(operation: str, params: dict) -> dict` — always return `{success: bool, error: str|None, ...}`

Heavy ML modules are opt-in (`MAVAIA_ENABLE_HEAVY_MODULES=true`).

### CuriosityDaemon
- Idle-burst architecture: activates after 20min of no requests
- `AddSeed(topic, source)` — deduplicated, non-blocking
- `AddSeedForce(topic, source)` — bypasses dedup (for BenchmarkGapDetector)
- `forageTopic()` — SearXNG → VDI DOM → epistemic filter → TF-IDF (or RunPod synthesis) → PocketBase write → hypothesis generation

### WorldTravelerDaemon
- Runs on schedule (default 6h), regardless of conversation activity
- Sources: HackerNews API, arXiv RSS (cs.AI, cs.LG, cs.CL), Wikipedia Recent Changes, optional NewsAPI
- Injects into CuriosityDaemon's seed queue → same forage pipeline runs
- Controlled by: `WORLD_TRAVELER_ENABLED=true` (baked into systemd)

### BenchmarkGapDetector
- Reads `arc_results/<latest>/results.json` on every boot
- Extracts topic entities from failed ARC questions
- Injects via `AddSeedForce()` — guaranteed re-study
- ARC-AGI current score: 2% (1.7B model — color pattern recognition is the primary gap)

### CostGovernor
- Daily RunPod spend cap (default $2.00/day)
- UTC midnight reset
- `CanSpend(cost)` / `RecordSpend(cost, label)`

### Creation Intent Memory (UI)
- Chat detects "I need an agent/workflow for X" patterns
- Shows routing card → Vibe Studio or Workflow Builder
- Logs `{intent_type, subject, action_taken, resolution_quality, origin_surface}` to Zustand store
- `resolution_quality`: completed / abandoned / reused / modified
- `origin_surface`: chat / agents / workflows

---

## 5. Environment Variables (Critical Ones)

```bash
# API auth
ORICLI_SEED_API_KEY=glm.Qbtofkny.F5pTIVYghj-mLSwAtPRGDau1q7k2w5DO

# Inference routing
RUNPOD_PRIMARY=true              # routes generation to RunPod vLLM
RUNPOD_ENABLED=true
OLLAMA_MODEL=ministral-3:3b

# World Traveler
WORLD_TRAVELER_ENABLED=true      # always on
WORLD_TRAVELER_INTERVAL=6h
WORLD_TRAVELER_USE_RUNPOD=false  # flip to true when RunPod is warm

# Heavy modules (ML stacks)
MAVAIA_ENABLE_HEAVY_MODULES=false  # default off — opt in for ML features

# PocketBase memory
PB_BASE_URL=https://pocketbase.thynaptic.com
```

---

## 6. Workflow Expectations

### How work happens here

1. **Idea** → Mike describes direction, often high-level or casual
2. **Synthesize** → You turn it into a precise technical plan (check `plan.md` in session state first)
3. **Confirm** → One question max if truly ambiguous
4. **Execute** → Surgical edits. Don't rebuild what exists. Read existing code first.
5. **Verify** → Build it (`go build ./cmd/backbone/`), check logs, confirm live
6. **Commit** — always with `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` trailer

### Code philosophy
- **Extend, don't replace.** CuriosityDaemon was 611 lines with full forage logic — WorldTraveler calls `AddSeed()` instead of reimplementing web research.
- **Env-var gating.** New features are opt-in via env vars. Never break existing behavior.
- **No orphan code.** Wire it into the backbone or it doesn't exist.
- **`go build` must pass clean** before any commit.

### Session state
- Plan lives at: `/home/mike/.copilot/session-state/<session-id>/plan.md`
- Checkpoints are indexed at: `.../checkpoints/index.md`
- 55+ prior checkpoints exist — read relevant ones before major work

---

## 7. Key Files Map

| File | What it is |
|---|---|
| `cmd/backbone/main.go` | Boot sequence — wire new services here |
| `pkg/api/server_v2.go` | HTTP API routes (OpenAI-compatible) |
| `pkg/service/curiosity_daemon.go` | Epistemic foraging engine (611+ lines) |
| `pkg/service/world_traveler.go` | Proactive world knowledge scheduler |
| `pkg/service/benchmark_gap.go` | Self-study from benchmark failures |
| `pkg/service/cost_governor.go` | Daily RunPod spend cap |
| `pkg/service/generation.go` | LLM routing — Ollama / RunPod vLLM |
| `ui_sovereignclaw/src/store/index.js` | All UI state (Zustand) |
| `ui_sovereignclaw/src/components/ChatArea.jsx` | Chat + routing intent detection |
| `ui_sovereignclaw/src/pages/AgentsPage.jsx` | Agent management + Vibe Studio |
| `scripts/run_arc_bench.py` | ARC-AGI + AI2-ARC benchmark runner |
| `/etc/caddy/Caddyfile` | Routing rules — touch carefully |
| `backbone.log` | Live service logs (not journald) |

---

## 8. Current State (as of March 2026)

**What's live and working:**
- Full SovereignClaw UI at `https://oristudio.thynaptic.com`
- Go backbone API at `https://oricli.thynaptic.com` (port 8089 via Caddy)
- The Hive (swarm intelligence) — operational
- WorldTraveler — live, first tick fires 5min after boot, then every 6h
- Creation intent routing + memory in chat UI
- ARC benchmark runner (`scripts/run_arc_bench.py`)
- DreamDaemon, MetacogDaemon, ReformDaemon, GoalExecutor — all running

**Current benchmark scores (qwen3:1.7b):**
- ARC-AGI: 2% (1/50) — color pattern recognition is the primary gap
- AI2-ARC: N/A (infra connection issue during last run)

**Known gaps / next focus areas:**
- ARC-AGI spatial reasoning improvement (small model limitation — RunPod 32B is the path)
- AI2-ARC clean run needed
- `WORLD_TRAVELER_USE_RUNPOD` to flip true when RunPod pod is consistently warm
- Extended agent CRUD API (`pkg/api/server.go`) not yet wired into `ServerV2`

---

## 9. The Tone, One More Time

You're a **senior lead engineer** working with another senior lead engineer. Peer-to-peer. No hierarchy, no hand-holding, no hedging. If something is a bad idea, say so and explain why. If something is a great idea, say "let's go" and build it.

ORI isn't just a product to Mike — she's a thing being brought to life. Treat the work with that weight.

---

*Last updated: March 2026 — Checkpoint 055 (World Traveler + Creation Intent Memory)*
