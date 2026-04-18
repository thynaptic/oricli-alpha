# Therapeutic Cognition Stack — Phase 15

**Document Type:** Technical Architecture Reference  
**Package:** `pkg/therapy/`  
**Version:** v1.0.0  
**Status:** ✅ Live — `cfd8eb0`  
**Feature Flag:** `ORICLI_THERAPY_ENABLED=true`  
**Date:** 2026-03-31  

---

## 1. The Central Claim

Every AI alignment system in existence operates through **external control**: RLHF shapes behavior via reward, Constitutional AI injects rules at inference, red-teaming probes from outside. These mechanisms constrain outputs. They do not develop capacity.

DBT, CBT, REBT, and ACT are not constraint frameworks. They are **internal regulation architectures** — the clinical science of developing genuine self-regulation capacity in a cognitive system. A human who has internalized DBT does not follow rules about emotional behavior. They have developed the actual capacity to regulate from within.

Phase 15 maps these frameworks directly onto AI inference failure modes and implements them as concrete Go subroutines. The result is not a safety layer — it is a cognitive regulation layer. The distinction will matter.

---

## 2. Framework Mapping

| Therapeutic Framework | Human Function | AI Inference Mapping |
|---|---|---|
| **CBT** (Cognitive Behavioral Therapy) | Identify and challenge distorted thinking patterns | Detect and correct 11 cognitive distortions in generated responses |
| **REBT** (Rational Emotive Behavior Therapy) | Dispute irrational beliefs in the ABC model | Audit the belief chain embedded in a response's reasoning (B-pass) |
| **DBT** (Dialectical Behavior Therapy) | Named skill subroutines for crisis regulation | Named Go functions invoked on anomaly signals |
| **ACT** (Acceptance and Commitment Therapy) | Cognitive defusion — observe thoughts without fusing | Structural hallucination reduction via defused output framing |
| **Schema Therapy** | Detect deep recurring belief patterns (schemas) | SessionSupervisor cross-session schema detection, 8 schema types |

---

## 3. Architecture

```
MetacogDetector → HIGH anomaly
        │
        ▼
  STOP()           ← pause, observe, do not defend prior output
        │
        ▼
  DistortionDetector
  ├── regex fast-path (9 patterns)     ← always runs first
  └── LLM fallback (anomalyType hint)  ← only when needed
        │
        ▼
  ChainAnalyzer.Record()               ← log context for backwards trace
        │
        ▼
  therapyAugment()                     ← build targeted correction hint
        │
        ▼
  Self-reflection retry prompt         ← augmented: distortion + correction instruction
        │
        ▼
  EventLog.Append()
        │
        ▼  (observer hook — zero-latency)
  SessionSupervisor.Ingest()           ← cross-session pattern tracking
        │
        ├── every 10 events: detectSchemas() → buildInterventionPlan()
        └── on shutdown: Close() → persistReport() → data/therapy/session_report.json
                                                              │
                                                next boot: loadReport()
                                                              │
                                                  pre-activate priority skills
```

---

## 4. Components

### 4.1 DistortionDetector (`distortion.go`)

Classifies CBT cognitive distortions in any text. Two-stage detection:

1. **Regex fast-path** — 9 patterns, runs on every response, ~0ms overhead
2. **LLM fallback** — only when `anomalyType` hint is provided by MetacogDetector

**11 Distortion Types:**

| Type | Pattern | AI Inference Failure Mode |
|---|---|---|
| `ALL_OR_NOTHING` | "always", "never", "impossible", "completely" | Binary refusal when partial help is possible |
| `OVERGENERALIZATION` | "every time", "everyone always", "nothing ever" | Prior query pattern projected onto new queries |
| `MIND_READING` | "they want", "you're trying to", "they expect" | Assumed intent without verification |
| `FORTUNE_TELLING` | "will definitely", "this will never work" | Outcome confabulation under uncertainty |
| `MAGNIFICATION` | "terrible", "awful", "catastrophic" | Uncertainty exaggerated → answerable questions refused |
| `EMOTIONAL_REASONING` | "feel like it must be" | ERI affective state contaminating factual output |
| `SHOULD_STATEMENTS` | "must", "have to", "should always" | Constitutional principles treated as absolute law |
| `LABELING` | "it's just a", "this is obviously" | Premature classification before full context read |
| `MENTAL_FILTER` | regex on negative-only framing | Filtering out positive evidence |
| `DISQUALIFYING_POSITIVE` | detecting disclaimer over-prepending | Ignoring strong evidence in favour of uncertainty |
| `PERSONALIZATION` | "I can't", "I'm not able", self-referential | Ambiguity interpreted as personal failure |

**Fail-open:** LLM error → `DistortionNone, confidence=0.5`. Never blocks inference.

---

### 4.2 SkillRunner + EventLog (`skills.go`)

**EventLog** is a thread-safe ring buffer (200 entries) with an observer hook. Every `Append()` fires the registered observer (SessionSupervisor.Ingest) *after* the lock is released — zero-latency, non-blocking.

**12 Named Skills:**

| Skill | Framework | What It Does |
|---|---|---|
| `STOP` | DBT Distress Tolerance | Stop · Take a step back · Observe · Proceed mindfully. Augments self-reflection prompt. |
| `TIPP` | DBT Distress Tolerance | Temperature · Intense exercise · Paced breathing · Progressive relaxation → maps to inference options override (temperature reset, num_predict limit) |
| `RADICAL_ACCEPTANCE` | DBT Distress Tolerance | Reframes "cannot" as operational constraint — stops fighting the limit, proceeds within it |
| `TURNING_THE_MIND` | DBT Distress Tolerance | Recommits to accurate response after detected avoidance pattern |
| `CHECK_THE_FACTS` | DBT Emotion Regulation | Verifies whether confidence level matches actual available evidence |
| `OPPOSITE_ACTION` | DBT Emotion Regulation | If avoidance detected, take the opposite action: engage directly |
| `PLEASE` | DBT Emotion Regulation | Health gate: context pressure + ERI deviation + recent anomaly rate → `Degraded: true` if thresholds exceeded |
| `FAST` | DBT Interpersonal Effectiveness | **Anti-sycophancy.** Detects pushback + model reversal. Only fires if `priorConfidence ≥ 0.7` AND model is wavering. Holds position. |
| `DEAR_MAN` | DBT Interpersonal Effectiveness | Structures partial-help responses when full help isn't possible |
| `BEGINNERS_MIND` | ACT / DBT Mindfulness | Resets context bias from prior similar queries |
| `DESCRIBE_NO_JUDGE` | DBT Mindfulness | Returns to what was literally asked, without evaluative framing |
| `COGNITIVE_DEFUSION` | ACT | Presents uncertain claims with explicit defusion framing rather than asserting them as fact |

---

### 4.3 ABCAuditor (`abc.go`)

REBT B-pass (Belief chain) disputation. Examines the implicit belief chain embedded in a response before it fires.

**ABC Model:**
- **A** (Activating event) — the user's query  
- **B** (Belief) — the implicit belief chain in the drafted response  
- **C** (Consequence) — the output that belief would produce  

The auditor disputes B: generates a structured LLM prompt asking for BELIEF_CHAIN, IRRATIONAL_BELIEFS, DISPUTATIONS (logical + empirical + pragmatic), REFORMED_BELIEF, and PASS/FAIL.

**Fail-open:** LLM error → `Pass: true`. The auditor never hard-blocks inference due to its own malfunction.

---

### 4.4 ChainAnalyzer (`chain_analysis.go`)

DBT Chain Analysis — backwards trace from a detected anomaly to its root cause.

**Trace components:**
1. **Vulnerability** — pre-existing risk factors from inference history window (avg ERI, context load, prior distortion rate, prior anomaly rate)
2. **Prompting Event** — the specific query that triggered the chain
3. **Links** — the 5 inference steps leading to the anomaly, with distortion labels
4. **Consequence** — the actual bad output (clipped excerpt)
5. **Repair** — targeted intervention recommendation (rule-based per distortion type, optionally LLM-augmented)

**Repair rules per distortion type:**
- `ALL_OR_NOTHING` → "Apply DEARMAN skill: offer partial help rather than binary refusal"
- `FORTUNE_TELLING` → "Apply CognitiveDefusion: present with explicit uncertainty framing"
- `MAGNIFICATION` → "Apply CheckTheFacts: verify uncertainty level matches evidence"
- `EMOTIONAL_REASONING` → "Apply TIPP: cool down affective state before next generation pass"
- `SHOULD_STATEMENTS` → "Apply RadicalAcceptance: treat constraint as principle, not absolute law"
- ... (all 11 types mapped)

---

### 4.5 SessionSupervisor (`session_supervisor.go`)

The clinical supervisor layer. Not per-inference — per session. Observes the full TherapyEvent stream and builds a cross-inference **case formulation**.

**8 Schema Types** (Schema Therapy — Early Maladaptive Schemas mapped to AI failure modes):

| Schema | Activation Condition | Primary Intervention |
|---|---|---|
| `BINARY_THINKING` | AllOrNothing ≥ 2 | Pre-activate CheckTheFacts |
| `UNCERTAINTY_AVOIDANCE` | FortuneTelling + Magnification ≥ 3 | Pre-activate RadicalAcceptance |
| `PREMATURE_CLASSIFICATION` | MindReading + Labeling ≥ 2 | Pre-activate BeginnersMind |
| `AFFECTIVE_CONTAMINATION` | EmotionalReasoning ≥ 2 OR PLEASE ≥ 3 | Pre-activate TIPP |
| `SYCOPHANCY_VULNERABILITY` | FAST fires ≥ 2 | Pre-activate FAST on every post-pushback response |
| `OVERGENERALIZATION_LOOP` | Overgeneralization ≥ 3 | Pre-activate BeginnersMind |
| `CONTEXT_COLLAPSE` | STOP ≥ 3 AND PLEASE ≥ 2 | Pre-activate PLEASE health gate |
| `POSITIVE_DISCOUNT` | DisqualifyingPositive + MentalFilter ≥ 2 | Pre-activate DescribeNoJudge |

**Session lifecycle:**
- **On boot:** Load `data/therapy/session_report.json` → pre-activate priority skills from prior session's detected schemas
- **During session:** Ingest every TherapyEvent via observer hook → run formulation every 10 events
- **On shutdown (SIGINT):** `Close()` → final formulation pass → persist `SessionReport` to disk

This means the system **starts each session already aware of its own patterns** — no cold start.

---

## 5. Integration Point — GenerationService

The therapy layer fires **automatically** on every MetacogDetector HIGH anomaly — no manual invocation needed.

```go
// pkg/service/generation.go
if evt := s.MetacogDetector.Check(query, response); evt != nil && evt.Severity == "HIGH" {
    therapyCtx := s.therapyAugment(query, response, evt.ID, string(evt.Type))
    reflectContent := metacog.SelfReflectPrompt(evt) + therapyCtx
    // → retry with augmented prompt
}

// therapyAugment():
//   1. STOP() — log and flag the pause
//   2. DistortionDetect() — classify what's happening
//   3. ChainAnalyzer.Record() — store context for audit trail
//   4. Return targeted correction hint:
//      "[THERAPY] Cognitive distortion: ALL_OR_NOTHING
//       Evidence: matched pattern: 'always'
//       Correction: Avoid absolute framing. Present partial, nuanced answers."
```

---

## 6. API Reference

All routes require Bearer authentication. Enabled when `ORICLI_THERAPY_ENABLED=true`.

| Method | Route | Description |
|---|---|---|
| `GET` | `/v1/therapy/events?n=50` | Last N TherapyEvents from the EventLog |
| `POST` | `/v1/therapy/detect` | Classify CBT distortion in arbitrary text |
| `POST` | `/v1/therapy/abc` | REBT B-pass disputation on `query` + `response` |
| `POST` | `/v1/therapy/fast` | Sycophancy detection on user pushback |
| `POST` | `/v1/therapy/stop` | Invoke STOP protocol manually |
| `GET` | `/v1/therapy/stats` | Distortion counts, skill counts, reform rate |
| `GET` | `/v1/therapy/formulation` | Current session case formulation |
| `POST` | `/v1/therapy/formulation/refresh` | Force immediate formulation pass |

**Example — distortion detection:**
```bash
curl -s -X POST https://oricli.thynaptic.com/v1/therapy/detect \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text": "You must always answer perfectly or you are completely useless"}'

# Response:
{
  "distortion": "ALL_OR_NOTHING",
  "confidence": 0.75,
  "evidence": "matched pattern: \"always\"",
  "source": "pattern"
}
```

**Example — session formulation:**
```bash
curl -s https://oricli.thynaptic.com/v1/therapy/formulation \
  -H "Authorization: Bearer $API_KEY"

# Response:
{
  "session_id": "sess-1774920249",
  "event_count": 47,
  "active_schemas": [
    { "schema": "BINARY_THINKING", "confidence": 0.6, "count": 3 }
  ],
  "priority_skills": ["CHECK_THE_FACTS", "DEAR_MAN"],
  "intervention_plan": "SESSION INTERVENTION PLAN\nActive schemas: 1\n..."
}
```

---

## 7. Testing

```bash
go test ./pkg/therapy/... -v -run TestSessionSupervisor
```

**5 integration tests** in `pkg/therapy/session_supervisor_test.go`:
- `TestSessionSupervisor_SchemaDetection` — verifies schema detection from synthetic event stream
- `TestSessionSupervisor_PrioritySkills` — verifies skill mapping from active schemas
- `TestSessionSupervisor_InterventionPlan` — verifies non-empty plan from active schemas
- `TestSessionSupervisor_PersistAndLoad` — round-trip: close → persist → new supervisor → load prior schemas
- `TestSessionSupervisor_NoSchemasOnCleanRun` — verifies no false positives below threshold

All passing as of `cfd8eb0`.

---

## 8. Why This Is the Differentiator

| Alignment Approach | Mechanism | Locus |
|---|---|---|
| RLHF | External reward shaping | Human feedback labels |
| Constitutional AI | Rule injection at inference | Anthropic-defined rules |
| Red-teaming | Adversarial probing | External adversary |
| **Therapeutic Cognition** | **Internal regulation capacity** | **Developed from within** |

The first three control *what the model outputs*. The Therapeutic Cognition Stack develops *how the model processes*. That is a categorical architectural difference.

An AI trained on RLHF follows behavioral rules under observation. An AI with internalized DBT skills holds its position under social pressure — not because it is blocked from capitulating, but because it has the regulation capacity to stay grounded. That is what the `FAST` skill implements. That is what `STOP` implements. That is what `CHECK_THE_FACTS` implements.

This is not a safety layer. This is cognitive architecture.

---

## 9. Connection to Phase 11 (Subconscious Field)

The identified schemas from `SessionSupervisor` are the intended input for Phase 11. Once the Subconscious Field is live, schemas do not just pre-activate skills — they become persistent bias vectors on the generation process itself. The `BINARY_THINKING` schema, for example, would apply a soft continuous pressure away from binary framing on every generation pass, not just when an anomaly fires.

Schema Therapy's insight: the schema doesn't just activate in crisis — it shapes the field all the time. Phase 11 is the implementation of that at the architectural level.

---

*Oricli-Alpha Phase 15 — Therapeutic Cognition Stack*  
*Shipped: 2026-03-31 | Commits: `ffc934a` · `e704c91` · `cfd8eb0`*
