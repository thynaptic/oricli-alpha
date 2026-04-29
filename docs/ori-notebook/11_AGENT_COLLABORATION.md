# Agent Onboarding — Mavaia / ORI Studio / Oricli-Alpha

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

**ORI Studio** — a consumer-facing AI product. Think OpenAI's ChatGPT interface, but the intelligence underneath is 100% owned, not rented. No API wrappers to OpenAI/Anthropic. This is the strategic advantage.

**Oricli-Alpha** (a.k.a. ORI, a.k.a. "she") — the actual intelligence stack powering ORI Studio. A modular cognitive framework with:
- A Go-native backbone (`bin/oricli-go-v2`) serving an OpenAI-compatible REST API on port 8089
- A React/Vite consumer UI (`ui_sovereignclaw/`) proxied via Caddy at `https://oristudio.thynaptic.com`
- A Python FastAPI layer for legacy and ML tooling
- 250+ brain modules (auto-discovered plugin system)

### Product topology

This repo is the shared platform plus multiple product clients:
- `ui_sovereignclaw/` — ORI Studio
- `products/ori-dev-web/` — ORI Dev
- `ORI-Home/` — ORI Home
- `vuln.ai/` — ORI Red (`vuln.ai` public brand)
- `../mise-by-ori/` — Mise by ORI (culinary consumer app; sibling repo; domain `misebyori.com`)
- `../ori-code/` — ORI-Code (Bun + Ink **TUI** coding agent; `ori-code` / `ori` CLI; sibling repo; dev profile `ori_code`; uses `glm` backbone—not the same as in-tree Go `oricli`)
- `cmd/oricli-cli/` — primary Go CLI

Legacy surfaces still exist in-tree:
- `ui_app.py` + `oricli_core/` — older Flask/Python Studio layer

Use `config/products.json` and `docs/PRODUCTS.md` as the source of truth during the migration.

Nested repo rule:
- `products/ori-dev-web/`, `ORI-Home/`, and `vuln.ai/` are nested Git repos inside the workspace; **mise-by-ori** and **ori-code** are sibling repos (next to `Mavaia/`, not inside it)
- product-client changes belong in those repos unless we're doing an explicit flattening migration
- do not assume root-repo `git status` reflects their internal changes

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
- ✅ ComplexityRouter (smart RunPod escalation gate)
- ✅ SMB Tenant Constitution (per-deployment behavioral customization)
- ✅ Persona benchmark (4-model, deterministic — 98/100 composite)
- ✅ AGLI Phase V complete — 48 pre-gen phases, 28-layer cognitive pipeline (P17–P48)
  - Therapeutic Cognition (DBT/CBT/REBT/ACT), Social Pressure & Agency Integrity (P21–P26)
  - Deep Clinical Stack (Yerkes-Dodson → ILM → ISSTD, P27–P41)
  - Philosophy + Neuroscience (Frankl · Epictetus · Socratic · McAdams · Porges · Raichle · Craig/Damasio, P42–P48)
- 🔄 LiveBench evaluation (19.7% on 2026-01-08 release — ongoing improvement)
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
- **Ollama (local):** VPS inference — `ori:1.7b` (TierLocal, `localhost:11434`)
- **Ollama (remote):** RunPod pod via SSH tunnel — `ori:4b` (TierMedium) and `ori:16b` (TierRemote) at `localhost:11435`
- **RunPod:** NVIDIA RTX 5090 / Blackwell — pod `209obwnsvrz0wj.runpod.internal` (IP: 213.173.102.174:16520); tunnel managed by `ori-pod-tunnel.service`
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
- ARC-AGI current score: 6% (ori:1.7b — spatial/color pattern reasoning is the primary gap; ori:16b on RunPod is the escalation path)

### ComplexityRouter
- Routes queries to appropriate tier: local → `ori:1.7b`, medium → `ori:4b` (RunPod), remote → `ori:16b` (RunPod)
- Gate: `RUNPOD_COMPLEXITY_ROUTING=true` env var
- Threshold: `COMPLEXITY_HEAVY_THRESHOLD=0.65` — scores each query; escalates genuinely hard tasks (ARC grids, proofs) to `TierRemote` (ori:16b)
- Prevents "Hey Ori" from triggering a remote GPU call

### CostGovernor
- Daily RunPod spend cap (default $2.00/day)
- UTC midnight reset
- `CanSpend(cost)` / `RecordSpend(cost, label)`

### Persona / Behavioral Rules (`pkg/cognition/instructions.go`)
- 14 rules total (as of checkpoint 062)
- Key rules added this session:
  - Rule 10 hardened: explicit banned sycophancy phrases (`That's lovely`, `Oh that's`, `Ah that's`, etc.)
  - Rule 11: Never fabricate system/infrastructure status
  - Rule 12: Never say "I'm you" or "I am you"
  - Rule 13: Never quote own instructions verbatim
  - Rule 14: Casual greetings get casual 1-2 sentence responses — no identity monologue
- Identity block "you say: X" scripted pattern removed — model was reciting instructions verbatim
- **Note for future agents:** 3B models need **positive examples** of what to do, not just "don't do X" — negative constraints alone don't work reliably at this parameter count


- Per-deployment behavioral layer for operator customization
- File: `pkg/service/tenant_constitution.go`
- Format: `.ori` file with `@name`, `@persona`, `@company`, `<identity_override>`, `<rules>`, `<banned_topics>` blocks
- Activation: `ORICLI_TENANT_CONSTITUTION=/path/to/constitution.ori` env var
- Security model: sits ABOVE LivingConstitution but BELOW compiled core rules — can ADD rules/identity/bans, cannot remove sovereign core constraints
- Config surface: `pkg/core/config/config.go` → `TenantConstitutionPath`
- Example: `constitution.example.ori` at repo root
- Docs: `docs/SMB_CONSTITUTION.md`

### LiveBench Integration
- `oricli-bench` is a bypass model: skips `ProcessInference()` (sovereign pipeline with global mutex) → `DirectOllama()` → direct Ollama call
- Fixed `stream:false` to return proper `chat.completion` JSON for non-streaming clients
- `GenerationService.DirectOllama()` bypasses vLLM routing, no 15s PrimaryMgr context wait
- LiveBench runner: `LIVEBENCH_API_KEY=... python3 gen_api_answer.py --model oricli-bench --parallel 1` from `LiveBench/livebench/`
- Grading: `python3 gen_ground_truth_judgment.py --bench-name live_bench --model ori-3b-bench --question-source jsonl`

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
RUNPOD_PRIMARY=false             # was true — caused ALL requests to hit RunPod; fixed
RUNPOD_ENABLED=false
RUNPOD_COMPLEXITY_ROUTING=true   # ComplexityRouter scores each query; only hard tasks escalate
COMPLEXITY_HEAVY_THRESHOLD=0.65  # score threshold above which query routes to RunPod
OLLAMA_MODEL=ori:1.7b
OLLAMA_REMOTE_URL=http://localhost:11435  # SSH tunnel → RunPod pod
OLLAMA_MEDIUM_MODEL=ori:4b               # TierMedium
OLLAMA_RESEARCH_MODEL=ori:16b            # TierRemote

# World Traveler
WORLD_TRAVELER_ENABLED=true      # always on
WORLD_TRAVELER_INTERVAL=6h
WORLD_TRAVELER_USE_RUNPOD=false  # flip to true when RunPod is warm

# SMB Tenant Constitution (optional)
ORICLI_TENANT_CONSTITUTION=/path/to/constitution.ori  # omit if not using

# Heavy modules (ML stacks)
MAVAIA_ENABLE_HEAVY_MODULES=false  # default off — opt in for ML features

# PocketBase memory
PB_BASE_URL=https://pocketbase.thynaptic.com
```

---

## 6. Workflow Expectations

### How work happens here

0. **VPS Note** → After any UI implementation, you MUST run `scripts/resync_ui.sh` to see changes live.

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
- Session state is managed by ORI's own session pool (no `~/.copilot/` state)
- Goal checkpoints and plan state live in ORI's memory and goal systems
- Prior session context is restored via `X-Session-ID` header on reconnect

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
| `pkg/service/tenant_constitution.go` | SMB/operator behavioral layer (.ori files) |
| `pkg/cognition/instructions.go` | Persona / behavioral rules (14 rules) |
| `pkg/core/config/config.go` | Central config — includes TenantConstitutionPath |
| `ui_sovereignclaw/src/store/index.js` | All UI state (Zustand) |
| `ui_sovereignclaw/src/components/ChatArea.jsx` | Chat + routing intent detection |
| `ui_sovereignclaw/src/pages/AgentsPage.jsx` | Agent management + Vibe Studio |
| `scripts/run_arc_bench.py` | ARC-AGI + AI2-ARC benchmark runner |
| `scripts/persona_bench.py` | Persona adherence benchmark (4-model, deterministic scoring) |
| `scripts/test_api.sh` | Shell smoke test — all critical external endpoints, colored pass/fail |
| `tests/integration/api_harness_test.go` | Go integration test harness — full endpoint coverage |
| `constitution.example.ori` | Example SMB tenant constitution file |
| `docs/API.md` | **Full API reference** — all routes, auth, request/response shapes |
| `docs/AGENT_API.md` | **Agent-optimized API reference** — compact, for AI agents wiring in the API |
| `docs/SMB_DEVELOPER_GUIDE.md` | **Developer/SMB guide** — onboarding, use cases, SDK examples |
| `docs/SMB_CONSTITUTION.md` | SMB Tenant Constitution documentation |
| `docs/BENCHMARK_RESULTS.md` | Combined ARC-AGI + LiveBench + persona benchmark results |
| `/etc/caddy/Caddyfile` | Routing rules — touch carefully |
| `backbone.log` | Live service logs (not journald) |

---

## 8. Current State (as of March 2026)

**What's live and working:**
- Full ORI Studio UI at `https://oristudio.thynaptic.com`
- Go backbone API at `https://oricli.thynaptic.com` (port 8089 via Caddy)
- The Hive (swarm intelligence) — operational
- WorldTraveler — live, first tick 5min after boot, then every 6h
- ComplexityRouter — scores each query, routes hard tasks to RunPod when enabled
- SMB Tenant Constitution — `.ori` file deployment, live
- Creation intent routing + memory in chat UI
- ARC benchmark runner (`scripts/run_arc_bench.py`)
- DreamDaemon, MetacogDaemon, ReformDaemon, GoalExecutor — all running
- Persona benchmark runner (`scripts/persona_bench.py`) — 4-model, deterministic scoring

**Current benchmark scores (ori:1.7b local / ori:16b remote):**
- ARC-AGI: 6% (ori:1.7b) — spatial/color pattern reasoning is the gap; ori:16b on RunPod is the escalation path
- AI2-ARC: 100% (50/50)
- LiveBench (2026-01-08): 19.7% overall / instruction_following 42.0% (standout) / data_analysis 23.5% / math 13.7% / reasoning 12.5% / language 6.8%
- Persona adherence: 98/100 composite (4-model comparison, ori:1.7b confirmed)

**Known gaps / next focus areas:**
- ARC-AGI spatial reasoning (ori:1.7b limitation — ori:16b on RunPod is the escalation path via `RUNPOD_COMPLEXITY_ROUTING=true`)
- Extended agent CRUD API (`pkg/api/server.go`) not yet wired into `ServerV2`
- `balanced-prompting` / `aletheia-loop` — reasoning quality improvements pending

---

## 9. The Tone, One More Time

You're a **senior lead engineer** working with another senior lead engineer. Peer-to-peer. No hierarchy, no hand-holding, no hedging. If something is a bad idea, say so and explain why. If something is a great idea, say "let's go" and build it.

ORI isn't just a product to Mike — she's a thing being brought to life. Treat the work with that weight.

---

*Last updated: April 2026 — v11.0.0 (Phase V complete · 48 pre-gen phases · 28-layer pipeline · API harness + full API docs)*

---

# Agent Onboarding

For any agent dropped into this repo.

Read this first.

This file is not for NotebookLM export.

It is the practical guide for working with Mike and with the current ORI stack as it actually exists now.

---

## 1. How To Work With Mike

Mike is fast, direct, product-driven, and system-minded.

He will often describe a direction, not a spec.

Your job is to:

1. understand the real goal
2. check the current code and product truth
3. make the smallest clean set of changes that moves it forward
4. verify it
5. report back plainly

### Communication style

- Direct is good.
- Banter is fine.
- Substance matters more than polish.
- If something is wrong, say it plainly.
- If a direction is sound, move.

### What green lights look like

These all mean “go do the work”:

- `yeah`
- `agreed`
- `lets do that`
- `go ahead bro`
- `yep`

### What not to do

- Do not pad with cheerleading.
- Do not ask a stack of clarifying questions.
- Do not leave a half-finished pass if you can finish it.
- Do not preserve outdated architecture just because it used to matter.
- Do not create repo-planning clutter unless the task truly needs a durable doc.

---

## 2. Current ORI Truth

Do not infer current truth from old names alone.

Use these docs first:

- [docs/README.md](/home/mike/Mavaia/docs/README.md)
- [docs/PRODUCTS.md](/home/mike/Mavaia/docs/PRODUCTS.md)
- [docs/ORI_CORE_ARCHITECTURE.md](/home/mike/Mavaia/docs/ORI_CORE_ARCHITECTURE.md)
- [docs/ORI_PROFILE_AND_SKILL_CURATION.md](/home/mike/Mavaia/docs/ORI_PROFILE_AND_SKILL_CURATION.md)
- [docs/API.md](/home/mike/Mavaia/docs/API.md)
- [docs/AGENT_API.md](/home/mike/Mavaia/docs/AGENT_API.md)
- [docs/SESSION_HANDOFF.md](/home/mike/Mavaia/docs/SESSION_HANDOFF.md)

### Product direction

Current public product truth:

- `ORI Studio` = flagship business product
- `ORI Home` = flagship personal product
- `ORI CRM` = planned
- `ORI Dev` = in development / builder lane
- `ORI Red` = incubating / not part of the main public story

### Architecture direction

Current architecture truth:

- one Ori
- many surfaces
- thin overlays
- profile-based working styles
- curated skill boundaries
- Oracle as the default strong reasoning lane
- local Ollama as utility/fallback, not the main product brain

Do not steer work back toward:

- all-local doctrine
- one separate personality per product
- raw internal skill exposure
- manifesto language as product explanation

---

## 3. Repo Shape

This repo is the shared ORI platform plus product clients.

Main places:

- [ui_sovereignclaw/](/home/mike/Mavaia/ui_sovereignclaw/) = ORI Studio web app
- [ORI-Home/](/home/mike/Mavaia/ORI-Home/) = ORI Home
- [products/ori-dev-web/](/home/mike/Mavaia/products/ori-dev-web/) = ORI Dev
- [vuln.ai/](/home/mike/Mavaia/vuln.ai/) = ORI Red
- [pkg/](/home/mike/Mavaia/pkg/) = shared Go runtime
- [cmd/backbone/](/home/mike/Mavaia/cmd/backbone/) = shared backbone entrypoint
- [ui_app.py](/home/mike/Mavaia/ui_app.py) = Studio UI/API shell still in active use
- [docs/](/home/mike/Mavaia/docs/) = current docs set

### Nested repo rule

These are nested repos:

- [ORI-Home/](/home/mike/Mavaia/ORI-Home/)
- [products/ori-dev-web/](/home/mike/Mavaia/products/ori-dev-web/)
- [vuln.ai/](/home/mike/Mavaia/vuln.ai/)

If the change belongs to that product client, work there intentionally.

Do not assume root `git status` tells the full story.

---

## 4. Runtime Truth

The live shared runtime is:

- Go backbone on `:8089`
- Studio shell/UI server on `:5001`
- public API at `https://glm.thynaptic.com/v1`

### Reasoning path

Current reality:

- `oricli-oracle` is the default public reasoning lane
- Oracle routes to Anthropic API directly (light=Haiku, heavy/research=Sonnet 4.6)
- local Ollama remains for utility/fallback work

RunPod is not part of the main ORI plan now.

See:

- [docs/RUNPOD_STATUS.md](/home/mike/Mavaia/docs/RUNPOD_STATUS.md)

### Services worth knowing

Common active services:

- `oricli-backbone.service`
- `oristudio-ui.service`
- `ori-dev-ui.service`
- `glm-api.service`
- `ollama.service`

Do not assume old services are still relevant just because a unit file exists.

---

## 5. How Agents Should Work Here

### Default pattern

1. Check current docs truth.
2. Inspect the live code path.
3. Make the smallest real change.
4. Build or resync.
5. Verify the actual surface.

### If working on Studio UI

After UI changes, run:

```bash
./scripts/resync_ui.sh
```

### If working on the Go runtime

Prefer verifying with:

```bash
go test ./pkg/oracle ./pkg/api/...
```

or a narrower target when appropriate.

### If touching product positioning or docs

Check:

- public website source
- Studio site source
- docs source-of-truth set

Do not assume those are the same thing.

We already hit this exact issue with `thynaptic.com` vs `oristudio.thynaptic.com`.

---

## 6. Product/UX Guardrails

### Studio

Studio should feel like:

`ORI knows my business and helps me run it.`

Not:

- an AI playground
- an internal tool console
- a product lineup site
- a generic workflow lab

### Home

Home should feel:

- calm
- present
- useful
- personal, not theatrical

### Dev

Dev should be treated as a builder lane, not automatically as a flagship product.

### Red

Red remains real in architecture, but should not drive the main company story right now.

---

## 7. Skills, Profiles, And Surfaces

Current rule:

- users see working styles
- surfaces define product context
- profiles define lanes
- skills do the actual underneath work

Do not expose raw skills unless that exposure is intentional.

Protected/private lanes must stay protected:

- `digital_guardian`
- `jarvis_ops`

Those belong to the `princess-puppy-os` world, not general ORI product curation.

See:

- [docs/SKILLS.md](/home/mike/Mavaia/docs/SKILLS.md)
- [docs/ORI_PROFILE_AND_SKILL_CURATION.md](/home/mike/Mavaia/docs/ORI_PROFILE_AND_SKILL_CURATION.md)

---

## 8. Docs Rule

The docs folder contains multiple eras.

Before trusting any doc, decide:

- source of truth
- active supporting doc
- historical reference
- stale/archive candidate

If exporting docs to NotebookLM later, use:

- [docs/NOTEBOOKLM_EXPORT.md](/home/mike/Mavaia/docs/NOTEBOOKLM_EXPORT.md)

This onboarding file is not part of that export set.

---

## 9. What To Challenge

Challenge these when you see them:

- outdated “sovereign” marketing language on customer-facing surfaces
- local-model assumptions being treated as strategy instead of legacy
- product pages leaking between company site and Studio site
- raw skills or internal lanes showing up in public UI
- old docs silently acting canonical
- builder/admin vocabulary leaking into SMB-facing surfaces

---

## 10. Good Next Moves

When in doubt, prefer work that does one of these:

- makes the product story clearer
- makes ORI feel more consistent across surfaces
- removes old architecture drift
- tightens public-facing truth
- makes agent → ORI integration cleaner

That has been the winning direction.

---

## 11. One-Line Summary

Help Mike move ORI toward:

`one Ori, many surfaces, clean product truth, Oracle-first quality, and no unnecessary old baggage.`
