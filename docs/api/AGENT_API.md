# ORI Agent Integration README

Status: active supporting doc

This is the handoff doc for external agents, app builders, and product clients that need to use ORI from outside the core repo.

Use this when you need to answer:

- how do I call ORI from another application?
- how do I make ORI act like the right product surface?
- how do I keep behavior aligned without writing a giant custom prompt?

For the fuller API reference, use:

- [API.md](/home/mike/Mavaia/docs/API.md) — Core backbone platform API
- [STUDIO_AGENT_API.md](/home/mike/Mavaia/oricli_core/docs/STUDIO_AGENT_API.md) — Studio-side workflows, pipelines, and email commands

## Core Rule

Do not treat ORI like “a model with a prompt.”

Treat ORI like a system with:

- a shared core identity
- product surface overlays
- working style profiles
- routing and tool permissions
- replaceable reasoning backends

That means external apps should usually pass:

- the right surface
- the right working style profile when needed
- the user’s actual task

Not:

- a giant custom persona prompt
- a whole new identity per application

## The Basic Integration Shape

**One key, anywhere:** the same `ori.<prefix>.<secret>` works for every client (web, mobile, IDE, MCP, automation). Use `X-Ori-Context`, profiles, and scopes to vary behavior — not multiple runtime keys per surface. Legacy `glm.*` tokens remain valid until rotated.

Most integrations should use:

- `POST /v1/chat/completions`
- `Authorization: Bearer ori.<prefix>.<secret>`
- `X-Ori-Context: <surface>`
- optional `profile`

Important:

- only use profiles that belong to the surface you are calling
- do not rely on hidden manifest names or internal lanes
- if you omit the surface, ORI stays on her default baseline

## Current Base URLs

Shared runtime:

```text
https://glm.thynaptic.com/v1
```

Local development (public gateway; same paths as production):

```text
http://localhost:8089/v1
```

## Authentication

Use Bearer auth (one token for all integrations):

```text
Authorization: Bearer ori.<prefix>.<secret>
```

Public runtime access is scope-based.

Examples:

- `runtime:chat`
- `runtime:email:send`
- `runtime:models`
- `runtime:spaces`
- `runtime:workspaces`

Failure behavior:

- missing or invalid key -> `401`
- valid key without the required scope -> `403`

## Surface Context

Set the surface explicitly.

Recommended header:

```text
X-Ori-Context: studio
```

Current surfaces:

- `studio`
- `home`
- `dev`
- `red`

The surface tells ORI:

- what tone shift is allowed
- what vocabulary fits
- what skills are allowed
- what product boundaries apply

Invalid surface values are ignored rather than promoted into a new public lane.

## Working Style Profiles

If you want ORI to lean into a specific lane, pass a profile.

If you do not need a specific lane, do not pass one. Let Ori stay on her default baseline for that surface.

Examples:

### Studio

- `studio_customer_comms`
- `studio_operations`
- `studio_meetings`
- `studio_research`
- `studio_knowledge`

### Home

- `home_companion`
- `home_planner`
- `home_notes`
- `home_research`

### Dev

- `dev_builder`
- `dev_architect`
- `dev_debugger`

### Red

- `ori_red`

If a profile does not belong to the chosen surface, ORI ignores it and stays on the default baseline.

## Minimal Example

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

## Streaming Example

```bash
curl -N https://glm.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer ori.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -H "X-Ori-Context: home" \
  -d '{
    "model": "oricli-oracle",
    "stream": true,
    "messages": [
      {"role": "user", "content": "Help me plan tomorrow without overloading it."}
    ]
  }'
```

## Model Rule

External apps should not usually decide ORI’s whole identity through model choice.

Current runtime direction:

- `oricli-oracle` is the default strong reasoning lane
- plain chat requests now go Oracle-first by default
- ORI decides behavior through core identity, overlays, profiles, and allowed skills
- public integrations should treat `oricli-oracle` as the main product lane

If you need a safe default:

- use `model: "oricli-oracle"`

## Prompt Rule

Prefer:

- real surface context
- real profile selection
- short task-specific instructions

Avoid:

- giant persona prompts
- duplicating ORI’s identity in every app
- trying to recreate product behavior entirely in the system prompt

Good:

```text
Surface: studio
Profile: studio_customer_comms
Task: Draft a friendly but firm follow-up to a late-paying client.
```

Bad:

```text
You are a hyper-detailed sovereign AI assistant with all business, home, dev, and emotional support capabilities...
```

## How To Think About External Apps

If you are plugging ORI into another application, decide:

1. what surface is this closest to?
2. does it need a working style?
3. what tools or permissions should it have?
4. what should stay hidden?

That keeps ORI aligned instead of letting every app become its own personality fork.

## Product-Key Reality

Trusted first-party products can self-register with `POST /v1/app/register`.

This is an internal bootstrap path, not a public self-serve key minting route. It requires the shared `registration_token` configured on the ORI backbone for first-party Thynaptic products.

Current behavior:

- `ORI Home` receives `runtime:chat`, `runtime:email:send`, `runtime:models`, `runtime:spaces`, and `runtime:workspaces`
- `ORI Studio` and `ORI Mobile` receive `runtime:chat`, `runtime:email:send`, and `runtime:models`
- `ORI Dev` receives `runtime:chat` and `runtime:models`

Product data can also be tenant-scoped.

Current example:

- ORI Home Spaces belong to the authenticated tenant key
- one Home install cannot see another install's Spaces

Trusted build agents can use a narrower bootstrap path:

- `POST /v1/agent/register`
- auth format: `Authorization: Bearer agb.<prefix>.<secret>`

That route is meant for agent-safe first-party bootstrap only. It can mint a normal product key for an approved app, but it does not expose the shared internal registration token and it does not grant runtime access on its own.

## Product Examples

### If the app feels like a business operator tool

- use `studio`

### If the app feels personal or household

- use `home`

### If the app is for coding, architecture, or technical work

- use `dev`

### If the app is security-specific

- use `red`

## Related Docs

- [ORI_CORE_ARCHITECTURE.md](/home/mike/Mavaia/docs/ORI_CORE_ARCHITECTURE.md)
- [SKILLS.md](/home/mike/Mavaia/docs/SKILLS.md)
- [REASONING.md](/home/mike/Mavaia/docs/REASONING.md)
- [PRODUCTS.md](/home/mike/Mavaia/docs/PRODUCTS.md)
