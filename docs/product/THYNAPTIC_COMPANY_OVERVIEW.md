# Thynaptic — Company Overview

> Last updated: 2026-04-20
> Audience: investors, partners, press, developer community

---

## What We Do

Thynaptic builds ORI — an intelligence layer for applications and the developers who build them.

You call the API. ORI thinks.

Not a model. Not a chatbot widget. An opinionated reasoning layer — with memory, context, multi-step planning, tool use, and domain-aware personas — available through a single endpoint. Developers get the cognitive infrastructure that normally takes months to assemble, ready to integrate in an afternoon.

---

## The Problem

Every team building an AI-powered product faces the same hidden tax: the model is the easy part.

The hard part is everything around it — maintaining conversation context across sessions, routing the right query to the right reasoning depth, handling tool calls cleanly, building a persona that stays consistent, managing memory without bloating the prompt. OpenAI and Anthropic give you a capable model. They hand you a blank canvas and a brush and wish you luck.

Most teams end up reinventing the same infrastructure. Memory stores, retrieval layers, session management, fallback logic, agent routing — built differently at every company, tested poorly, and rebuilt when something breaks.

---

## What ORI Is

ORI is the layer between your application and the model.

It handles the infrastructure teams keep rebuilding: session-persistent reasoning, multi-turn memory, agent profiles that constrain behavior by task type, dynamic routing between fast and deep reasoning modes, tool orchestration, and a swarm layer for multi-agent coordination when a single pass isn't enough.

The model underneath is swappable. The reasoning architecture is not.

ORI is accessed via a clean, OpenAI-compatible REST API. If your app already calls a chat completions endpoint, the integration surface is familiar. What changes is what happens on the other side of that call.

---

## Proof of Work

We didn't design ORI for a whitepaper. We built it to power our own products. Every surface below runs on the same API your integration would call:

**ORI Studio** — AI operator for small businesses. Automates invoices, client follow-ups, scheduling, and weekly recaps through a Jobs-based interface. The brief: *ORI knows my business and handles it when I need her to.*

**ORI Home** — Resolution Engine for the mental load of modern life. Turns chaos into a single Active Pin — one thing, perfectly timed, with a resolution already staged. Ships as an Electron desktop app and a web SaaS. Built for the WFH parent who needs a partner that handles the logistics, not another tool to manage.

**ORI Code** — Terminal UI for developers. Bun-powered, Ink-rendered, direct API connection. A coding agent for people who live in the console.

**ORI Stone** — Hearthstone game analyst. Reads Power.log in real time. Delivers turn-by-turn fault detection, trade evaluation, missed lethal identification, and tempo analysis with the precision of a competitive coach.

**Mise by ORI** — Culinary intelligence for serious home cooks. Sequenced mise en place, flavor diagnostics (Salt / Fat / Acid / Heat), technique coaching, multi-component timing sync, ingredient substitution — available mid-cook, not just in a recipe card.

**vuln.ai** — Red team and security surface. Adversarial analysis, attack-surface review, and hardening guidance powered by a dedicated security-mode agent profile.

**G-LM** — Enterprise LLM gateway. OpenAI-compatible API in front of any model backend, with policy enforcement, deterministic routing, tenant isolation, model allowlists, and full audit trails.

These are not demos. They are production applications with real users, and they are the reason ORI's API is battle-tested across wildly different domains.

---

## The API

ORI exposes an OpenAI-compatible chat completions endpoint with extensions for session management, agent selection, and reasoning depth.

```
POST https://glm.thynaptic.com/v1/chat/completions
Authorization: Bearer <your-key>
```

Existing integrations require minimal changes. Teams already using the OpenAI SDK can point at ORI's base URL and get session memory, agent routing, and tool orchestration without rewriting their call sites.

Agent profiles let callers declare intent — `ori_code`, `smb_assistant`, `home_companion`, `ori_red` — so ORI calibrates its behavior, persona, and allowed toolset to the task. No prompt engineering required to change how ORI shows up.

An SDK is on the roadmap. The API comes first.

---

## Technical Foundation

ORI's backbone is a Go-native reasoning engine — 269+ cognitive modules, a swarm orchestration layer with Contract Net bidding and shared blackboard state, and a session management layer with 30-minute TTL pooling built directly on the Anthropic API. Reasoning modes include Chain-of-Thought, Tree-of-Thought, and Monte Carlo Tree Search, routed dynamically by query complexity.

The architecture is designed for reliability under real usage: session pooling eliminates cold-start latency across turns, agent profiles enforce capability boundaries without duplicating module logic, and the swarm layer handles multi-agent coordination when a single-pass response isn't sufficient.

Oracle, the high-capability reasoning tier, routes through GitHub Copilot's model catalog with automatic model selection keyed to query tier and model availability.

---

## Where We're Going

ORI is production today. The developer-facing API is the immediate focus — cleaner docs, stable versioning, key management, usage dashboards.

The SDK follows: a library that lets developers embed ORI's session management, agent routing, and tool orchestration locally, without calling the hosted API for every turn. The same intelligence, optionally closer to the application.

The product line continues to expand. New surfaces validate new domains. Each one tightens the API, surfaces new capability requirements, and produces documented integration patterns that become first-class SDK features.

---

## Company

Thynaptic is the research and product studio behind ORI. We are a small team building fast, with a bias toward shipping over planning and real applications over benchmarks.

ORI is live. The API is open. The work is ongoing.

---

*For API access, partnerships, or press inquiries: thatnotiondude@gmail.com*
