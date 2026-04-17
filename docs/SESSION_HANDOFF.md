# Session Handoff

Open this first at the start of a session.

This file is the operational handoff for the VPS working copy. It should stay short, current, and useful. It is not a changelog and it is not product doctrine.

If time is short, update only:

- `Last Updated`
- `Current Focus`
- `What Changed This Session`
- `Next Best Move`
- top entry in `Session Log`

---

## Handoff Rules

- Keep this practical, not polished.
- Prefer bullets over long explanation.
- Update what is live on-box, not what is merely planned.
- Name the exact next implementation move so a future agent can continue without re-auditing.
- If priorities change, update `Current Focus` before anything else.

## Last Updated

- `2026-04-08 01:45 UTC`

## Current Focus

ORI Studio product refinement for SMBs, especially the workflow surface now renamed conceptually to `Jobs`.

Current direction:

- ORI Studio = SMB operator surface
- ORI Home = everyday companion / chat-first layer
- ORI Dev = later creative companion layer

Studio should feel like:

`ORI knows my business and handles it for me when I need her to.`

Not:

- an AI playground
- a workflow lab
- a generic chatbot

## Current Snapshot

### Product truths

- Email-first is real and already works well enough to lean into.
- SMB means solo operators and tiny teams, especially service businesses.
- `Jobs` is the right user-facing label.
- Morning briefing remains a built-in ORI behavior, not a Job.
- Guided setup is the right pattern for starter Jobs.

### What is live now

- Landing page is warmer, calmer, and SMB-friendly.
- FAQ is shorter, tabbed, and on the same marketing palette as landing.
- Public-facing jargon like `sovereign` has been translated into plain customer language.
- Softer `OriStudio` wordmark is used on public-facing Studio pages.
- `Jobs` is the canonical SMB workflow surface.
- Starter Jobs are service-business oriented:
  - Invoice Check and Summary
  - Customer Follow-Up Draft
  - Today’s Schedule Check
  - Weekly Job Recap
- Guided setup exists for:
  - Invoice Check
  - Today’s Schedule Check

### Guided setup pattern

1. User clicks a starter Job
2. Small modal asks practical business questions
3. ORI builds the underlying workflow
4. User lands in the editor with a configured job

This is the preferred pattern going forward.

## What Changed This Session

- Added a stronger handoff format to this file so future agents can resume quickly.
- Preserved the current Studio product direction, live status, and next build target.
- Added a first-pass agent knowledge layer under `docs/` with playbooks, runbooks, and recipes for future agent execution.
- Added a cross-product architecture direction in `docs/ORI_CORE_ARCHITECTURE.md`.
- Direction now assumes `One Ori, many surfaces`: ORI as the system, Oracle as the default reasoning muscle, local models as utility/fallback workers.
- Added explicit `red` surface support in the shared ORI runtime plus a dedicated `ori_red` profile for ORI Red / vuln.ai work.
- Curated the shared profile set into product-facing working styles (`smb_assistant`, `home_companion`, `dev_builder`, `ori_red`) while keeping `ori_core` and `oricli` internal.
- Added a machine-readable surface skill catalog in `config/skill_catalog.json` plus `docs/ORI_PROFILE_AND_SKILL_CURATION.md`.
- Started a real docs cleanup system with `docs/README.md` and `docs/DOCS_REFACTOR_PLAN.md` so stale docs stop silently acting like source-of-truth.
- Rewrote `docs/SKILLS.md`, `docs/REASONING.md`, `docs/SOVEREIGN_STACK.md`, `docs/ORI_HOME_SPEC.md`, and `docs/SMB_DEVELOPER_GUIDE.md` into current-language supporting docs instead of older-era stack manifestos.
- Replaced the old public and agent-facing overview docs with:
  - `docs/public_overview.md` for plain-language public framing
  - `docs/AGENT_API.md` as the handoff/readme for external agents and app builders using ORI
- Rewrote `docs/API.md` into a shorter practical platform reference instead of a giant mixed-era endpoint dump.

## Current UX Direction

### Keep

- `Jobs` as the main SMB workflow surface
- Email-first runtime model
- Starter Jobs
- Guided setup modals
- Warm marketing palette for public-facing pages

### Demote later

- `Workflows`
- `Pipeline Canvas`
- `ORI Studio` DSL/editor

These can remain for advanced or internal use, but should not define the SMB product story.

## Open Threads

1. The `Jobs` editor still becomes more builder-like once inside the job.
   The entry experience is improving, but the inside still feels like a generic workflow tool.

2. More starter Jobs need guided setup.
   Best next candidates:
   - Customer Follow-Up
   - Weekly Job Recap

3. Studio home/dashboard may still need to be reshaped around relief:
   - what ORI handled
   - what needs approval
   - what should I do next

4. Overlapping workflow surfaces still exist in Studio.
   They have not been removed or hidden yet.

## Next Best Move

Continue the docs authority cleanup:

- rewrite or relabel the docs most likely to mislead current work:
- review `docs/API.md`, `docs/AGENT_API.md`, and `docs/public_overview.md`
- review `docs/EXTERNAL_INTEGRATION.md` and decide whether it should be folded into current docs, reduced to deep reference, or marked historical
- decide what in `oricli_core/docs/` should stay implementation-only versus move into main docs
- start adding short status headers to older theory/reference docs instead of letting them silently read as current doctrine

Why:

- product and runtime changed faster than the docs did
- stale docs are now a real source of confusion
- the repo needs clear source-of-truth layers before more surfaces get added

## Watchouts

- Do not drift Studio back toward ORI Home’s chat/companion feel.
- Do not let ORI Dev concerns shape Studio right now.
- Do not reintroduce dark, aggressive, “AI bunker” marketing tone.
- Do not promote advanced workflow surfaces as the main SMB path.

## Files Most Relevant Right Now

- [LandingPage.jsx](/home/mike/Mavaia/ui_sovereignclaw/src/pages/LandingPage.jsx)
- [FAQPage.jsx](/home/mike/Mavaia/ui_sovereignclaw/src/pages/FAQPage.jsx)
- [AutomationsPage.jsx](/home/mike/Mavaia/ui_sovereignclaw/src/pages/AutomationsPage.jsx)
- [HomePage.jsx](/home/mike/Mavaia/ui_sovereignclaw/src/pages/HomePage.jsx)
- [NavRail.jsx](/home/mike/Mavaia/ui_sovereignclaw/src/components/NavRail.jsx)
- [ORI_STUDIO_PRODUCT_VISION.md](/home/mike/Mavaia/docs/ORI_STUDIO_PRODUCT_VISION.md)
- [ui_sovereignclaw/README.md](/home/mike/Mavaia/ui_sovereignclaw/README.md)

## Session Log

### 2026-04-07 05:39 UTC

- Added a stronger, reusable session-handoff format.
- Current workstream remains ORI Studio, especially `Jobs`.
- Best next move remains guided `Customer Follow-Up`.

### 2026-04-07 07:00 UTC

- Added `docs/AGENT_KNOWLEDGE_LAYER.md` as the entrypoint for future agents.
- Added product playbooks for Studio, Home, and Dev.
- Added runbooks for live VPS UI work and Studio guided Jobs.
- Added recipes for guided starter Jobs and the next `Customer Follow-Up` implementation move.

### 2026-04-07 21:59 UTC

- Added `docs/ORI_CORE_ARCHITECTURE.md`.
- Locked the cross-product direction to `One Ori, many surfaces`.
- Direction now favors ORI as the system layer, Oracle as the default reasoning layer, and local models only as utility/fallback workers.
- Next best move is starting the core-vs-overlay separation work.

### 2026-04-08 00:00 UTC

- Added explicit `red` surface support to the shared overlay architecture.
- Added `ori_red` as a dedicated ORI Red runtime profile.
- Next best move is wiring ORI Red / `vuln.ai` clients to send the `red` surface context into the shared runtime where appropriate.

### 2026-04-08 01:00 UTC

- Added `docs/README.md` as the docs entrypoint.
- Added `docs/DOCS_REFACTOR_PLAN.md` to define source-of-truth vs historical/reference docs.
- Next best move is rewriting the most misleading stale docs, starting with `docs/SKILLS.md`.

### 2026-04-08 01:20 UTC

- Rewrote the most misleading current docs into the new authority model:
  - `docs/SKILLS.md`
  - `docs/REASONING.md`
  - `docs/SOVEREIGN_STACK.md`
  - `docs/ORI_HOME_SPEC.md`
  - `docs/SMB_DEVELOPER_GUIDE.md`
- Next best move is reviewing `docs/API.md`, `docs/AGENT_API.md`, and `docs/public_overview.md` for the same old-world drift.

### 2026-04-08 01:35 UTC

- Replaced `docs/public_overview.md` with a plain-language ORI overview.
- Replaced `docs/AGENT_API.md` with the external-agent/app-builder integration README.
- Next best move is deciding how to break down `docs/API.md` so it stays useful without dragging old-world framing forward.

### 2026-04-08 01:45 UTC

- Rewrote `docs/API.md` into a shorter current platform reference.
- `docs/EXTERNAL_INTEGRATION.md` is now the main likely old-world API/integration drift doc to review next.

### 2026-04-16 03:15 UTC

- Replaced `gpt-4.1` with `gpt-5-mini` as the default Oracle Copilot reasoning model.
- Updated `pkg/oracle/oracle.go` and its corresponding tests.
- Verified that `gpt-5-mini` correctly omits the `--reasoning-effort` flag by default.

## End-of-Session Update Template

Copy and replace the latest `Session Log` entry with something like this:

```md
### YYYY-MM-DD HH:MM UTC

- Worked on:
- Changed:
- Live on-box:
- Still unresolved:
- Next best move:
```

## End-of-Session Update Checklist

Before ending a session, update:

- `Last Updated`
- what page or surface we were working on
- what is now live on-box
- what still feels unresolved
- the next concrete implementation move

If nothing else gets updated, update `Next Best Move` and add one new `Session Log` entry.
