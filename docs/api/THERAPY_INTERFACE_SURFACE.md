# Therapy Interface Surface

**Document Type:** Repo Governance  
**Status:** Draft  
**Date:** 2026-04-07  

---

## Purpose

This document enumerates the exported `pkg/therapy` symbols that are currently used outside the package.

This is the interface surface that must be preserved when `pkg/therapy/` is extracted behind a private boundary.

Use this with:

- [THERAPY_EXTRACTION_PLAN.md](/home/mike/Mavaia/docs/THERAPY_EXTRACTION_PLAN.md)
- [PRIVATE_MIGRATION_PLAN.md](/home/mike/Mavaia/docs/PRIVATE_MIGRATION_PLAN.md)

---

## External Dependents

Current non-therapy package dependents:

- `pkg/api/server_v2.go`
- `pkg/service/generation.go`
- `pkg/hopecircuit/circuit.go`
- `pkg/cli/` consumes therapy HTTP endpoints, not package internals

---

## Exported Types Used Outside pkg/therapy

### Runtime components

- `SkillRunner`
- `DistortionDetector`
- `ABCAuditor`
- `ChainAnalyzer`
- `SessionSupervisor`
- `EventLog`
- `HelplessnessDetector`
- `MasteryLog`
- `AttributionalRetrainer`

### Shared data types

- `TherapyEvent`
- `DistortionType`
- `HelplessnessSignal`
- `SessionFormulation`
- `SessionReport`
- `SchemaName`
- `SchemaPattern`
- `SkillType`

### Shared entries / records

- `MasteryEntry`
- `Attribution3P`
- `DetectionResult`
- `DisputationReport`
- `ChainAnalysis`
- `SkillInvocation`

---

## Exported Constants / Enum Values Used Outside pkg/therapy

### Distortion constants

- `DistortionNone`
- `AllOrNothing`
- `FortuneTelling`
- `Magnification`
- `EmotionalReasoning`
- `ShouldStatements`
- `Overgeneralization`
- `MindReading`
- `Labeling`
- `Personalization`

### Schema constants

- `SchemaLearnedHelplessness`
- `SchemaBinaryThinking`
- `SchemaUncertaintyAvoidance`
- `SchemaSycophancyVulnerability`

### Skill constants

- `SkillSTOP`
- `SkillCheckFacts`
- `SkillFAST`
- `SkillTIPP`
- `SkillRadicalAccept`
- `SkillPLEASE`

---

## Exported Constructors Used Outside pkg/therapy

- `NewSkillRunner`
- `NewDistortionDetector`
- `NewABCAuditor`
- `NewChainAnalyzer`
- `NewSessionSupervisor`
- `NewEventLog`
- `NewHelplessnessDetector`
- `NewMasteryLog`
- `NewAttributionalRetrainer`

---

## Exported Functions Used Outside pkg/therapy

- `InferTopicClass`

---

## High-Coupling Call Sites

### API layer

`pkg/api/server_v2.go` is the heaviest consumer of concrete therapy types.

It directly stores:

- `*therapy.SkillRunner`
- `*therapy.DistortionDetector`
- `*therapy.ABCAuditor`
- `*therapy.ChainAnalyzer`
- `*therapy.SessionSupervisor`
- `*therapy.EventLog`
- `*therapy.HelplessnessDetector`
- `*therapy.MasteryLog`
- `*therapy.AttributionalRetrainer`

### Generation layer

`pkg/service/generation.go` directly depends on:

- therapy runtime component types
- `DistortionType`
- several distortion constants
- `InferTopicClass`
- `HelplessnessSignal`

### Hopecircuit

`pkg/hopecircuit/circuit.go` depends directly on:

- `*therapy.MasteryLog`

This should be reduced to a smaller mastery interface during extraction.

---

## What Must Survive Extraction

At minimum, the public boundary must preserve:

### Constructors or factories

- enough construction helpers to wire the API and generation layers

### Stable enums / DTOs

- distortion names
- schema names
- therapy event / formulation payload shapes

### Minimal helper functions

- `InferTopicClass` or an equivalent exposed through a smaller boundary package

---

## What Should Not Survive As Public Implementation

These can remain represented at the interface level, but their internal logic should move private:

- detector internals
- regex rules
- schema thresholds
- helplessness heuristics
- repair mapping logic
- retraining prompt logic
- session formulation logic

---

## Immediate Follow-On

Before moving code, create a narrower boundary:

1. define which of these types can become interfaces
2. define which enums/DTOs need to stay public
3. remove direct dependence on concrete `MasteryLog` where possible

