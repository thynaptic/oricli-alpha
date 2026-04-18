# Therapy Extraction Plan

**Document Type:** Repo Governance  
**Status:** Draft  
**Date:** 2026-04-07  

---

## Purpose

This document defines the first concrete extraction target from the public repo:

- `pkg/therapy/`

The goal is to move the therapeutic cognition implementation behind a private boundary without breaking:

- API routes in `pkg/api/server_v2.go`
- generation integration in `pkg/service/generation.go`
- CLI status views in `pkg/cli/`
- adjacent packages that consume mastery or schema signals

---

## Why Therapy Goes First

`pkg/therapy/` is the best first extraction target because it is:

- high IP value
- clearly documented in [THERAPEUTIC_COGNITION.md](/home/mike/Mavaia/docs/THERAPEUTIC_COGNITION.md)
- internally cohesive
- smaller and cleaner than moving all of `pkg/cognition/` first

Files in scope:

- `pkg/therapy/abc.go`
- `pkg/therapy/chain_analysis.go`
- `pkg/therapy/distortion.go`
- `pkg/therapy/helplessness.go`
- `pkg/therapy/mastery_log.go`
- `pkg/therapy/session_supervisor.go`
- `pkg/therapy/skills.go`
- `pkg/therapy/types.go`

---

## Current Public-Repo Dependents

### API layer

`pkg/api/server_v2.go` currently depends on:

- `therapy.SkillRunner`
- `therapy.DistortionDetector`
- `therapy.ABCAuditor`
- `therapy.ChainAnalyzer`
- `therapy.SessionSupervisor`
- `therapy.EventLog`
- `therapy.HelplessnessDetector`
- `therapy.MasteryLog`
- `therapy.AttributionalRetrainer`
- `therapy.SchemaLearnedHelplessness`

### Generation layer

`pkg/service/generation.go` currently depends on:

- `therapy.DistortionType`
- distortion constants like `AllOrNothing`, `FortuneTelling`, etc.
- `therapy.HelplessnessDetector`
- `therapy.InferTopicClass`
- `therapy.MasteryLog`
- therapy augmentation and mastery-recording behavior

### CLI layer

`pkg/cli/commands.go` and `pkg/cli/client.go` depend on therapy endpoints, not package internals.

This is good: CLI mostly survives unchanged if the HTTP API stays stable.

### Other package dependents

Current cross-package uses found:

- `pkg/hopecircuit/` -> `therapy.MasteryLog`
- `pkg/api/server_v2.go`
- `pkg/service/generation.go`

That means the real hard dependencies are concentrated and tractable.

---

## Recommended Extraction Shape

Do **not** make the public repo import a private repo directly everywhere.

Instead use a boundary like this:

### Private implementation module

Move the full `pkg/therapy/` implementation into a private/internal module or repo.

### Public interface layer

Leave a thin public boundary in the platform repo, either:

1. `pkg/therapyapi/` for interfaces and lightweight DTOs, or
2. a narrower retained `pkg/therapy/` package that becomes interfaces-only

Recommended approach:

- keep the public API surface small
- move implementation, detection logic, and regulation internals private
- retain only the minimum types/interfaces needed for wiring

---

## Interface Boundary

The public side should only know about capabilities, not implementation detail.

Suggested public interfaces:

### Event log and telemetry

- `TherapyEvent`
- `SessionFormulation`
- `SessionReport`

### Runtime capabilities

- `SkillRunner`
- `DistortionDetector`
- `ABCAuditor`
- `ChainAnalyzer`
- `SessionSupervisor`
- `HelplessnessDetector`
- `MasteryStore`

### Helper enums / contracts

- `DistortionType`
- `SkillType`
- `SchemaName`

Avoid exposing:

- regex heuristics
- intervention logic
- schema thresholds
- repair mappings
- retraining prompt construction
- detector internals

Those belong private.

---

## Migration Phases

### Phase A — Stabilize interfaces

1. Identify the exact types consumed outside `pkg/therapy/`
2. Move those contracts into a stable boundary package or thin public layer
3. Keep method names and response shapes stable

### Phase B — Isolate implementation

1. Move detector and supervisor internals to the private module
2. Keep constructors or factories on the public side only if needed
3. Replace direct type construction with interface-based wiring

### Phase C — Preserve API compatibility

1. Keep `/v1/therapy/*` routes unchanged
2. Keep CLI output unchanged
3. Keep generation hooks unchanged at the interface level

### Phase D — Clean follow-on imports

1. Update `pkg/hopecircuit/` to depend on the public mastery interface, not raw implementation
2. Update any generation helpers to depend on interfaces or DTOs

---

## Risks

### Tight type coupling

`pkg/api/server_v2.go` uses many concrete therapy types directly.

Mitigation:

- define explicit interfaces/DTOs first
- avoid moving code before the surface is stabilized

### Generation coupling

`pkg/service/generation.go` uses therapy constants and helper functions directly.

Mitigation:

- move constant/enums to the public boundary if they must remain shared
- keep the actual detector logic private

### Adjacent packages

`pkg/hopecircuit/` consumes `MasteryLog`.

Mitigation:

- introduce a small mastery interface
- do not let adjacent packages reach into full therapy implementation details

---

## What To Keep Public

Safe to keep public:

- therapy HTTP routes
- therapy response DTOs
- CLI commands that consume therapy endpoints
- minimal type contracts needed by public packages

Not safe to keep public:

- detector internals
- schema logic
- belief-chain audit prompts
- repair mappings
- regulation heuristics
- helplessness detection logic
- mastery evidence logic

---

## Immediate Next Step

Before moving code, do this:

1. make a concrete list of exported `pkg/therapy` symbols used outside the package

That gives the exact interface surface we need to preserve during extraction.

