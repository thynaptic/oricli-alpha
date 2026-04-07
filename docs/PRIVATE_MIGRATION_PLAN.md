# Private Boundary Migration Plan

**Document Type:** Repo Governance  
**Status:** Draft  
**Date:** 2026-04-07  

---

## Purpose

This document turns the governance rules into an execution plan for separating public platform code from private ORI IP.

It is intentionally staged.

Do not try to move everything at once.

Use this with:

- [IP_BOUNDARY.md](/home/mike/Mavaia/docs/IP_BOUNDARY.md)
- [IP_SURFACES.md](/home/mike/Mavaia/docs/IP_SURFACES.md)
- [PUBLIC_ALLOWLIST.md](/home/mike/Mavaia/docs/PUBLIC_ALLOWLIST.md)
- [SERVICE_SURFACES.md](/home/mike/Mavaia/docs/SERVICE_SURFACES.md)
- [EDGE_SURFACES.md](/home/mike/Mavaia/docs/EDGE_SURFACES.md)
- [PRIVATE_EXTRACTION_CANDIDATES.md](/home/mike/Mavaia/docs/PRIVATE_EXTRACTION_CANDIDATES.md)

---

## Target End State

The repo should eventually have two clear layers:

### Public platform

Safe to publish:

- API transport and OpenAI-compatible surfaces
- CLI and admin plumbing
- browser runtime and tool execution stack
- product shells and deploy wiring
- public documentation

### Private ORI core

Not publishable:

- cognition and reasoning systems
- therapy and regulation systems
- safety and disclosure defense systems
- memory and internal state systems
- model-selection and oracle-routing systems
- internal orchestration heuristics

---

## Principle

The public repo should expose **interfaces and integration points**, not the crown-jewel implementations.

That means:

- keep public wrappers where needed
- move private logic behind internal package or module boundaries
- preserve API compatibility while reducing code exposure

---

## Phase 1 — Governance Freeze

### Goal

Stop accidental public leakage before any code movement.

### Actions

1. Treat these as internal-only in practice:
   - `pkg/cognition/`
   - `pkg/therapy/`
   - `pkg/core/reasoning/`
   - `pkg/core/metareasoning/`
   - `pkg/safety/`
   - `pkg/curator/`
   - `pkg/oracle/`

2. Do not casually commit changes to private-default files in public cleanup lanes.

3. Route public work into allowlisted namespaces first.

### Exit criteria

- team uses the governance docs as the default review lens
- private namespaces stop getting mixed into normal public cleanup

---

## Phase 2 — Boundary Labels In Repo

### Goal

Make the repo self-describing before moving code.

### Actions

1. Add package-level markers or short README notes to private namespaces.
2. Add a top-level repo note describing:
   - public platform surfaces
   - internal/private surfaces
3. Optionally add CI or lint checks later that flag edits touching private namespaces.

### Suggested scope

- `pkg/cognition/README.md`
- `pkg/therapy/README.md`
- `pkg/safety/README.md`
- `pkg/core/reasoning/README.md`
- `pkg/core/metareasoning/README.md`
- `pkg/curator/README.md`
- `pkg/oracle/README.md`

### Exit criteria

- any engineer opening the tree can tell which packages are private-default

---

## Phase 3 — Extract The Obvious Private Packages

### Goal

Move the clearest IP first, with the least coupling pain.

### First extraction targets

1. `pkg/therapy/`
2. `pkg/curator/`
3. `pkg/oracle/`

### Why these first

- smaller than `pkg/cognition/`
- cleaner boundaries
- high IP value
- lower blast radius than moving the entire reasoning engine first

### Strategy

- create a private module or private repo
- move implementation there
- keep thin public interfaces only if needed

### Exit criteria

- these packages no longer live in the public tree as full implementations

---

## Phase 4 — Extract The Core Private Engines

### Goal

Move the main reasoning and safety engines behind a private boundary.

### Targets

1. `pkg/cognition/`
2. `pkg/core/reasoning/`
3. `pkg/core/metareasoning/`
4. `pkg/safety/`

### Strategy

Do this in slices, not as a single move:

- reasoning dispatch and mode selection
- adaptive engines and planners
- search engines and evaluators
- safety gates and disclosure defenses

### Warning

This is the hardest phase.
Expect interface work, import churn, and temporary wrappers.

### Exit criteria

- public repo no longer contains the core reasoning/safety implementations

---

## Phase 5 — Split Mixed Service Layer

### Goal

Clean `pkg/service/` so it stops hiding private behavior under generic filenames.

### Private service targets

- `generation.go`
- `reasoning_*.go`
- `memory*.go`
- `semantic_understanding.go`
- `emotional_inference.go`
- `meta_evaluator.go`
- `introspection.go`
- `subconscious.go`
- `precog.go`
- `safety*.go`
- `tenant_constitution.go`
- `living_constitution.go`
- orchestration-heavy files like `agent.go`, `coordinator.go`, `swarm_*.go`

### Public service targets

Keep public:

- browser stack
- tool execution/planning wrappers
- document/web/code/product services that stay generic

### Strategy

- split interfaces from implementation
- leave public wrappers if APIs depend on them
- move private implementations behind internal boundaries

### Exit criteria

- `pkg/service/` is mostly public-facing orchestration and tooling
- private behavior is no longer smeared across generic service files

---

## Phase 6 — Review The Borderline Set

### Goal

Resolve the ambiguous remainder only after the obvious private code is fenced off.

### Review set

- `pkg/service/rag.go`
- `pkg/service/research.go`
- `pkg/service/rules.go`
- `pkg/service/sandbox.go`
- `pkg/service/availability.go`
- `pkg/service/budget.go`
- `pkg/service/identity_seed.go`
- `pkg/service/profile.go`
- `pkg/service/persona.go`
- `pkg/service/skills.go`
- `pkg/service/world_knowledge.go`
- `pkg/service/world_traveler.go`
- `pkg/service/intent.go`
- `pkg/service/classifier.go`
- `pkg/service/monitor.go`
- `pkg/service/metrics.go`
- demo binaries in `cmd/`
- `docs/EXTERNAL_INTEGRATION.md`

### Exit criteria

- every remaining surface is explicitly public or private

---

## Recommended Implementation Order

Do this order:

1. Phase 1: governance freeze
2. Phase 2: boundary labels
3. Phase 3: extract `pkg/therapy`, `pkg/curator`, `pkg/oracle`
4. Phase 4: extract reasoning + safety engines
5. Phase 5: split mixed `pkg/service`
6. Phase 6: review remainder

This order reduces risk and keeps momentum.

---

## What Not To Do

Do not:

- move everything in one giant refactor
- flatten public and private code back together in a new folder structure
- expose private logic through overly descriptive public wrappers
- treat private docs as public just because they are already in the repo

---

## Immediate Next Step

The next practical move should be:

1. add boundary labels / README markers to the private namespaces

That is the cheapest enforcement step and makes later extraction work easier.

