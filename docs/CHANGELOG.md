# Changelog

All notable changes to **ORI Studio / SovereignClaw** are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versions track `VERSION` file. Commits listed for traceability.

---

## [Unreleased]

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
- **AI system prompt** — Updated branding from "SovereignClaw" → "ORI Studio".
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
- **Rebrand: SovereignClaw → ORI Studio** — UI, docs, service names, system prompts. (`0db0469`, `07fd93c`)
- **ORI crimson color system** — New design language replacing electric sci-fi palette.

### Fixed
- **Workflow cancel/pause** no longer reverts to `'running'`. (`2ea8b5e`)
- **Todoist API** — Migrated from v2 (`/rest/v2/tasks` — 410 Gone) to v1. (`5aeaab3`, `2f6d1b8`)

---

## [1.x] — Pre-2026

Initial SovereignClaw consumer UI, Canvas, Agent Creators, deployment on `sovereignclaw.thynaptic.com` → migrated to `oristudio.thynaptic.com`. See earlier session checkpoints for history.

---

*Maintained by the ORI Studio team. Update this file with every doc-touching commit.*
