# Edge Surfaces Classification

**Document Type:** Repo Governance  
**Status:** Active  
**Date:** 2026-04-06  

---

## Purpose

This document classifies the remaining "edge" surfaces that do not sit cleanly inside the obvious public or private namespaces.

Primary targets:

- `pkg/curator/`
- `pkg/oracle/`
- `cmd/` demo binaries

Use this with:

- [IP_BOUNDARY.md](/home/mike/Mavaia/docs/IP_BOUNDARY.md)
- [IP_SURFACES.md](/home/mike/Mavaia/docs/IP_SURFACES.md)
- [PUBLIC_ALLOWLIST.md](/home/mike/Mavaia/docs/PUBLIC_ALLOWLIST.md)
- [SERVICE_SURFACES.md](/home/mike/Mavaia/docs/SERVICE_SURFACES.md)

---

## pkg/curator

### Classification

`pkg/curator/` is **private-default**.

### Why

Even though it looks like ordinary model operations code, it implements:

- sovereign model benchmarking
- usage-tier recommendation logic
- model selection and fallback policy
- constitutional pass/fail scoring

That is not generic deployment plumbing. It is internal decision logic about how ORI selects and ranks models.

### Current files

- `pkg/curator/curator.go`
- `pkg/curator/suite.go`

### Working rule

Do not publish `pkg/curator/` by default.

---

## pkg/oracle

### Classification

`pkg/oracle/` is **private-default**.

### Why

It implements:

- high-complexity escalation routing
- privileged CLI-based fallback and injection behavior
- oracle answer formatting and override semantics
- routing logic for when ORI bypasses or augments local reasoning

That is internal orchestration logic, not generic transport.

### Current files

- `pkg/oracle/oracle.go`
- `pkg/oracle/router.go`

### Working rule

Do not publish `pkg/oracle/` by default.

---

## cmd/

### Classification

`cmd/` is **public-default**, but demo binaries are **review-required**.

### Why

The directory mostly contains:

- application entrypoints
- operational binaries
- demos and experiments

Entry points such as:

- `cmd/backbone/main.go`
- `cmd/oricli-cli/main.go`
- `cmd/oricli-engine/main.go`

are public-default platform surfaces.

But demo binaries can leak internal concepts by:

- naming proprietary subsystems
- exercising private cognition flows
- embedding prompts or orchestration assumptions

### Review-required demos

Treat these as review-required before publishing:

- `cmd/chronos_demo/main.go`
- `cmd/dream_demo/main.go`
- `cmd/ghost_demo/main.go`
- `cmd/gosh_demo/main.go`
- `cmd/kernel_demo/main.go`
- `cmd/precog_demo/main.go`
- `cmd/safety_demo/main.go`
- `cmd/scaling_demo/main.go`
- `cmd/sentinel_demo/main.go`
- `cmd/sovereign_demo/main.go`

### Public-default command binaries

These are safe by default unless they absorb private logic later:

- `cmd/backbone/main.go`
- `cmd/oricli-cli/main.go`
- `cmd/oricli-engine/main.go`

### Working rule

For `cmd/`:

- app/runtime entrypoints are public-default
- demos are review-required
- if a demo materially teaches private system behavior, move it to private-default

---

## External Integration Docs

`docs/EXTERNAL_INTEGRATION.md` is **review-required**, not public-default.

### Why

It mixes:

- legitimate public API documentation
- internal cognitive module naming
- therapy and cognition route exposure
- system-behavior descriptions that reveal more than a normal public API reference should

### Working rule

Do not assume this doc is safe to publish in full without trimming or splitting.

---

## Immediate Working Rule

For the outer ring:

- `pkg/curator/` -> private-default
- `pkg/oracle/` -> private-default
- `cmd/` platform entrypoints -> public-default
- `cmd/` demos -> review-required
- `docs/EXTERNAL_INTEGRATION.md` -> review-required

