# docs.thynaptic.com IA

Status: active supporting doc

This defines the first version of the human-focused developer docs site for:

- `docs.thynaptic.com`

This site should not replace:

- `dev.thynaptic.com`

Instead, the split is:

- `dev.thynaptic.com` = terse, agent-readable integration portal
- `docs.thynaptic.com` = human developer docs, guides, walkthroughs, and examples

## Purpose

The goal of `docs.thynaptic.com` is not to become a giant knowledge dump.

It should answer:

- what is ORI?
- how do I authenticate?
- how do I make my first request?
- how do surfaces and working styles actually work?
- how do I stream?
- how do I register a first-party app?
- what should a real integration look like?

## V1 Rule

Launch narrow.

Do not try to document every endpoint, every era, and every internal system all at once.

V1 should be enough for:

- a developer integrating ORI into an app
- a developer testing the API manually
- a developer wiring a first-party client

## Relationship To Existing Docs

Canonical source docs already exist in the repo:

- [public_overview.md](/home/mike/Mavaia/docs/public_overview.md)
- [AGENT_API.md](/home/mike/Mavaia/docs/AGENT_API.md)
- [API.md](/home/mike/Mavaia/docs/API.md)

`docs.thynaptic.com` should be built from these, not invented separately.

## Suggested Top-Level Navigation

V1 top nav:

- Overview
- Quickstart
- Guides
- API Reference
- Examples

Footer links:

- `dev.thynaptic.com`
- `glm.thynaptic.com/v1/health`
- ORI Studio

## V1 Information Architecture

### 1. Overview

Purpose:

- explain ORI in plain developer language
- explain the “one ORI, many surfaces” model
- orient the reader before they see raw API details

Page content:

- what ORI is
- how ORI differs from “just a model”
- surfaces
- working styles
- safe integration rule

Primary source:

- [public_overview.md](/home/mike/Mavaia/docs/public_overview.md)

### 2. Quickstart

Purpose:

- get a developer from zero to first successful request quickly

Page content:

- base URL
- auth format
- simplest `chat/completions` call
- streaming example
- safe defaults:
  - `model: "oricli-oracle"`
  - `X-Ori-Context`
  - optional `profile`

Primary sources:

- [API.md](/home/mike/Mavaia/docs/API.md)
- [AGENT_API.md](/home/mike/Mavaia/docs/AGENT_API.md)

### 3. Guides

Purpose:

- explain common integration patterns without making people infer them from raw reference pages

V1 guide pages:

- Authentication
- Surfaces and Working Styles
- Streaming Responses
- First-Party App Registration
- Choosing the Right Surface

Optional early guide:

- “When to use a profile”

### 4. API Reference

Purpose:

- concise human reference for the practical runtime surface

V1 reference pages:

- Health
- Models
- Chat Completions
- App Register
- Shares
- Identity / Working Style notes

Keep this practical.

Do not dump every historical endpoint into the public docs site.

Deep or unstable/internal groups can stay in repo docs until they are ready.

### 5. Examples

Purpose:

- show real integration shapes by use case

V1 example pages:

- Studio integration
- Home integration
- Dev integration
- bare ORI call without a surface
- streaming client example

Language targets:

- curl
- JavaScript / TypeScript
- Python

## Page-Level Recommendations

### Homepage

Should feel like:

- “build with ORI”
- not marketing fluff
- not agent-only shorthand
- not giant technical reference

Hero:

- one sentence on ORI as a shared intelligence runtime
- one CTA to Quickstart
- one CTA to API Reference

Below hero:

- 3 simple cards:
  - One ORI, many surfaces
  - Oracle-first runtime
  - Safe defaults for integration

### Quickstart Page

Must be scannable in under 60 seconds.

Ideal structure:

1. Base URL
2. Auth
3. First request
4. First streaming request
5. Surface and profile note

### API Reference Pages

Each page should include:

- endpoint
- auth requirement
- request shape
- response shape
- one example
- one note on safe usage

## What Should Stay Off docs.thynaptic.com For Now

Do not lead with:

- cognition theory
- daemon internals
- old Oricli-alpha architecture
- benchmark archaeology
- internal-only or protected skills
- every historical endpoint ever exposed

Those can remain in repo docs as deep reference.

## Tone

The docs site should feel:

- plain
- precise
- calm
- modern
- technical without sounding like a manifesto

Avoid:

- bunker-language
- sovereign theater
- giant walls of explanation
- “our model is magic” copy

## Recommended Build Sequence

### Phase 1

Ship the minimum viable docs site with:

- homepage
- quickstart
- auth
- chat completions
- surfaces and working styles
- streaming

### Phase 2

Add:

- app registration
- examples by product surface
- error handling
- FAQs for developers

### Phase 3

Add:

- SDK starter packages
- OpenAPI or generated schema references if helpful
- changelog / release notes

## Success Criteria

The site is ready when:

- a developer can make a first successful request in minutes
- a developer understands surface + profile without asking
- the docs do not contradict `dev.thynaptic.com`
- the docs do not require reading the repo to get started

## Next Build Artifacts

When implementation starts, create:

- docs site homepage copy
- page list / route map
- docs site design system or template choice
- first five pages as content files

