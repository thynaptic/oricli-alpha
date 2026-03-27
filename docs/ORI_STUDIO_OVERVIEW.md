# ORI Studio — Product Overview

**By Thynaptic Research**  
*For design, branding, and creative AI agents*

---

## What Is ORI Studio?

ORI Studio is the **sovereign developer workspace** built on top of Oricli-Alpha — Thynaptic's local-first Agent OS. It is the primary interface where engineers, researchers, and power users collaborate with the Oricli intelligence layer.

Think of it as an IDE that thinks with you. Not a chat window bolted onto a code editor — a unified environment where AI cognition, automation pipelines, and code generation are first-class citizens of the workspace itself.

ORI Studio lives at **oristudio.thynaptic.com** and is the consumer-facing product layer of the SovereignClaw platform.

---

## The Name

**ORI** is short for Oricli — derived from two mythological roots:

- **Orion** — the Greek hunter, symbol of exploration, discovery, and relentless pursuit
- **Clio** — the Muse of history and knowledge, keeper of truth and record

Together: *a powerful entity that discovers, reasons, and remembers.* The Studio suffix grounds it — this is the workspace where that intelligence is harnessed.

---

## What ORI Studio Does

ORI Studio is organized around five core modes, each accessible from the left navigation rail:

### 1. **Chat** — The Sovereign Conversation Layer
Direct dialogue with Oricli. Not a wrapper around GPT — 100% local, sovereign intelligence running on our own infrastructure. Supports research mode, deep-think, web-grounded answers, and memory-aware conversation. ERI (Emotional Resonance Intelligence) subtly tunes the UI tone and Oricli's persona in real time based on conversational energy.

### 2. **ORI Studio IDE** — Vibe Coding + Workflow Editor
A dual-panel workspace:
- **Left**: Code/workflow editor with ORI Syntax highlighting, inline AI autocomplete, and diagnostics
- **Right**: Chat panel where you describe what you want in plain language — "build me a data pipeline that scrapes X, summarizes it, and emails the digest"

The AI builds, modifies, and explains in context. The editor supports **ORI DSL** (a domain-specific workflow language) and general code. There are three AI modes: *generate*, *explain*, and *fix* (auto-triggered by compiler diagnostics).

### 3. **Canvas** — Artifact Generation
Full-page generative output mode. Long-form code, landing pages, documentation, reports. Canvas renders the output with live streaming and syntax-aware display. Outputs are portable artifacts.

**New:** HTML artifacts can be opened in a new tab, and any canvas artifact can be shared via a permanent public link (`/share/:id`) backed by PocketBase.

### 4. **Research** — Deep Knowledge Mode
Routes queries to the heavyweight reasoning stack (deepseek-coder-v2:16b) for long-horizon tasks. Engages the Hive's web ingestion, RAG memory, and multi-step reasoning. Shows a visible "Researching" card only when deep-mode is active — not on casual queries.

### 5. **Workflows** — Autonomous Pipeline Orchestration
Build, run, and monitor autonomous multi-step pipelines. Workflows are defined in ORI DSL or generated via the IDE. They can chain web searches, agent tasks, code execution, and canvas output in parallel or sequential branches.

---

## Supporting Surfaces

Beyond the five core modes, ORI Studio exposes:

- **Agents** — View, configure, and spawn Hive micro-agents
- **Agent Vibe Studio** — Natural-language agent creation for rapid scaffolding (phases 1–3)
- **Memory Browser** — Inspect Oricli's long-term memory graph (PocketBase + vector store)
- **Goals** — Multi-day sovereign objectives — set once, executed autonomously across sessions
- **Connections** — MCP (Model Context Protocol) integrations and external service bridges
- **Artifacts Canvas** — Library of generated outputs (code, docs, reports)
- **Logs** — Live backbone and daemon event stream

---

## Design Language

ORI Studio runs dark. Always. This is intentional — it's a power tool for focus, not a consumer app.

### Color Palette

| Role | Hex | Notes |
|---|---|---|
| Background | `#080810` | Near-black, slight purple undertone |
| Surface | `#0E0810` | Raised panels |
| Surface 2 | `#150A14` | Modals, drawers |
| Border | `#1E0A18` | Subtle deep-burgundy borders |
| **Accent / Primary** | `#E5004C` | Sovereign crimson — the ORI red |
| Accent Glow | `#FF0055` | Bloom/glow variant of accent |
| Text | `#F0ECE8` | Warm off-white |
| Text Muted | `#8A7880` | Labels, secondary info |
| Success | `#06D6A0` | Teal-green |
| Danger | `#FF4D6D` | Error states |
| Info Blue | `#4D9EFF` | Links, active states |

The accent (`#E5004C`) transitions dynamically based on ERI state — it can pulse, shift warmth, or dim based on conversational energy. This is a live design feature, not static.

### Visual Tone

- **Dense, not cluttered** — high information density without visual noise
- **Glowing edges** — thin 1px borders with faint colored glow on interactive elements
- **Monospace-forward** — code and workflow content is always in a fixed-width font with syntax color
- **Minimal chrome** — the content is the product; UI furniture recedes
- **Sovereign energy** — the product should feel capable, local, and owned — not cloud-soft or enterprise-sanitized

### Typography Direction
- UI labels: clean sans-serif (system or Inter-equivalent)
- Code/workflows: monospace (JetBrains Mono or similar)
- Product name treatment: all-caps **ORI** with the word "Studio" in lighter weight alongside

---

## Positioning

| Dimension | ORI Studio |
|---|---|
| **vs. Cursor/Copilot** | Sovereign — no data leaves your infrastructure. The AI *is* yours. |
| **vs. ChatGPT/Claude** | Not a chat product. A workspace. Memory, goals, pipelines, artifacts. |
| **vs. n8n/Zapier** | Intelligence-first orchestration. Workflows understand intent, not just triggers. |
| **vs. OpenWebUI** | Purpose-built for power users, not generic model switching. |

**One-liner**: *The sovereign workspace for engineers who want AI that works for them — not a cloud it rents from.*

---

## Brand Attributes

These words should guide all visual and copy decisions:

- **Sovereign** — owned, private, no external dependency
- **Precise** — surgical, capable, not chatty
- **Deep** — real reasoning, not autocomplete
- **Local** — runs on your iron, not someone else's
- **Alive** — the UI breathes with the intelligence (ERI theming, pulse animations)

---

## What's Still Being Built

ORI Studio is actively in development. These are live or in-progress:

- ✅ Chat with ERI live theming
- ✅ ORI Studio IDE (vibe coding + ORI DSL)
- ✅ Canvas streaming generation
- ✅ Research mode (deep model routing)
- ✅ Workflows (build + run)
- ✅ Memory Browser, Goals, Agents, Connections
- 🔄 Artifacts library (canvas outputs persisted and browsable)
- 🔄 Full autonomous goal execution UI
- 🔄 Multi-agent collaboration view (Hive visualization)
- 🔄 Mobile-responsive layout

---

*This document is the canonical design context for ORI Studio. Last updated: March 2026.*
