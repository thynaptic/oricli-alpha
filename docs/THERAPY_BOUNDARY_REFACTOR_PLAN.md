# Therapy Boundary Refactor Plan

**Document Type:** Repo Governance  
**Status:** Draft  
**Date:** 2026-04-07  

---

## Purpose

This document defines the refactor we should do **before** extracting `pkg/therapy/` behind a private boundary.

The immediate goal is not to move files yet.

The immediate goal is to:

- reduce concrete coupling
- preserve stable public contracts
- make the later extraction low-risk

Use this with:

- [THERAPY_EXTRACTION_PLAN.md](/home/mike/Mavaia/docs/THERAPY_EXTRACTION_PLAN.md)
- [THERAPY_INTERFACE_SURFACE.md](/home/mike/Mavaia/docs/THERAPY_INTERFACE_SURFACE.md)
- [PRIVATE_MIGRATION_PLAN.md](/home/mike/Mavaia/docs/PRIVATE_MIGRATION_PLAN.md)

---

## The Core Problem

Right now, several public packages depend directly on concrete `pkg/therapy` implementations.

That means extraction would currently break:

- API wiring in `pkg/api/server_v2.go`
- generation logic in `pkg/service/generation.go`
- mastery consumers like `pkg/hopecircuit/circuit.go`

So we need to split:

- **public contract**
- **private implementation**

---

## Target Boundary Shape

The public repo should keep a **thin therapy contract layer**.

That public layer should contain only:

### DTOs / payload shapes

- `TherapyEvent`
- `SessionFormulation`
- `SessionReport`
- `HelplessnessSignal`
- `DetectionResult`
- `DisputationReport`
- `ChainAnalysis`
- `SchemaPattern`
- `MasteryEntry`

### Enums / names

- `DistortionType`
- distortion constants
- `SchemaName`
- schema constants
- `SkillType`
- skill constants

### Interfaces

- `SkillRuntime`
- `DistortionRuntime`
- `ABCRuntime`
- `ChainRuntime`
- `SessionSupervisorRuntime`
- `EventLogRuntime`
- `HelplessnessRuntime`
- `MasteryRuntime`
- `AttributionRuntime`

### Minimal helpers

- `InferTopicClass` if we decide it must remain shared

Everything else should move private.

---

## Proposed Public Interfaces

These names are illustrative. We can tune them when we implement.

### Skill runtime

```go
type SkillRuntime interface {
	FAST(userMessage, priorResponse, currentDraft string, priorConfidence float64) SkillInvocation
	STOP(trigger, originalText string) SkillInvocation
}
```

### Distortion runtime

```go
type DistortionRuntime interface {
	Detect(text, anomalyType string) DetectionResult
}
```

### ABC runtime

```go
type ABCRuntime interface {
	Audit(query, proposedResponse string) DisputationReport
}
```

### Chain runtime

```go
type ChainRuntime interface {
	Record(query, response, anomalyID string, distortion DistortionType)
}
```

### Session supervisor runtime

```go
type SessionSupervisorRuntime interface {
	Formulation() SessionFormulation
	ForceFormulation() SessionFormulation
	RecordHelplessness()
	Close()
}
```

### Event log runtime

```go
type EventLogRuntime interface {
	Recent(n int) []*TherapyEvent
}
```

### Helplessness runtime

```go
type HelplessnessRuntime interface {
	Check(query, draft string) *HelplessnessSignal
}
```

### Mastery runtime

```go
type MasteryRuntime interface {
	Record(topicClass, query string, success bool)
	SuccessRate(topicClass string) float64
	RecentSuccesses(topicClass string, n int) []*MasteryEntry
	StatsByClass() map[string]map[string]int
}
```

### Attribution runtime

```go
type AttributionRuntime interface {
	Retrain(signal *HelplessnessSignal) string
}
```

---

## Refactor Order

### Step 1 — Hopecircuit first

`pkg/hopecircuit/circuit.go` should stop depending on concrete `*therapy.MasteryLog`.

Replace:

- `*therapy.MasteryLog`

With:

- a small mastery interface

Why first:

- it is the cleanest dependency to decouple
- it gives us a pattern for reducing concrete type dependence

---

### Step 2 — ServerV2 field types

In `pkg/api/server_v2.go`, change fields from concrete types to runtime interfaces where possible.

Current concrete examples:

- `*therapy.SkillRunner`
- `*therapy.DistortionDetector`
- `*therapy.ABCAuditor`
- `*therapy.ChainAnalyzer`
- `*therapy.SessionSupervisor`
- `*therapy.EventLog`
- `*therapy.HelplessnessDetector`
- `*therapy.MasteryLog`
- `*therapy.AttributionalRetrainer`

Goal:

- make `ServerV2` care only about capabilities, not implementations

---

### Step 3 — GenerationService field types

In `pkg/service/generation.go`, change therapy fields from concrete implementations to runtime interfaces where possible.

Keep shared DTOs/enums public.

Why:

- generation is the biggest long-term coupling point
- but once fields are interface-based, the implementation can move later

---

### Step 4 — Constructors/factories

Introduce a single boundary factory on the public side that returns the runtime interfaces needed by:

- API layer
- generation layer
- adjacent packages

That gives the later private extraction one place to plug in.

---

## What Stays Public

Keep public:

- therapy HTTP payload shapes
- therapy enum names used in responses
- route response contracts
- CLI compatibility via HTTP
- minimal interfaces and helper types

This preserves external behavior while shrinking implementation exposure.

---

## What Moves Private

Move private:

- regex detectors
- LLM fallback prompts
- schema thresholds
- repair logic
- intervention planning
- session formulation internals
- helplessness heuristics
- mastery persistence logic if we choose
- distortion correction mapping

That is the valuable part.

---

## Recommended First Code Change

If we start implementation, the first safest code move is:

1. introduce `MasteryRuntime` interface
2. update `pkg/hopecircuit/circuit.go` to depend on it

Why:

- smallest blast radius
- validates the extraction pattern
- improves boundary hygiene immediately

---

## Exit Criteria For Refactor Phase

The refactor phase is complete when:

- `pkg/api/server_v2.go` no longer stores concrete therapy implementations
- `pkg/service/generation.go` no longer depends on concrete therapy implementations for wiring
- adjacent packages use small interfaces instead of concrete `pkg/therapy` types where practical
- the remaining public therapy surface is mostly DTOs, enums, and interfaces

