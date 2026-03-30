# Changelog

All notable changes to **ORI Studio / ORI Studio** are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versions track `VERSION` file. Commits listed for traceability.

---

## [Unreleased]

### Added
- **`oricli-bench` bypass model** — Model name `oricli-bench` (or header `X-Benchmark-Mode: true`) skips `ProcessInference` entirely: no sovereign pipeline, no mutex contention, no multi-LLM reasoning calls. Direct `DirectOllama()` call. Latency drops from 60–120s → **< 1s** when Ollama is free. (`66cbeec`, `d205b34`)
- **`GenerationService.DirectOllama()`** — New public method that bypasses all vLLM/RunPod routing and calls `ollamaChatStream` directly. Eliminates the 15s `PrimaryMgr` context-cancel wait that blocked bench/studio paths when a RunPod pod was active. (`d205b34`)
- **`stream:false` non-streaming JSON path** — `handleChatCompletions` now gates all SSE writes behind `useSSE := req.Stream`. Non-streaming clients (LiveBench, Python OpenAI SDK) receive proper `chat.completion` JSON instead of hanging. (`66cbeec`)
- **LiveBench integration** — ORI scores against LiveBench via `gen_api_answer.py --model oricli-bench`. ARC-AGI baseline established (6%, on par with GPT-4). First full LiveBench run (682 questions) complete — scored **19.7% overall**: instruction_following 42.0, data_analysis 23.5, math 13.7, reasoning 12.5, language 6.8. Competitive for a 3B local sovereign model.
- **Rule 11 (Persona)** — ORI never fabricates infra/routing status. Anchored in `instructions.go`. (`7e41253`)
- **Rule 10 (Persona)** — Removed performative emotion/sycophancy from ORI response patterns. (`e0079d5`)
- **Agent Vibe Studio** — Natural-language agent creation (phases 1–3), enabling fast agent scaffolding from plain-English specs. (`6993820`)
- **Canvas share links** — Create public, permanent `/share/:id` links backed by PocketBase `canvas_shares`. (`8ac2819`)
- **Canvas "Open HTML in new tab"** — One-click open for HTML artifacts from the canvas toolbar. (`5e91cc2`)
- **RunPod vLLM primary inference** — Optional GPU-first routing for all tiers when `RUNPOD_PRIMARY=true`. (`68c9865`)
- **Vision vLLM pod upgrade** — RunPod vision pod now uses Qwen2‑VL‑2B via vLLM; supports data-URI images and MIME detection. (`420bfd2`, `dd32627`)
- **Pod spin-up callouts** — Personality callouts during RunPod warmup for better UX feedback. (`4846d4a`)
- **Escalation + success callout tones** — Clearer UI tone shifts during high-stakes and completion states. (`3276402`)

### Fixed
- **`OLLAMA_NUM_THREADS=24 → 6`** — VPS has 8 vCPUs, not 32. Over-subscription caused 60–90s inference and total Ollama serialization under parallel load. (`d205b34`)
- **`/ori/ai-assist` ERR_HTTP2_PROTOCOL_ERROR** — Root cause was Ollama thread over-subscription + 15s vLLM context-cancel wait in the bench path. Fixed by `DirectOllama()` + thread count fix. (`d205b34`)
- **Complexity router false positives** — Pattern matching now scoped to last user message only, not full conversation history. (`1f59047`)
- **Share URL domain** — Share links now use `oristudio.thynaptic.com`. (`26188a0`)
- **Canvas iframe flash** — Eliminated flicker on live render updates. (`b1c2ba2`)
- **Pod state persistence** — RunPod pod state now survives service restarts. (`fe206c5`)

---
## [2.1.0] — 2026-03-24

### Added
- **ORI Studio AI error-awareness** — Vibe Mode AI now recognizes compiler diagnostics (`E[xxx]`/`W[xxx]`). Auto-detects fix intent via regex; shows `⚡ Fix N errors/warnings` quick-action chip when diagnostics exist. All AI modes now receive diagnostics as context. (`f6da9cc`)
- **`GET /v1/modules` endpoint** — Go backbone now exposes live `AgentSkill` objects from `SkillManager`. Returns 18 real skills. Flask `/modules` proxies to this endpoint. (`ed62d22`)
- **Improved Ollama error reporting** — `generation.go` now reads and surfaces Ollama error body on 4xx instead of silently dropping it. (`e0c316b`)
- **ERI live UI theming** — ERI swarm resonance state dynamically adjusts UI shade/tone in real time. (`b45f727`)

### Fixed
- **Canvas 400 error** — `/models` endpoint now filters embedding-only models (`all-minilm`, `nomic-embed-text`, `mxbai-embed-large`, etc.) from the chat model list. Backbone default (`qwen3:1.7b` via `OLLAMA_MODEL`) is sorted first so the UI picks a valid chat model on load. (`e0c316b`)
- **Editor overlay vertical offset** — ORI Studio syntax-highlight `<pre>` overlay was rendering ~3 lines below cursor. Fixed by replacing `<pre>` with `<div>`, setting `overflow: scroll` with CSS-hidden scrollbar (`scrollbar-width: none` + `::-webkit-scrollbar { display: none }`). (`c65c1f3`)
- **`/modules` 502** — Previously proxied to dead Python API on `:8081`. Now proxies to Go backbone `/v1/modules`. (`ed62d22`, `ea5b9b1`)
- **WebSocket 502** — Caddy `/v1/ws` block was missing `flush_interval -1`, preventing WS upgrade handshake. (`ea5b9b1`)
- **Dead `PYTHON_API_BASE` removed** — `/models` and `/health` were still proxying to the dead Python service on `:8081`. Rewired: `/models` pulls from Ollama `/api/tags`; `/health` checks backbone + Ollama. (`c06469e`)

### Changed
- **`/models`** — Now returns only chat-capable models from Ollama (embedding models excluded). Pattern filter: `embed`, `minilm`, `nomic`, `mxbai`, `bge-`, `e5-`, `gte-`.
- **`/health`** — Now reports `{ backbone: bool, ollama: bool }` against real services.
- **AI system prompt** — Updated branding from "ORI Studio" → "ORI Studio".
- **Flask proxy** — `PYTHON_API_BASE` fully removed; replaced with `OLLAMA_BASE` (`localhost:11434`).

---

## [2.0.0] — 2026-03 (approx)

### Added
- **ORI Studio IDE** — Full in-browser DSL IDE with syntax highlighting, compiler-style error output, autocomplete dropdown, and AI Vibe Coding panel. (`0dc0463`, `ff23103`, `381cd6f`)
- **ORI syntax docs** — `docs/ORI_SYNTAX.md` covering full `.ori` DSL spec.
- **Workflow template variables** — Built-in and user-defined run-time params. (`6195770`)
- **Workflow project folders** — Folder grouping with chain graph + Run Project. (`3408458`)
- **Step presets** — 8 ready-made output templates. (`a21318d`)
- **Stop / pause / resume workflows** — State persists across refresh. (`27ef1e3`)
- **Workflow branching + canvas** — Visual connections, branching logic. (`030`)
- **RAG store + doc ingest** — Document ingestion pipeline. (`029`)
- **OAuth2** — Workflow chaining + auto-index scheduler. (`028`)
- **MCP connections** — Agent switcher, Tasks pane, MCP backend. (`004`)
- **Research page** — Canvas fixes. (`003`)

### Changed
- **Rebrand: ORI Studio → ORI Studio** — UI, docs, service names, system prompts. (`0db0469`, `07fd93c`)
- **ORI crimson color system** — New design language replacing electric sci-fi palette.

### Fixed
- **Workflow cancel/pause** no longer reverts to `'running'`. (`2ea8b5e`)
- **Todoist API** — Migrated from v2 (`/rest/v2/tasks` — 410 Gone) to v1. (`5aeaab3`, `2f6d1b8`)

---

## [1.x] — Pre-2026

Initial ORI Studio consumer UI, Canvas, Agent Creators, deployment on `sovereignclaw.thynaptic.com` → migrated to `oristudio.thynaptic.com`. See earlier session checkpoints for history.

---

*Maintained by the ORI Studio team. Update this file with every doc-touching commit.*
