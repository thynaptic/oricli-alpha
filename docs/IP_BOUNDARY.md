# IP Boundary — Public vs Private Code

**Document Type:** Repo Governance  
**Status:** Active  
**Date:** 2026-04-06  

---

## Purpose

This document defines the default public/private boundary for the Mavaia / ORI codebase.

It exists because the repo currently mixes:

- public platform/runtime code
- proprietary cognition and therapeutic regulation logic
- local operator glue and legacy surfaces

The goal is to make classification fast and boring.

---

## Governing Principle

If DeepMind would not publish it, neither do we.

In practice:

- product shells, deployment, transport, CLI, docs, and admin plumbing are usually publishable
- cognition, reasoning, regulation, model-policy, orchestration heuristics, and safety-control logic are not

If a file materially teaches someone how ORI thinks, adapts, judges, routes, self-regulates, selects models, or protects its internal boundaries, treat it as **private / IP**.

---

## Crown-Jewel Anchors

These two documents define systems that are **private / IP** by default:

- [REASONING.md](/home/mike/Mavaia/docs/REASONING.md)
- [THERAPEUTIC_COGNITION.md](/home/mike/Mavaia/docs/THERAPEUTIC_COGNITION.md)

If a file directly implements the architectures, heuristics, routing, or regulation logic described in those docs, treat it as **private-default** unless explicitly allowlisted.

Other docs that strongly indicate private system behavior:

- `docs/MCTS_REASONING.md`
- `docs/MEMORY_ARCHITECTURE.md`
- `docs/POCKETBASE_MEMORY.md`
- `docs/EPISTEMIC_HYGIENE.md`
- `docs/SELF_LAYER.md`
- `docs/SOVEREIGN_STACK.md`
- `docs/TR-2026-02-Go-Native-Reasoning-Architecture.md`
- `docs/SMB_DEVELOPER_GUIDE.md`
- `docs/AGLI_Phase_II.md`

If a code path is the implementation target of one of those documents, assume `private-default` until proven otherwise.

---

## Classification Rule

Use this order:

1. If the file directly implements reasoning internals, therapeutic cognition internals, model-selection policy, or cognition behavior, it is `private-default`.
2. If the file is transport, CLI, auth, serving, deployment, or general product plumbing, it is `public-default`.
3. If the file exposes cognition behavior, policy, orchestration, or memory surfaces without clearly being core IP, it is `review-required`.

`private-default` does **not** mean "delete immediately."
It means:

- do not assume it belongs in the public repo
- do not casually commit changes to it
- require explicit review before publishing or open-sourcing

---

## Private-Default Namespaces

These areas are presumed proprietary.

### Reasoning internals

- `pkg/cognition/`
- `pkg/core/reasoning/`
- `pkg/core/metareasoning/`
- `pkg/service/reasoning_*.go`
- `pkg/service/generation.go`

Examples:

- `pkg/cognition/adaptive_engine.go`
- `pkg/cognition/reasoning_modes.go`
- `pkg/cognition/reasoning_engines.go`
- `pkg/cognition/self_discover.go`
- `pkg/cognition/sovereign.go`
- `pkg/cognition/mcts.go`
- `pkg/cognition/tot.go`
- `pkg/cognition/response_planner.go`
- `pkg/core/reasoning/mcts.go`
- `pkg/core/reasoning/multiagent.go`
- `pkg/core/metareasoning/chain.go`
- `pkg/core/metareasoning/evaluator.go`

### Therapeutic cognition internals

- `pkg/therapy/`

### Safety and disclosure defense internals

- `pkg/safety/`

Examples:

- `pkg/therapy/distortion.go`
- `pkg/therapy/skills.go`
- `pkg/therapy/abc.go`
- `pkg/therapy/chain_analysis.go`
- `pkg/therapy/session_supervisor.go`
- `pkg/therapy/types.go`

### Why these are private-default

These files directly encode:

- reasoning mode dispatch
- adaptive budget logic
- model selection and fallback policy
- search and deliberation policies
- self-reflection and verification loops
- therapeutic regulation mappings
- schema detection and intervention logic
- disclosure defense and anti-extraction logic
- safety gating and internal policy enforcement

That is the highest-value system behavior in the repo.

---

## Public-Default Namespaces

These areas are presumed safe to keep public unless they accidentally absorb private logic.

- `cmd/`
- `pkg/cli/`
- `pkg/core/http/`
- deployment/service files
- general docs and operational scripts

Examples:

- `cmd/oricli-cli/main.go`
- `pkg/cli/client.go`
- `pkg/core/http/server.go`
- `scripts/start_ori_dev.sh`
- `ori-dev-ui.service`
- `docs/ORI_DEV_DEPLOY.md`

### Why these are public-default

These files mostly implement:

- process startup
- API transport
- CLI ergonomics
- admin endpoints
- serving and deployment
- repo and product documentation

They matter operationally, but they do not define the crown-jewel cognition systems by themselves.

---

## Review-Required Areas

These sit between platform plumbing and core IP. They need a deliberate call.

- `pkg/service/agent.go`
- `pkg/service/memory_bank.go`
- `pkg/service/memory*.go`
- `pkg/service/semantic_understanding.go`
- `pkg/service/emotional_inference.go`
- `pkg/cognition/instructions.go`
- `pkg/metacog/`
- `pkg/sentinel/`
- `pkg/conformity/`

### Why these require review

These files often:

- expose cognition behavior externally
- shape system policy
- bridge internal reasoning into public-facing APIs
- embed heuristics that may be more proprietary than they first look

Rule: if a file changes model behavior, response policy, memory policy, or safety posture, treat it as `review-required` even if the package name sounds generic.
If it changes **cognition behavior or model-policy**, prefer `private-default`.

---

## Commit Policy

When reviewing changes:

### Public-default

- can be committed normally
- still review for secrets and accidental algorithm leakage

### Review-required

- commit only with explicit intent
- keep commits narrow and explain the behavioral change

### Private-default

- do not commit by default
- if already present in the repo, treat edits as sensitive
- prefer moving these surfaces into a private/internal boundary over time

---

## Working Heuristic

When in doubt, ask:

1. Does this file implement *how ORI thinks*?
2. Does this file implement *how ORI self-regulates*?
3. Does this file merely expose or transport those capabilities?

If the answer is:

- `1` or `2` -> `private-default`
- `3` -> `public-default` or `review-required`

---

## Immediate Practical Use

For current repo cleanup, use this default split:

### Private-default now

- all of `pkg/therapy/`
- all of `pkg/cognition/` unless explicitly allowlisted later
- all of `pkg/core/reasoning/`
- all of `pkg/core/metareasoning/`
- all of `pkg/safety/`
- any file outside those namespaces that changes reasoning flow, model defaults, cognition policy, or therapeutic regulation

### Public-default now

- `cmd/`
- `pkg/cli/`
- `pkg/core/http/`
- deployment/service/docs/scripts

### Review-required now

- `pkg/service/agent.go`
- `pkg/service/memory_bank.go`
- `pkg/cognition/instructions.go`
- any service layer that changes response policy, model defaults, or orchestration behavior

---

## Follow-On Work

This document is the policy anchor.

Follow-on work should:

1. add explicit allowlists for public files inside `pkg/cognition/` if needed
2. identify private code that should move into a private/internal repo or module
3. mark review-required files more precisely as public or private over time

---

## Doc-Derived IP Signals

The `/docs` tree is itself a useful classifier.

### Usually private-signal docs

These documents describe internal architecture, cognition, regulation, memory, or proprietary control loops:

- `docs/REASONING.md`
- `docs/THERAPEUTIC_COGNITION.md`
- `docs/MCTS_REASONING.md`
- `docs/MEMORY_ARCHITECTURE.md`
- `docs/POCKETBASE_MEMORY.md`
- `docs/EPISTEMIC_HYGIENE.md`
- `docs/SELF_LAYER.md`
- `docs/SOVEREIGN_STACK.md`
- `docs/TR-2026-02-Go-Native-Reasoning-Architecture.md`
- `docs/SMB_DEVELOPER_GUIDE.md`
- `docs/AGLI_Phase_II.md`
- `docs/EXTERNAL_INTEGRATION.md` when it reveals internal cognitive modules or therapeutic routes

### Usually public-signal docs

These are generally safe to publish:

- `docs/API.md`
- `docs/PRODUCTS.md`
- `docs/ORI_DEV_DEPLOY.md`
- `docs/ORI_HOME_SPEC.md`
- `docs/CHANGELOG.md`
- `docs/SECURITY.md`
- `docs/public_overview.md`

### Working rule

If a doc explains:

- how ORI reasons
- how ORI self-regulates
- how ORI stores or shapes internal cognition state
- how ORI detects, scores, or routes behavior internally

then code implementing it is presumptively private.
