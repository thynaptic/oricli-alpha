# IP Surfaces Map

**Document Type:** Repo Governance  
**Status:** Active  
**Date:** 2026-04-06  

---

## Purpose

This document turns the `/docs` corpus into an actionable map for code visibility decisions.

Rule:

- if a doc describes internal cognition, reasoning, regulation, memory, or control-loop behavior
- then the code implementing that behavior is presumptively private

Use this together with [IP_BOUNDARY.md](/home/mike/Mavaia/docs/IP_BOUNDARY.md).

---

## Core Private-Signal Docs

### Reasoning

- [REASONING.md](/home/mike/Mavaia/docs/REASONING.md)
- [MCTS_REASONING.md](/home/mike/Mavaia/docs/MCTS_REASONING.md)
- [TR-2026-02-Go-Native-Reasoning-Architecture.md](/home/mike/Mavaia/docs/TR-2026-02-Go-Native-Reasoning-Architecture.md)

Primary code surfaces:

- `pkg/cognition/`
- `pkg/core/reasoning/`
- `pkg/core/metareasoning/`
- `pkg/service/reasoning_*.go`
- `pkg/service/generation.go`

### Therapeutic cognition

- [THERAPEUTIC_COGNITION.md](/home/mike/Mavaia/docs/THERAPEUTIC_COGNITION.md)
- [AGLI_Phase_II.md](/home/mike/Mavaia/docs/AGLI_Phase_II.md)

Primary code surfaces:

- `pkg/therapy/`
- `pkg/service/generation.go`
- `pkg/service/safety*.go`
- `pkg/metacog/` when it triggers or shapes therapy flows

### Safety and boundary defense

- [SECURITY.md](/home/mike/Mavaia/docs/SECURITY.md)
- [EXTERNAL_INTEGRATION.md](/home/mike/Mavaia/docs/EXTERNAL_INTEGRATION.md) when it exposes internal safety or cognition modules
- [SMB_DEVELOPER_GUIDE.md](/home/mike/Mavaia/docs/SMB_DEVELOPER_GUIDE.md) when it documents internal protection layers

Primary code surfaces:

- `pkg/safety/`
- `pkg/service/safety*.go`
- `pkg/service/holistic_safety.go`
- `pkg/service/tenant_constitution.go`

### Memory and internal state

- [MEMORY_ARCHITECTURE.md](/home/mike/Mavaia/docs/MEMORY_ARCHITECTURE.md)
- [POCKETBASE_MEMORY.md](/home/mike/Mavaia/docs/POCKETBASE_MEMORY.md)

Primary code surfaces:

- `pkg/service/memory*.go`
- `pkg/service/memory_bank.go`
- `pkg/service/memory_graph.go`
- `pkg/service/state_memory_tools.go`
- `pkg/cognition/chronos.go`
- `pkg/cognition/relational_context.go`
- `pkg/cognition/belief_state.go`

### Epistemic and self-regulation

- [EPISTEMIC_HYGIENE.md](/home/mike/Mavaia/docs/EPISTEMIC_HYGIENE.md)
- [SELF_LAYER.md](/home/mike/Mavaia/docs/SELF_LAYER.md)
- [SOVEREIGN_STACK.md](/home/mike/Mavaia/docs/SOVEREIGN_STACK.md)

Primary code surfaces:

- `pkg/cognition/epistemic*.go`
- `pkg/cognition/reflection*.go`
- `pkg/cognition/self_*.go`
- `pkg/cognition/supervision*.go`
- `pkg/cognition/substrate*.go`
- `pkg/service/introspection.go`
- `pkg/service/meta_evaluator.go`
- `pkg/service/holistic_safety.go`

### Broad internal architecture / system behavior

- [SMB_DEVELOPER_GUIDE.md](/home/mike/Mavaia/docs/SMB_DEVELOPER_GUIDE.md)
- [EXTERNAL_INTEGRATION.md](/home/mike/Mavaia/docs/EXTERNAL_INTEGRATION.md)

Primary code surfaces:

- treat as a review amplifier, not a sole source
- if these docs expose internal module names or routes tied to cognition internals, the backing code is private-default

---

## Public-Signal Docs

These docs usually point at publishable platform surfaces:

- [API.md](/home/mike/Mavaia/docs/API.md)
- [PRODUCTS.md](/home/mike/Mavaia/docs/PRODUCTS.md)
- [ORI_DEV_DEPLOY.md](/home/mike/Mavaia/docs/ORI_DEV_DEPLOY.md)
- [ORI_HOME_SPEC.md](/home/mike/Mavaia/docs/ORI_HOME_SPEC.md)
- [CHANGELOG.md](/home/mike/Mavaia/docs/CHANGELOG.md)
- [SECURITY.md](/home/mike/Mavaia/docs/SECURITY.md)
- [public_overview.md](/home/mike/Mavaia/docs/public_overview.md)

Typical backing code:

- `cmd/`
- `pkg/cli/`
- `pkg/core/http/`
- deployment scripts
- product shell wiring

---

## Package Classification

### Private-default now

- `pkg/cognition/`
- `pkg/therapy/`
- `pkg/core/reasoning/`
- `pkg/core/metareasoning/`
- `pkg/safety/`

### Public-default now

- `cmd/`
- `pkg/cli/`
- `pkg/core/http/`
- `scripts/`
- service files

### Review-required now

- `pkg/service/agent.go`
- `pkg/service/memory*.go`
- `pkg/service/semantic_understanding.go`
- `pkg/service/emotional_inference.go`
- `pkg/service/meta_evaluator.go`
- `pkg/service/holistic_safety.go`
- `pkg/curator/`
- `pkg/oracle/`

Rule:

- if a review-required package mostly implements behavior described in the private-signal docs, move it to private-default
- if it mostly transports, exposes, or operationalizes those capabilities, it can remain public or semi-public

---

## Fast Triage Heuristic

Ask two questions:

1. Which doc most directly explains this file?
2. Is that doc a private-signal doc or a public-signal doc?

If the answer is:

- private-signal doc -> private-default
- public-signal doc -> public-default
- multiple mixed docs -> review-required

---

## Immediate Next Audit Targets

Use this order:

1. `pkg/service/` files touched by reasoning, memory, or therapy docs
2. `pkg/safety/`
3. `pkg/curator/`
4. `pkg/oracle/`

That will catch most of the "not obviously cognition package, but still IP" surfaces.
