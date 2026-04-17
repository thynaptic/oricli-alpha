# ORI API Guide

Status: active supporting doc

This file is the simpler external-facing guide for developers integrating with ORI.

It replaces the older “ORI Studio Developer Guide” framing that mixed live API usage with a large amount of internal stack and cognition doctrine.

For the fuller API reference, use:

- [API.md](/home/mike/Mavaia/docs/API.md)
- [AGENT_API.md](/home/mike/Mavaia/docs/AGENT_API.md)

## What This Guide Is For

Use this doc when you need the quick integration picture:

- base URL
- auth
- basic chat usage
- profile and surface hints
- what kind of API ORI is today

## Base URL

Production:

```text
https://glm.thynaptic.com/v1
```

Local/backbone development commonly runs through:

```text
http://localhost:8089/v1
```

## Authentication

Use a Bearer token:

```text
Authorization: Bearer glm.<prefix>.<secret>
```

## API Shape

ORI keeps an OpenAI-compatible chat surface, with a few ORI-specific controls layered in.

Main endpoint:

```text
POST /chat/completions
```

Useful ORI-specific fields:

- `profile`
  - choose a working style/profile
- `surface`
  - or send `X-Ori-Context` when applicable
- `stream`
  - SSE streaming

## Product Reality

ORI is not just a thin model wrapper.

The current runtime shape is:

- Ori Core for identity, memory, routing, and permissions
- surface overlays for Studio, Home, Dev, and Red
- profiles for working styles
- Oracle as the default reasoning lane
- local models for utility/fallback work

That means integrations should think in terms of:

- which surface am I in?
- which working style do I want?
- what does the user need done?

Not:

- which raw model is “the product”

## Minimal Chat Example

```bash
curl -s https://glm.thynaptic.com/v1/chat/completions \
  -H "Authorization: Bearer glm.<prefix>.<secret>" \
  -H "Content-Type: application/json" \
  -H "X-Ori-Context: studio" \
  -d '{
    "model": "oricli-oracle",
    "messages": [
      {"role": "user", "content": "Summarize what needs my attention this week."}
    ]
  }'
```

## Surface Examples

### Studio

- use `X-Ori-Context: studio`
- use a Studio working style profile when needed
- best for business operator flows

### Home

- use `X-Ori-Context: home`
- use a Home working style profile when needed
- best for personal and household help

### Dev

- use `X-Ori-Context: dev`
- use a Dev working style profile when needed
- best for technical and product-building flows

### Red

- use `X-Ori-Context: red`
- use `ori_red` where appropriate
- keep security-specific use explicit and bounded

## Working Styles

The preferred integration pattern is to choose a working style profile instead of injecting a giant ad-hoc system prompt.

That keeps:

- behavior more consistent
- products more coherent
- hidden/internal lanes out of public integrations
- prompt sprawl lower

See:

- [SKILLS.md](/home/mike/Mavaia/docs/SKILLS.md)
- [ORI_PROFILE_AND_SKILL_CURATION.md](/home/mike/Mavaia/docs/ORI_PROFILE_AND_SKILL_CURATION.md)

## Product Rule

If you are integrating ORI, treat Ori as the system and the models as the compute underneath.

That is the stable direction.
