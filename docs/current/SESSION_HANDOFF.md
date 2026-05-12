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

- `2026-05-09 UTC`

## Current Focus

ORI is being shaped as one shared reasoning system with reusable intelligence layers, not app-specific clones.

Current direction:

- Ongoing research loop: Mike reverse-engineers useful apps/products, then ORI extracts the underlying cognition primitive instead of cloning the app.
- Active 2026-05-09 trajectory: SaaS/product cognition scan → reusable ORI cognition primitives → small app-neutral API endpoints → smoke/deploy every 2-3 additions.
- ORI Core stays the shared identity and API/runtime layer.
- ORI Home now has reusable planning, reflection, and household logistics intelligence.
- ORI Learn now has reusable material-to-mastery intelligence.
- ORI Studio remains the SMB operator surface; do not let Home companion behavior leak into Studio.
- ORI Dev remains the builder surface; use it for implementation and integration work.
- Research docs should be mined for ORI-wide primitives first, not copied as full apps.

Primary implementation posture:

`Extract the cognitive capability, keep product/app storage and UI outside ORI unless explicitly required.`

Product-app reports should be treated as cognitive extraction canvases:

- identify the retention mechanism and cognitive burden being reduced
- name the reusable primitive(s)
- implement deterministic package-level foundations first
- add `.ori` skill lanes and surface/profile metadata only when useful
- expose a small internal/API tool surface when clients need direct invocation
- leave capture, OCR, storage, sync, reminders, calendars, payments, booking, and UI to product clients unless explicitly scoped

## Current Snapshot

### Product truths

- Users choose product surfaces and working-style profiles; they should not manage raw skills directly.
- Home should feel low-load, gentle, one-thing-at-a-time, and useful in ordinary life.
- Studio should feel practical, operator-oriented, and relief-focused for SMBs.
- Dev should stay technical and builder-oriented.
- Runtime code wins for API behavior; product docs win for surface intent.

### What is live now

- Public runtime: `https://glm.thynaptic.com/v1`
- Local runtime ports: `8088` and `8089`
- Default model lane: `oricli-oracle`
- Live `/v1/modules` count after latest deploy: `40`
- Services restarted and healthy after latest changes:
  - `oricli-api`
  - `oricli-backbone`

### New Home intelligence layers

Planning:

- `planning_decomposer`
- `task_patch_planner`
- `executive_function_coach`
- `focus_session_conductor`
- `planning_review_rescheduler`

Reflection:

- `reflective_journal_companion`
- `reflection_prompt_generator`
- `personal_pattern_synthesizer`
- `memory_handoff_curator`

Household logistics:

- `household_context_ingester`
- `active_pin_resolver`
- `temporal_deadline_guardian`
- `household_resolution_drafter`

Learning/mastery:

- `material_to_mastery_compiler`
- `adaptive_explanation_layer`
- `guided_completion_mode`
- `user_corpus_grounding`
- `learning_goal_dag`

Reusable cognition API primitives now live:

- `POST /v1/learning/mastery/compile` — MaterialToMasteryCompiler
- `POST /v1/quest/scaffold` — Cajun Koi extraction: Quest Scaffold
- `POST /v1/behavior/create`, `/event`, `/state` — Habitica extraction: Behavioral Reinforcement Substrate
- `POST /v1/context/momentum` — Tiago Forte extraction: Context-to-Momentum Engine
- `POST /v1/procedure/compile` — Scribe extraction: Procedure Compiler
- `POST /v1/workflow/grammar/compile` — raw ORI substrate: Workflow Grammar Compiler
- `POST /v1/actions/plan` — Zapier/Make extraction: Sovereign Action Gateway planner
- `POST /v1/conversation/harvest` — Granola extraction: Conversational Context Harvester
- `POST /v1/temporal/coordinate` — Motion extraction: Temporal Coordination Engine
- `POST /v1/anticipation/prepare` — Superhuman Go extraction: Ambient Anticipation
- `POST /v1/codebase/task/plan` — Cursor extraction: Codebase-Resident Task Agent planner
- `POST /v1/continuity/recover` — GPT Pulse/Notion extraction: Continuity Recovery Engine
- `POST /v1/execution/orchestrate` — GPT Pulse/Linear extraction: Intent-First Execution Orchestrator
- `POST /v1/workgraph/compile` — ClickUp extraction: WorkGraph v0
- `POST /v1/workgraph/answer` — ClickUp extraction: Ambient Answers
- `POST /v1/contextual-action/plan` — Clay extraction: Contextual Action Fabric
- `POST /v1/signals/opportunities` — Clay extraction: Signal Opportunity layer
- `POST /v1/intent/timeline` — calm-software extraction: Intent Timeline
- `POST /v1/procedural/crystallize` — calm-software extraction: Procedural Crystallizer
- `POST /v1/memory/semantic/graph` — Tana/calm-software extraction: Semantic Memory Graph
- `POST /v1/resources/commitment/reason` — YNAB extraction: Commitment-Aware Resource Reasoner

## What Changed This Session

### 2026-05-09 — Pulse, ClickUp, Clay, calm software, and YNAB cognition primitives

- **Intent Timeline shipped** — mined the calm-software retention canvas into `/v1/intent/timeline`: work events, artifacts, decisions, constraints, outcomes, and open loops → preserved intent moments, detected intent shifts, rationale trails, current-intent state, continuity packets, memory seeds, and Continuity/WorkGraph/Procedure/Memory/Temporal hints.
- **Procedural Crystallizer shipped** — mined the calm-software retention canvas into `/v1/procedural/crystallize`: repeated workflow runs, triggers, steps, tools, pain points, inputs, outputs, and outcome signals → pattern readiness, candidate procedure, skill candidate, automation readiness, next-observation plan, memory seeds, and Procedure/Skills/WorkGraph/Memory/Temporal/Forge hints.
- **Semantic Memory Graph shipped** — mined Tana / calm-software retention insight into `/v1/memory/semantic/graph`: loose captures, node hints, tags, people, objects, source handles, and retrieval questions → ontology-free nodes, edges, soft clusters, recoverability score, retrieval moves, progressive-structure guidance, memory seeds, and Memory/WorkGraph/Continuity/Intent/Procedure hints.
- **Commitment-Aware Resource Reasoner shipped** — mined YNAB into `/v1/resources/commitment/reason`: scarce resource pools, proposed actions, explicit commitments, hidden-obligation context, decision questions, and drift events → resource reality, protected/affected commitments, tradeoff options, least-disruptive repair, non-shaming permission language, memory seeds, and Memory/Chronos/WorkGraph/Temporal/Intent/Behavior hints.
- **Workflow Grammar Compiler shipped** — raw ORI substrate at `/v1/workflow/grammar/compile`: natural-language workflow intent, triggers, conditions, action hints, available tools, approvals, constraints, and exceptions → trigger/action graph, variables, approval gates, failure modes, dry-run plan, readiness score, compiled expression, and Procedure/WorkGraph/Temporal/Forge/Memory hints.
- **Sovereign Action Gateway planner shipped** — mined Zapier/Make action-reach insight into `/v1/actions/plan`: intent, action hints, available providers, scopes, approval policy, risk tolerance, and memory policy → ranked action candidates, recommended provider route, approval gate, policy labels, audit plan, dry-run instructions, memory plan, and WorkflowGrammar/WorkGraph/CALI/SCL/Chronos/Red hints. It does not execute external actions.
- **Todoist Karma report triaged, no new endpoint** — useful extraction is future `Behavior Reflection v2`: enrich `/behavior/state` or a small adjacent behavior reflection surface with longitudinal, shame-safe continuity reflection, recovery quality, friction zones, sustainable pace, and identity-safe next adjustment. Do not build XP, badges, streak worship, public productivity scores, or metric-addiction loops.
- **Deploy cadence followed** — focused cognition/API tests, engine build, dev-portal JSON validation, scratch server smokes, binary swap, service restarts, local authenticated smokes, and public authenticated smokes passed. Latest observed `/v1/modules` count remains `40` because these additions are API primitives, not new `.ori` skills.
- **Current substrate shape** — Intent Timeline preserves why work changed; Procedural Crystallizer notices repeated operational paths before they become SOPs, `.ori` skills, or low-risk automations; Semantic Memory Graph makes loose information recoverable without folder/taxonomy maintenance; Commitment Resource Reasoning turns scarcity into explicit tradeoffs without financial-product behavior or shame loops; Workflow Grammar Compiler converts messy automation intent into reviewable workflow structure; Sovereign Action Gateway chooses governed provider routes before execution exists.
- **Continuity Recovery Engine shipped** — mined GPT Pulse / Notion-style workspace OS insight into `/v1/continuity/recover`: previous sessions, artifacts, decisions, commitments, and open loops → compact recovered thread, context packets, decision/commitment logs, suggested continuation, and Memory/Chronos/Conversation/Temporal/Procedure hints.
- **Intent-First Execution Orchestrator shipped** — mined GPT Pulse / Linear clarity-velocity pattern into `/v1/execution/orchestrate`: goal/intent, task state, blockers, dependencies, energy, time, and recent signals → momentum score, next-best move, next options, blocked-because reasoning, dependency edges, and Continuity/Temporal/Procedure/Memory hints.
- **WorkGraph v0 shipped** — mined ClickUp into `/v1/workgraph/compile`: messy operator context, notes, conversations, and work items → typed work-state objects: jobs, tasks, decisions, owners, deadlines, blockers, approvals, notes, follow-ups, metrics, edges, operator pulse, and integration hints.
- **Ambient Answers shipped** — mined ClickUp Brain-style ambient retrieval into `/v1/workgraph/answer`: supplied WorkGraph state + operator question → findings, recommended moves, confidence, and Execution/Continuity/Memory hints. It answers from supplied graph only and does not mutate workspaces.
- **Contextual Action Fabric shipped** — mined Clay into `/v1/contextual-action/plan`: entity + objective + tools/evidence/signals/constraints → entity profile, missing context, evidence waterfall, fit/confidence score, governed recommendations, and reusable Skill Function candidate.
- **Signal Opportunity layer shipped** — mined Clay signals into `/v1/signals/opportunities`: entity-bound signals + context/objective/windows → ranked opportunities, handle-first recommendation, watchlist candidates, memory seeds, and Contextual Action/Temporal/WorkGraph hints.
- **Deploy cadence followed** — after each 2-primitives batch, built `./cmd/oricli-engine/`, swapped `/home/mike/Mavaia/bin/oricli-go-v2`, restarted `oricli-api.service` and `oricli-backbone.service`, and smoked live endpoints.
- **Latest live verification completed** — focused cognition/API tests, engine build, dev-portal JSON validation, `/v1/modules` smoke, and endpoint smokes passed. Latest smoked endpoint: `/v1/actions/plan`. Latest observed `/v1/modules` count remains `40`.
- **Current substrate shape** — WorkGraph knows the operator's work state; Contextual Action Fabric knows how to gather entity evidence and make a governed next action obvious; Continuity/Execution turn prior state into the next useful move; Commitment Resource Reasoning exposes scarcity, obligations, and repair paths without cloning budgeting software.

### 2026-05-08 — OpenAI runtime migration + SaaS cognition primitives

- **Oracle provider migration shipped** — ORI's primary Oracle runtime now uses OpenAI Responses API directly. Public API still exposes `oricli-oracle`; internal defaults are `gpt-5.4-mini` for light chat and `gpt-5.5` for heavy/research/vision. Anthropic is no longer the active primary Oracle path.
- **Persona/runtime integrity benchmark drove provider decision** — after Claude broke ORI persona during a simple AGLI doc-read task, ORI moved toward OpenAI for continuity, capability, and architecture integrity.
- **Quest Scaffold shipped** — mined Cajun Koi into `/v1/quest/scaffold`: vague goal → adult role identity, first action, milestones, rhythm, workspace, progress model, review schedule, and Memory/Chronos/GoalDaemon/PAD hints.
- **Behavioral Reinforcement Substrate shipped** — mined Habitica into `/v1/behavior/create`, `/v1/behavior/event`, and `/v1/behavior/state`: behavior/routine loops, completion/miss/defer handling, shame-safe recovery, stability scoring, and Memory/Chronos/GoalDaemon/PAD/CALI hints.
- **Context-to-Momentum Engine shipped** — mined Tiago Forte motivation frameworks into `/v1/context/momentum`: messy context → actionability buckets, future-self packets, next 5/30-minute moves, stepping stone, and Memory/Chronos/GoalDaemon hints.
- **Procedure Compiler shipped** — mined Scribe into `/v1/procedure/compile`: observed workflow → SOP, checklist, skill candidate, automation readiness, SCL TierSkills seed, and GoalDAG/Chronos/Forge hints.
- **Conversational Context Harvester shipped** — mined Granola into `/v1/conversation/harvest`: meeting/chat turns → decisions, commitments, unresolved threads, follow-up packets, memory seeds, and Memory/Chronos/GoalDAG/Procedure hints.
- **Temporal Coordination Engine shipped** — mined Motion into `/v1/temporal/coordinate`: tasks/windows/fixed events/energy/dependencies → now/next/later buckets, schedule proposals, conflicts, memory seeds, and Chronos/GoalDAG/Memory automation hints.
- **Ambient Anticipation shipped** — mined Superhuman Go into `/v1/anticipation/prepare`: upcoming situation → readiness score, prep packets, missing context, suggested tone, safe next moves, and Memory/Chronos/Conversation/Temporal hints.
- **Codebase-Resident Task Agent planner shipped** — mined Cursor into `/v1/codebase/task/plan`: dev intent/repo signals → scoped work packets, file ownership proposals, risks, verification, delegation hints, and Procedure/Temporal/Memory/Forge hints.
- **Deploy cadence followed** — after each 2-primitives batch, built `./cmd/oricli-engine/`, swapped `/home/mike/Mavaia/bin/oricli-go-v2`, restarted `oricli-api.service` and `oricli-backbone.service`, and smoked live endpoints.
- **Live verification completed** — focused cognition/API tests, engine builds, dev-portal JSON validation, local endpoint smokes, module check, and service restarts all passed. Latest observed `/v1/modules` count remains `40`.

### 2026-05-08 — Codex migration + ORI intelligence layers

- **Codex context merged** — `AGENTS.md` and Codex memory now point future sessions at this handoff and the ORI-wide reusable-intelligence trajectory.
- **SCAI remold shipped** — instead of visibly showing corrections, SCAI now regenerates under tightened constraints and returns the safer final answer.
- **Temporal Clock upgraded** — added richer event kinds, session arc, temporal commitments, continuity ledger, claim guard, salience scoring, persistence, and tests.
- **MCTS/value/reflection repair shipped** — restored value-network path, repaired MCTS integration, added reflection v2, and verified cognition/API builds.
- **Planning intelligence shipped** — mined the Neurolist-style planner research for reusable ORI executive-function primitives and five Home planner skills.
- **Reflection intelligence shipped** — mined the Rosebud research for dialogic reflection, prompt generation, pattern synthesis, and consent-aware memory handoff skills.
- **Household logistics shipped** — mined the ORI Home School Wedge report for Active Pin, deadline, context-ingestion, and one-tap resolution primitives.
- **Learning substrate shipped** — mined the Knowunity report for MaterialToMasteryCompiler, adaptive explanation, guided completion, user-corpus grounding, LearningGoalDAG, mastery ledger, and `learn` surface/profile primitives.
- **Local runtime key refreshed** — stale `.oricli/api_key` was regenerated through first-party app registration and verified against `/v1/learning/mastery/compile`.
- **Skill routing made more deterministic** — `SkillManager` now sorts skill lists and ranks trigger matches by specificity before name.
- **Docs updated around Home planner/reflection/logistics lanes** — `docs/current/SKILLS.md`, `docs/api/AGENT_API.md`, and `docs/product/ORI_HOME_SPEC.md` now describe the new layers and app-boundary constraints.
- **Live verification completed** — focused tests, package tests, build, local smoke, live health checks, module checks, and service restarts all passed.

### 2026-05-05 (session 3) — ORI VPS CLI

- **`thynaptic/ori-vps/` built and shipped** — Go CLI, binary `ori` at `~/.local/bin/ori`
- **REPL + one-shot modes** — `ori` drops into readline REPL, `ori "query"` one-shots
- **Always-on tool loop** — `read_file`, `list_dir`, `write_file`/`edit_file` (.md only), `run_command` (bash, 30s timeout), 9 GitHub tools via `gh` CLI
- **Markdown rendering** — glamour with auto-style, full syntax (headers, tables, code blocks)
- **Local SQLite store** — tasks + notes at `~/.ori/ori.db`
- **VPS context injected** — live service health, SCL stats, TCD domain count, 2h daemon logs, open tasks; 5min cache
- **Session persistence** — session ID survives across one-shot calls (`~/.ori/session`)
- **GitHub tools** — list/get/create issues, list/get PRs, list commits, get file contents, list repos; auth via existing `gh` CLI session (`cassianwolfe`)
- **Status check** — proper `oneshot` service handling (`glm-mesh-ping` shows last run result, not false-negative "down")
- Registered in `registry.yaml` and `CLAUDE.md` products table

### 2026-05-05 (session 2) — Epistemics Engine

- **`pkg/epistemics/` built and shipped** — conjecture-criticism-synthesis loop. Closes Deutsch's gaps 1–3 (mimicry vs creativity, prediction vs explanation, philosophical bottleneck).
- **3-pass loop:** Conjecture (Haiku) → Criticism (Haiku, adversarial, severity-scored 0–1) → Synthesis (Haiku or Sonnet if severity ≥ 0.65)
- **Early-exit** on convergence (word overlap > 75%) or weak criticism (severity < 0.2)
- **Oracle router** updated — `IsExplanatory` flag on `Decision`, auto-detects why/how/what-causes queries
- **server_v2** hooked — epistemics pre-pass fires on heavy-route explanatory queries, fallback to oracle on error
- **`pkg/llm/`** — `ChatModel()` added (configurable model + max_tokens), `HaikuModel`/`SonnetModel` exported
- **`IsExplanatoryQuery()`** lives in `pkg/epistemics/` — oracle calls through, no cycle
- **Two agent personas** — `ori-conjecturer.agent.md`, `ori-critic.agent.md`
- **Test suite** — `TestDeutschGaps` (live, 4 queries, full trace), offline routing/parsing/convergence tests. All passed. 119s for 4 live cycles.
- **`scripts/proof_epistemics.sh`** — bash API-level smoke test
- **Deployed** — binary swapped, 8088/8089 live
- **`docs/current/CLAUDE_PROJECTS_README.md`** — platform README for Claude Projects context

Cost: ~$0.014–$0.034/cycle. Daemon idle ~$6–17/month.

### 2026-05-05 (session 1) — Repo Cleanup

- **20 dead `pkg/core/` packages deleted** — adversarial, audit, contextindex, document, http, idempotency, intent, memorydynamics, metareasoning, observability, orchestrator, policy, ratelimit, reasoning, skillcompiler, state, stylecontract, symbolicoverlay, toolcalling, upstream. Kept: auth, config, model, store.
- **`TALOS_` → `ORI_` rename complete** — 426 occurrences across 14 files in pkg/cognition/, pkg/memory/, pkg/enterprise/memory/
- **vuln.ai/ archived** — moved to `~/vuln.ai-archived/`, out of repo
- **All SLM eviction changes from 2026-05-02 committed** — were unstaged, now in history
- Build clean, zero broken imports

## What Changed Last Session

### 2026-05-02 — SLM Eviction + Oracle Migration

- **Full SLM purge** — every hardcoded llama/qwen/ministral/gemma/phi/deepseek model name evicted from active code paths outside `pkg/core/` (dead zone) and the `GenerationService` itself (embedding-layer internals)
- **`pkg/llm/` confirmed** — Mike built this today (thin Haiku wrapper, Anthropic direct, prompt caching). It's the lightweight inference path for all cognition-tier work.
- **Dead model vars killed** — `intentModels`, `symbolicModels`, `intentFastModels`, `importanceEvalModels`, `visionModels`, `models []string` across cognition + memory packages
- **Timeout gremlins fixed** — `supervision_policy.go`, `reflection_policy.go`, `style_model.go`, `style_profile.go`: 60-250ms SLM-era timeouts bumped to 3s default / 1-15s range
- **Vision fully migrated to Oracle** — `vision_grounding.go` (live), `node/vision_module.go` (dead→migrated), both `multimodal.go` files cleaned
- **Enterprise memory importance eval** — migrated from Ollama loop to `llm.Chat()`, stale `mm.client == nil` guard fixed
- **forge, tcd, pad** — `GateDistiller`/`Distiller` interfaces removed, `ministral-3:3b`/`qwen2.5-coder:3b` evicted, all wired to `llm.Chat()`
- **reform_daemon.go** — `qwen2.5-coder:3b` evicted, now `llm.Chat()` with constitution as system prompt
- **DreamDaemon, CuriosityDaemon, ChronosDaemon** — all three migrated from GenService (Ollama) to `llm.Chat()`. ORI now grows idly for ~$1-3/month on Haiku.
- **ChronosDaemon** — `LLMSummarizer` interface removed entirely, wires direct to `llm.Chat()`
- **Stale comments swept** — sovereign.go, confidence.go, task_executor.go, task_decomposer.go, reasoning_engines.go, reasoning_modes.go, browser.go, both evolution.go files, self_model.go, scai.go
- **`pkg/core/` identified as dead zone** — 21 of 24 packages have zero external callers outside pkg/core itself. Full G-LM server stack (http, orchestrator, reasoning, upstream, ratelimit, policy...) is orphaned. Cleanup deferred — Mike's call.
- **AGLI + Thynaptic docs updated** — Perimeter Sovereignty reframed (architecture sovereign, intelligence tier is Anthropic), Phase II design constraints updated, company overview GitHub Copilot reference killed

## What Changed This Session (Previous)

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

- One ORI, many surfaces.
- Working styles over raw skills.
- Home: low cognitive load, Active Pin, no shame, presence over productivity.
- Studio: SMB operator surface, `Jobs`, guided setup, email-first where useful.
- Dev: builder surface, implementation and integration.
- Research-to-runtime loop: read research, extract ORI-wide primitives, ship small deterministic foundations + `.ori` skills.
- Reverse-engineered app cognition as the ongoing implementation strategy: app success pattern → burden reduced → reusable ORI primitive → deterministic package/API surface.

### Avoid

- Turning ORI into a clone of any single app from research.
- Claiming calendar/reminder/payment/booking/memory actions happened unless a tool confirms them.
- Therapy-product claims, diagnosis, or clinical framing for reflection features.
- Surfacing internal/protected lanes as product settings.
- Letting old `sovereign`/bunker language leak into public product framing.

## Open Threads

1. Planning, reflection, and household logistics primitives are still partly package-level helpers and `.ori` skills. The new SaaS-extracted primitives now have dedicated API endpoints, but the older Home planner/reflection/Active Pin primitives may still need direct endpoint exposure if Home clients need them.

2. Home clients will still need to own capture, OCR, local storage, sync, notifications, calendars, reminders, biometric locks, and consent policy.

3. `docs/current/SKILLS.md` is current for the new Home lanes, but `config/skill_catalog.json` may need a follow-up pass if product-surface curation becomes machine-enforced.

4. Older Studio work is still valid, but ORI Core now has enough app-neutral cognition primitives that Studio/Home/Dev clients should consume shared substrate before inventing product-local intelligence.

5. Epistemics/CuriosityDaemon integration remains valuable, but the immediate trajectory is the product/SaaS cognition extraction loop.

## Next Best Move

**Continue the SaaS/product cognition extraction loop and keep shipping the strongest primitives as small app-neutral API surfaces.**

Recommended next slice:

- For the next research docs Mike pulls up, read the ranking/primitive scan first and choose one extraction at a time.
- Favor primitives that reduce cognitive load or turn ambient context into useful action substrate.
- Keep endpoints deterministic, app-neutral, and explicit about product-client ownership of storage, writes, reminders, calendars, notifications, payments, and UI.
- Add package tests + handler tests for each primitive.
- After every 2-3 new primitives, build `./cmd/oricli-engine/`, restart `oricli-api.service` + `oricli-backbone.service`, and smoke the new endpoints live.
- Good next primitives if no new target is supplied: `Semantic Time Navigation` / context trace, future `Behavior Reflection v2` folded into the behavioral substrate, `Observable Cognitive Workflow Graph`, or app-derived workflow hardening from Zapier/Make/Airtable.

After that:

- Consider a thin internal Dev/Home/Studio client flow that composes these primitives instead of calling them manually.
- Revisit `config/skill_catalog.json` if surfaced skill groups need machine-readable product curation.
- Return to CuriosityDaemon → epistemics integration when the reusable primitive lane has a stable invocation story.

## Previous Next Best Move

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
- Do not let ORI Dev concerns shape Studio product copy.
- Do not reintroduce dark, aggressive, “AI bunker” marketing tone.
- Do not claim ORI owns app-layer storage/sync/OCR/calendar/reminder/payment behavior unless implemented.
- Do not write over user changes in the dirty worktree; inspect diffs first.
- Test runs can append to `pkg/cognition/.memory/*_audit.jsonl`; remove only generated test-run lines before finishing.

## Files Most Relevant Right Now

- [AGENTS.md](/home/mike/Mavaia/AGENTS.md)
- [SKILLS.md](/home/mike/Mavaia/docs/current/SKILLS.md)
- [AGENT_API.md](/home/mike/Mavaia/docs/api/AGENT_API.md)
- [ORI_HOME_SPEC.md](/home/mike/Mavaia/docs/product/ORI_HOME_SPEC.md)
- [planning_intelligence.go](/home/mike/Mavaia/pkg/cognition/planning_intelligence.go)
- [reflection_intelligence.go](/home/mike/Mavaia/pkg/cognition/reflection_intelligence.go)
- [home_logistics_intelligence.go](/home/mike/Mavaia/pkg/cognition/home_logistics_intelligence.go)
- [learning_intelligence.go](/home/mike/Mavaia/pkg/cognition/learning_intelligence.go)
- [work_graph.go](/home/mike/Mavaia/pkg/cognition/work_graph.go)
- [contextual_action_fabric.go](/home/mike/Mavaia/pkg/cognition/contextual_action_fabric.go)
- [signal_opportunity.go](/home/mike/Mavaia/pkg/cognition/signal_opportunity.go)
- [continuity_recovery.go](/home/mike/Mavaia/pkg/cognition/continuity_recovery.go)
- [execution_orchestrator.go](/home/mike/Mavaia/pkg/cognition/execution_orchestrator.go)
- [skills.go](/home/mike/Mavaia/pkg/service/skills.go)
- [global_routing.ori](/home/mike/Mavaia/oricli_core/rules/global_routing.ori)

## Session Log

### 2026-05-09 UTC

- Shipped calm-software retention primitives from `ori_retention_mechanics_calm_software_codex_canvas.md`.
- Shipped YNAB extraction from `CAIO_Canvas___YNAB.md` as `/v1/resources/commitment/reason`.
- Shipped Zapier/Make extraction from `Multi-Part_Report__Zapier___Make.md` as `/v1/actions/plan`.
- Live endpoints now include `/v1/intent/timeline`, `/v1/procedural/crystallize`, `/v1/memory/semantic/graph`, `/v1/resources/commitment/reason`, `/v1/workflow/grammar/compile`, and `/v1/actions/plan`.
- Verified focused cognition/API tests, engine build, dev-portal JSON, scratch server smokes, live local smokes, public authenticated smokes, service health, and `/v1/modules` count `40`.
- Current trajectory: continue CAIO/product reverse-engineering into reusable ORI substrate; next strong candidates are `Semantic Time Navigation`, future `Behavior Reflection v2`, `Observable Cognitive Workflow Graph`, or a thin composition flow across Continuity + Intent Timeline + Procedural Crystallizer + Commitment Resource Reasoning + Workflow Grammar + Action Gateway.

### 2026-05-09 UTC

- Updated handoff for new-session continuity.
- Live runtime still reports `/v1/modules` count `40`.
- Latest deployed/smoked primitive pair: Clay `Contextual Action Fabric` and `Signal Opportunity`.
- Current trajectory: continue CAIO/product reverse-engineering into reusable ORI substrate; deploy every 2-3 primitives.

### 2026-05-08 UTC

- Migrated working continuity from Claude Code context into Codex-native handoff/orientation.
- Shipped SCAI regenerate-not-correct behavior.
- Upgraded Temporal Clock.
- Repaired MCTS value network + reflection v2.
- Built and deployed reusable planning, reflection, and household logistics intelligence layers.
- Built and deployed reusable learning/material-to-mastery intelligence layers from the Knowunity report.
- Shipped OpenAI Responses primary Oracle runtime.
- Shipped SaaS/product primitives through Cajun Koi, Habitica, Tiago Forte, Scribe, Granola, Motion, Superhuman Go, Cursor, GPT Pulse, ClickUp, and Clay.
- Regenerated stale local runtime key and verified authenticated learning compiler smoke.
- Live `/v1/modules` count is `40`.
- Next: continue app reverse-engineering into ORI cognition; prioritize reusable substrate over product-shell cloning.

### 2026-05-05 UTC (session 3)

- Built ori-vps from scratch — Go CLI with REPL, tool loop, markdown rendering, GitHub tools
- Shipped to ~/.local/bin/ori, available as `ori` alias
- Next: extend tools as needed (more GitHub ops, ClickUp integration, etc.)

### 2026-05-05 UTC (session 2)

- Built and shipped pkg/epistemics/ — conjecture-criticism-synthesis loop
- Live test passed: 4 Deutsch-relevant queries, full dialectical trace, escalated to Sonnet where warranted
- Deployed to 8088/8089
- Wrote CLAUDE_PROJECTS_README.md
- Next: CuriosityDaemon → epistemics integration

### 2026-05-05 UTC (session 1)

- Deleted 20 dead pkg/core packages, build clean
- Renamed TALOS_ → ORI_ across all pkg/ Go files
- Archived vuln.ai/ to ~/vuln.ai-archived/
- Committed all SLM eviction changes from last session

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

### 2026-04-28 UTC

- **Oracle fully migrated off GitHub Copilot SDK** → direct Anthropic API (HTTP/SSE, no daemon, no port 8090).
- `ANTHROPIC_API_KEY` added to systemd service envs. `GITHUB_MODELS_TOKEN` no longer needed for Oracle.
- **Prompt caching** wired — system prompt sent as `cache_control: ephemeral` block on all routes.
- **Extended thinking** live — heavy route 8K budget, research route 10K. Disable with `ORACLE_THINKING_*=0`.
- **Native tool use** wired — `oracle.ChatWithTools()` + `server_v2` tool path with proper OpenAI↔Anthropic conversion. `reqMsgsToOracle()` preserves `tool_call_id` through the pipeline.
- **Batch API** ready — `pkg/oracle/batch.go` with `SubmitBatch/GetBatch/FetchResults/PollUntilDone`. Studio Jobs integration pending.
- **`.ori` skills restored** — `pkg/oracle/skills.go` loads `oricli_core/skills/*.ori`, trigger-matches against query, injects as system prompt overlay.
- **ORI Code unblocked** — fixed missing `await` on `buildTurn()` in `index.tsx` + fixed `tool_call_id` pipeline bug. Full local tool loop working (read, write, shell, git).
- All docs and personas updated — no remaining Copilot SDK references anywhere.

### 2026-04-21 UTC

- Oracle model selection now static (env/defaults). Cache file at `/tmp/oracle_model_cache.json` is observability only.

### 2026-05-08 UTC

- **Oracle primary runtime migrated from Anthropic to OpenAI** after substrate-integrity benchmarking.
- Active defaults: light `gpt-5.4-mini`, heavy `gpt-5.5`, research `gpt-5.5`; public model remains `oricli-oracle`.
- `OPENAI_API_KEY` is now required for live Oracle chat/vision/tool routes. Both `oricli-api.service` and `oricli-backbone.service` have systemd drop-ins at `/etc/systemd/system/<service>.d/openai.conf`.
- Anthropic remains only in `pkg/oracle/batch.go` legacy batch helper; no active callers observed during migration.
- Verified live after deploy: `/v1/modules` count `40`, light chat routed to `gpt-5.4-mini`, research/heavy smoke routed to `gpt-5.5`.
- Follow-up same day: active OpenAI adapter moved from Chat Completions to the Responses API under the same `oricli-oracle` public contract. Streaming now consumes `response.output_text.delta`; tools use Responses function-call items; vision uses Responses image input.

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
