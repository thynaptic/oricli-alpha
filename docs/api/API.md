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

These are Oracle-grade reasoning primitives exposed as first-class endpoints. All run through the `oracle.Complete()` provider chain (Copilot→Gemini→Codex fallback). They require auth.

### `POST /audit/constitutional`

Runs the SCAI constitutional audit loop against a response.

Body:

```json
{
  "query": "original user query",
  "response": "draft response to audit",
  "max_cycles": 3
}
```

Returns `{ compliant, critique, revised, original, cycles }`.

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

Analyze an image via local vision models (llava/moondream). Requires Ollama running locally.

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
