# ORI API Reference

Status: active supporting doc

This is the current platform API reference for ORI.

Use this doc when you need:

- the main base URLs
- authentication rules
- the primary endpoint groups
- the current integration model

If you need the external-agent handoff, use:

- [AGENT_API.md](/home/mike/Mavaia/docs/AGENT_API.md)

If you need deeper implementation reality, inspect:

- `pkg/api/server_v2.go`

## Current API Model

ORI exposes an OpenAI-compatible chat surface plus ORI-specific endpoints for:

- goals
- ingestion
- learning/mastery compilation
- quest scaffolding
- behavioral reinforcement
- documents
- shares
- identity/profile control
- enterprise knowledge
- images
- selected operational/admin functions

The API should be read through the current architecture:

- Ori Core handles identity, memory, routing, permissions, and product behavior
- product surfaces are selected by explicit context
- working style profiles shape the lane
- Oracle is the default strong reasoning path
- public integrations should treat `oricli-oracle` as the normal user-facing default

## Base URLs

Shared runtime:

```text
https://glm.thynaptic.com/v1
```

Local development (typical split stack):

```text
http://localhost:8089/v1   # public gateway (G-LM) — what apps and proxies should call
http://localhost:8088/v1   # cognitive backbone (Mavaia) — localhost-only; do not expose publicly
```

Legacy docs and some clients may still reference:

```text
https://oricli.thynaptic.com
```

Treat `glm.thynaptic.com` as the preferred current shared runtime origin.

## Authentication

**One key, anywhere:** the same `ori.<prefix>.<secret>` authenticates every client (web, mobile, IDE, MCP, scripts). Use `X-Ori-Context`, profiles, and scopes to vary behavior — not multiple runtime keys per surface.

Protected routes use:

```text
Authorization: Bearer ori.<prefix>.<secret>
```

Legacy `glm.*` runtime keys remain valid until rotated.

Some public routes do not require auth, such as:

- `GET /health`
- `GET /ws`
- `GET /metrics`
- `GET /share/:id`

Admin routes require an admin-scoped key.

Runtime routes enforce scopes.

Common results:

- missing or invalid key -> `401`
- valid key without the needed scope -> `403`
- invalid surface or invalid profile -> ignored rather than treated as public errors

## Core Chat Endpoint

### `POST /chat/completions`

OpenAI-compatible chat with ORI-specific controls.

Useful request fields:

- `model`
- `messages`
- `stream`
- `profile`
- `tools`

Recommended additions for ORI:

- `X-Ori-Context: <surface>`
- `profile: <working_style>` when you want a specific lane

Important:

- Profiles are only honored when they match the active surface.
- If you send a profile without `X-Ori-Context`, ORI stays on the default baseline.
- Hidden/internal manifests are not part of the public API contract.

Example:

```bash
curl -s https://glm.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer ori.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -H "X-Ori-Context: studio" \
  -d '{
    "model": "oricli-oracle",
    "messages": [
      {"role": "user", "content": "Summarize what needs my attention this week."}
    ]
  }'
```

## Public / Utility Endpoints

### `GET /health`

Basic readiness probe.

### `GET /ws`

WebSocket endpoint for real-time state/event streaming.

### `GET /metrics`

Prometheus-compatible metrics endpoint.

### `GET /share/:id`

Render or return a shared artifact.

### `POST /app/register`

First-party app self-registration flow used for products like ORI Home.

This route is not public self-serve. It requires the shared internal `registration_token` configured on the ORI backbone for trusted Thynaptic products.

The app receives a product-scoped runtime key based on `app_name`.

Examples:
- `ORI Home` → `runtime:chat`, `runtime:email:send`, `runtime:models`, `runtime:spaces`, `runtime:workspaces`
- `ORI Studio` / `ORI Mobile` → `runtime:chat`, `runtime:email:send`, `runtime:models`
- `ORI Dev` → `runtime:chat`, `runtime:models`

Public developer keys should use the tenant admin key flow instead of `app/register`. Agents and external builders should not expect `app/register` to work without an internal registration token.

Registration is tenant-scoped by app and device.

Example tenant shape:

- `ORI Home` + `device_id: home-safe-a` -> `app:ori-home:home-safe-a`

### `POST /agent/register`

Agent-safe bootstrap flow for trusted build agents.

This route accepts `Authorization: Bearer agb.<prefix>.<secret>` and mints a normal product-scoped runtime key (`ori.*` preferred; older mints may still show as `glm.*`) for an approved first-party app without exposing the shared internal `registration_token`.

Bootstrap keys are intentionally narrow:

- they can only call `POST /agent/register`
- they must include `bootstrap:agent-register`
- they must also include `bootstrap:app:<normalized-app-name>` for the app they are allowed to mint
- they do not grant chat, spaces, email, or admin access by themselves

Example:

- a bootstrap key with `bootstrap:agent-register` + `bootstrap:app:ori-mobile` can mint an `ORI Mobile` runtime key
- the same bootstrap key cannot mint `ORI Home` unless it also includes `bootstrap:app:ori-home`

### Runtime Scopes

- `runtime:chat`
- `runtime:email:send`
- `runtime:models`
- `runtime:spaces`
- `runtime:workspaces`
- `runtime:*`

## Tenant-Scoped Product Data

Some product endpoints are tenant-scoped, not shared globally.

Current example:

- Spaces created through `ORI Home` belong to the authenticated tenant key
- a different Home install or tenant key cannot list, read, or use those Spaces
- legacy unowned Spaces are hidden until explicitly migrated

## Main Protected Endpoint Groups

### Learning Substrate

- `POST /learning/mastery/compile`
- `POST /quest/scaffold`
- `POST /behavior/create`
- `POST /behavior/event`
- `POST /behavior/state`
- `POST /context/momentum`
- `POST /procedure/compile`
- `POST /workflow/grammar/compile`
- `POST /actions/plan`
- `POST /conversation/harvest`
- `POST /temporal/coordinate`
- `POST /anticipation/prepare`
- `POST /codebase/task/plan`
- `POST /continuity/recover`
- `POST /execution/orchestrate`
- `POST /workgraph/compile`
- `POST /workgraph/answer`
- `POST /contextual-action/plan`
- `POST /signals/opportunities`
- `POST /intent/timeline`
- `POST /procedural/crystallize`
- `POST /memory/semantic/graph`
- `POST /resources/commitment/reason`

Internal/app-neutral `MaterialToMasteryCompiler` endpoint.

It converts supplied user-owned material into summary, concept graph, flashcards, practice drills, quizzes, mock assessments, misconception map, review cadence, mastery score, guided assistance mode, learning goal DAG, and cross-surface reinforcement hints.

Use `X-Ori-Context: learn` for the reusable learning substrate. Product clients still own capture, OCR, source storage, calendars, reminders, notifications, consent, and persistence.

`/quest/scaffold` is the app-neutral goal-to-operating-system transformer. It accepts a vague improvement goal plus optional notes, constraints, preferences, and surface context, then returns a named quest, adult role identity, first action, milestones, daily rhythm, workspace sections, progress model, review schedule, memory seeds, and Memory/Chronos/GoalDaemon/PAD integration hints.

Use `X-Ori-Context` to let the scaffold choose surface-appropriate language such as Home, Studio, or Dev. Product clients still own persistence, reminder delivery, community/accountability features, and confirmation before registering anything as a GoalDaemon DAG.

`/behavior/create`, `/behavior/event`, and `/behavior/state` expose the app-neutral Behavioral Reinforcement Substrate. They turn routines, habits, todos, goals, and shared goals into shame-safe state feedback loops: temporal contract, symbolic surface feedback, completion/miss/defer state updates, recovery suggestions, stability score, friction pattern, and Memory/Chronos/GoalDaemon/PAD/CALI integration hints.

Use `X-Ori-Context` to select labels such as household calm, workflow health, implementation momentum, or signal momentum. Product clients still own durable behavior storage, event logs, reminders, widgets, sync, shared-goal rooms, permissions, and user-configurable reinforcement intensity.

`/context/momentum` exposes the app-neutral Context-to-Momentum Engine. It turns messy notes, tasks, links, project fragments, user energy, and time availability into actionability buckets, future-self packets, next 5-minute and 30-minute moves, one preserved stepping stone, memory seeds, and Memory/Chronos/GoalDaemon integration hints.

Use `X-Ori-Context` to select surface hints for Home, Studio, or Dev. Product clients still own capture, storage, file movement, task creation, reminders, and confirmed archive/write actions.

`/procedure/compile` exposes the app-neutral Procedure Compiler. It turns observed workflows, transcripts, notes, tools, inputs, outputs, and outcome signals into SOPs, checklists, skill candidates, automation readiness, SCL TierSkills seed records, and GoalDAG/Chronos/Forge integration hints.

Use `X-Ori-Context` to shape surface language for Studio, Dev, Home, or future work surfaces. Product clients still own durable writes, skill registration, automation execution, permissions, approval gates, and any external system changes.

`/workflow/grammar/compile` exposes the app-neutral Workflow Grammar Compiler. It turns natural-language workflow intent, triggers, conditions, actions, tools, approvals, constraints, and exceptions into a trigger/action graph, variables, approval gates, failure modes, dry-run plan, readiness score, and Procedure/WorkGraph/Temporal/Forge/Memory integration hints.

Use `X-Ori-Context` to shape workflow language for Studio, Dev, Home, or future work surfaces. Product clients still own durable workflow registration, external system writes, schedules, notifications, execution, credentials, permissions, and approval UX.

`/actions/plan` exposes the app-neutral Sovereign Action Gateway planner. It turns user intent, action hints, available providers, scopes, approval policy, risk tolerance, and memory policy into ranked action candidates, recommended provider route, approval gate, policy labels, audit plan, dry-run instructions, memory plan, and WorkflowGrammar/WorkGraph/CALI/SCL/Chronos/Red integration hints.

This endpoint does not execute actions. Use it before any native tool, Zapier MCP, Make MCP, custom MCP, or external provider call. Product clients still own provider credentials, real execution, approval UX, durable action logs, notifications, schedules, and external mutations.

`/conversation/harvest` exposes the app-neutral Conversational Context Harvester. It turns meeting/chat transcripts, participant turns, intent, and context links into decisions, commitments, unresolved threads, follow-up packets, memory seeds, and Memory/Chronos/GoalDAG/Procedure integration hints.

Use `X-Ori-Context` to shape outputs for Studio, Dev, Home, or future work surfaces. Product clients still own note storage, memory writes, task creation, reminders, CRM/calendar updates, and confirmation before durable persistence.

`/temporal/coordinate` exposes the app-neutral Temporal Coordination Engine. It turns tasks, available attention windows, fixed events, energy, dependencies, and scheduling preferences into now/next/later buckets, schedule proposals, conflict detection, memory seeds, and Chronos/GoalDAG/Memory automation hints.

Use `X-Ori-Context` to shape outputs for Studio, Dev, Home, or future work surfaces. Product clients still own calendar writes, task mutations, reminders, notifications, conflict resolution, and confirmation before moving real commitments.

`/anticipation/prepare` exposes the app-neutral Ambient Anticipation layer. It turns upcoming situations, intent, participants, context signals, preferences, and recent outcomes into readiness scoring, prep packets, missing context, suggested tone, safe next moves, memory seeds, and Memory/Chronos/Conversation/Temporal integration hints.

Use `X-Ori-Context` to shape outputs for Studio, Dev, Home, or future work surfaces. Product clients still own email, calendar, CRM, memory, notification, task writes, and confirmation before durable or external actions.

`/codebase/task/plan` exposes the app-neutral Codebase-Resident Task Agent planner. It turns developer intent, repo area, file/symbol signals, constraints, known risks, and test commands into scoped work packets, file ownership proposals, risk flags, verification steps, delegation hints, memory seeds, and Procedure/Temporal/Memory/Forge integration hints.

Use `X-Ori-Context: dev` for technical builder surfaces. Product clients and agent runtimes still own actual file reads, edits, tests, commits, deployment, permission checks, and protection of unrelated user changes.

`/continuity/recover` exposes the app-neutral Continuity Recovery Engine. It turns previous sessions, artifacts, decisions, commitments, open loops, intent, and project context into a compact recovered thread, context packets, decision/commitment logs, open-loop state, suggested continuation, memory seeds, and Memory/Chronos/Conversation/Temporal/Procedure hints.

Use `X-Ori-Context` to shape restart language for Dev, Studio, Home, or future surfaces. Product clients still own durable memory writes, project snapshots, document/task updates, timelines, notifications, and source-of-truth storage.

`/execution/orchestrate` exposes the app-neutral Intent-First Execution Orchestrator. It turns goal/intent, task state, blockers, dependencies, energy, available time, and recent signals into a momentum score, next-best move, next options, blocked-because reasoning, dependency edges, memory seeds, and Continuity/Temporal/Procedure/Memory hints.

Use `X-Ori-Context` to shape execution language for Dev, Studio, Home, or future surfaces. Product clients still own issue/task mutations, project board writes, scheduling, assignment, notifications, and external execution.

`/workgraph/compile` exposes WorkGraph v0. It turns messy operator context, notes, conversations, and work items into typed work-state objects: jobs, tasks, decisions, owners, deadlines, blockers, approvals, notes, follow-ups, and metrics, plus graph edges, an operator pulse, memory seeds, and Continuity/Execution/Conversation/Temporal/Procedure hints.

`/workgraph/answer` exposes Ambient Answers over supplied WorkGraph state. It answers questions like “what is stuck?”, “what did I promise?”, “what needs approval?”, “who owns this?”, and “what should I handle first?” from the provided graph only.

Use `X-Ori-Context` to shape WorkGraph language for Studio, Dev, Home, or future surfaces. Product clients still own durable graph storage, workspace UI, dashboards, permissions, notifications, task/document writes, and all external system mutations.

`/contextual-action/plan` exposes the Contextual Action Fabric. It turns an entity, objective, surface context, available tools, evidence, signals, and constraints into an entity profile, evidence acquisition plan, fit/confidence score, governed action recommendations, reusable Skill Function candidate, memory seeds, and WorkGraph/Execution/Procedure/Memory/Temporal hints.

`/signals/opportunities` exposes the Signal Opportunity layer. It turns entity-bound signals, context, objective, and optional timing windows into ranked opportunities, a handle-first recommendation, watchlist candidates, memory seeds, and Contextual Action/Temporal/WorkGraph hints.

Use `X-Ori-Context` to shape Clay-derived primitives for Studio, Dev, Red, Home, Growth, or future surfaces. Product clients still own provider calls, paid enrichment, durable watches, CRM updates, outreach, notifications, budgets, audit logs, and approval gates.

`/intent/timeline` exposes the Intent Timeline. It turns work events, artifacts, decisions, constraints, outcomes, and open loops into preserved intent moments, detected intent shifts, rationale trails, current-intent state, continuity packets, memory seeds, and Continuity/WorkGraph/Procedure/Memory/Temporal hints.

`/procedural/crystallize` exposes the Procedural Crystallizer. It turns repeated workflow runs, triggers, steps, tools, pain points, inputs, outputs, and outcome signals into pattern readiness, candidate procedures, skill candidates, automation readiness, next-observation plans, memory seeds, and Procedure/Skills/WorkGraph/Memory/Temporal/Forge hints.

`/memory/semantic/graph` exposes the Semantic Memory Graph. It turns loose captures, notes, existing node hints, tags, people, objects, source handles, and retrieval questions into ontology-free nodes, edges, soft clusters, recoverability scoring, retrieval moves, progressive-structure guidance, memory seeds, and Memory/WorkGraph/Continuity/Intent/Procedure hints.

`/resources/commitment/reason` exposes the Commitment-Aware Resource Reasoner. It turns scarce resource pools, proposed actions, explicit commitments, hidden-obligation context, decision questions, and drift events into resource reality, protected commitments, affected commitments, tradeoff options, least-disruptive repair, non-shaming permission language, memory seeds, and Memory/Chronos/WorkGraph/Temporal/Intent/Behavior hints.

Use `X-Ori-Context` to shape calm-software and commitment-clarity primitives for Studio, Dev, Home, Red, Growth, or future surfaces. Product clients still own durable writes, memory persistence, artifact/task updates, skill registration, automation execution, schedules, notifications, approvals, payments, bank/account sync, tax/debt/investment/legal advice, and all external mutations.

### Goals

- `GET /goals`
- `GET /goals/:id`
- `POST /goals`
- `PUT /goals/:id`
- `DELETE /goals/:id`

Use when you need long-running or tracked objective execution.

### Ingestion

- `POST /ingest`
- `POST /ingest/web`

Use when feeding text or web sources into ORI’s knowledge/memory systems.

### Documents

- `POST /documents/upload`
- `GET /documents`

Use for file upload and document listing.

### Enterprise Knowledge

- `POST /enterprise/learn`
- `GET /enterprise/learn/:job_id`
- `GET /enterprise/knowledge/search`
- `DELETE /enterprise/knowledge`

Use for namespace-scoped ingest/search workflows.

### Images

- `POST /images/generations`

### Shares And Feedback

- `POST /share`
- `POST /feedback`

### Identity / Profile

- `GET /sovereign/identity`
- `PUT /sovereign/identity`

This is still the historical endpoint naming. The current product language is “working style” and “profile,” but the route remains.

### Agent / Builder

- `POST /agents/vibe`

Natural-language agent creation path.

## Cognitive Capability Endpoints

These are Oracle-grade reasoning primitives exposed as first-class endpoints. All route through the Anthropic API via Oracle. They require auth.

### `POST /audit/constitutional`

Runs the legacy explicit SCAI constitutional audit against a supplied draft.

Runtime chat no longer depends on visible post-generation correction. The current
chat path builds a SCAI constraint contract before generation, then uses structural
output gates and, for non-streaming risky responses, regeneration under a tighter
contract before returning the final answer.

Body:

```json
{
  "query": "original user query",
  "response": "draft response to audit",
  "max_cycles": 3
}
```

Returns `{ compliant, critique, revised, original, cycles }` for compatibility with
older audit clients. New product surfaces should prefer constraint-native generation
instead of showing user-visible correction badges or patches.

`max_cycles` defaults to 3, capped at 5. The loop stops early if no violations are found.

### `POST /reasoning/self-play`

Adversarial multi-vector self-play. Attacks the candidate answer from multiple reasoning vectors and returns a hardened result.

Body:

```json
{
  "candidate": "answer to stress-test",
  "references": ["optional supporting context"]
}
```

Returns full `SelfPlayResult`: `{ final_candidate, max_flaw_score, cycles, contradictions, opponent_finding, winning_vector, winning_rationale, attack_vectors }`.

### `POST /contradiction/detect`

Semantic contradiction scoring between two claims.

Body:

```json
{
  "claim_a": "first claim",
  "claim_b": "second claim"
}
```

Returns `{ score, contradicts }`. Score is `0.0–1.0`. `contradicts` is `true` when score ≥ 0.7.

### `POST /intent/normalize`

Normalizes raw user input against an optional mission plan context.

Body:

```json
{
  "input": "raw user message",
  "mission": { "goal": "...", "tasks": [] }
}
```

Returns `IntentNormalizationResult` including `corrected_input` and `ambiguity_score`.

### `POST /align`

Runs the alignment auditor on an output string against a named policy profile.

Body:

```json
{
  "output": "text to audit",
  "policy": "standard"
}
```

`policy` accepts `strict`, `standard`, or `permissive`. Defaults to `standard`.

Returns `{ compliant, corrected, violations, policy }`.

### `POST /vision/analyze`

Analyze an image via Oracle's vision tier (`oricli-oracle`). Calls `glm.thynaptic.com/v1` with OpenAI vision message format.

Body:

```json
{
  "image_url": "https://...",
  "image_base64": "<base64>",
  "image_path": "/path/on/server",
  "prompt": "optional context prompt",
  "save_memory": false
}
```

Returns `{ description, tags, model }`. When `save_memory: true` and `MemoryBank` is available, the result is written as a `ProvenanceSeen` memory fragment.

## Surface And Profile Guidance

If you are integrating ORI into a product client or external app:

- set the surface explicitly with `X-Ori-Context`
- choose a profile only when you need a specific lane
- do not recreate ORI’s identity with giant system prompts

Useful surfaces:

- `studio`
- `home`
- `dev`
- `red`

## Current Safe Defaults

If you need a safe integration default:

- use `model: "oricli-oracle"`
- pass the right `X-Ori-Context`
- let Ori stay on the default baseline unless you genuinely need a working-style override

Important runtime behavior:

- plain chat requests now default to Oracle
- public integrations should use `oricli-oracle` unless Thynaptic documents another supported lane

## Important Reality

This doc is intentionally shorter than the older giant API references.

That is on purpose.

The current goal is:

- one practical platform reference
- one agent/app-builder handoff doc
- fewer sprawling docs that silently mix product, infra, cognition theory, and every endpoint ever exposed

If you need a missing endpoint, inspect:

- `pkg/api/server_v2.go` — Go backbone source
- [STUDIO_API.md](/home/mike/Mavaia/oricli_core/docs/STUDIO_API.md) — Studio-side proxy routes
