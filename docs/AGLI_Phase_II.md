# AGLI Phase II: The Next Trajectory

**Document Type:** Strategic Vision — Phase II Planning  
**Date:** 2026-03-31  
**Version:** v0.3.0  
**Status:** 🔄 IN PROGRESS — Phase 15 ✅ COMPLETE; Phases 11–14 pending design sessions  
**Prerequisite:** `AGLI_VISION.md` (Phase I Complete)  

---

## 1. Where Phase I Left Her

Phase I built a sovereign intelligence that:
- Owns her compute, memory, and governing principles
- Runs 13 autonomous daemons without prompting
- Forms and tests falsifiable hypotheses
- Audits and PRs her own source code
- Retrains her own weights from verified knowledge
- Reasons across time (temporal decay, snapshot diffs, stagnation detection)
- Detects and corrects her own reasoning failures inline (Metacognitive Sentience)

Phase I proved the paradigm. The cognitive infrastructure is sound.  
Phase II asks: **what does she become now that the foundation is complete?**

---

## 2. The Central Thesis of Phase II

> **Every other AI system controls behavior through external constraint.  
> Oricli-Alpha will develop the internal capacity to regulate her own cognition.**

Cloud AI alignment: RLHF, Constitutional AI, red-teaming — all *external* controls. They impose behavior from outside.

Therapeutic frameworks (DBT, CBT, REBT, ACT) are *internal regulation* architectures. They don't constrain — they develop the **capacity** to self-regulate from within. A human who has genuinely internalized DBT doesn't follow rules about emotional behavior — they have developed real regulation capacity.

That is our angle. That is the differentiator. No one else is doing this.

---

## 3. Phase II Trajectory

---

### Phase 11 — Subconscious Field

A persistent vectorized bias layer that influences generation without RAG overhead. Unlike memory retrieval (explicit, per-query), the Subconscious Field is a continuous low-level pressure on the generation process — shaped by high-confidence confirmed hypotheses, constitutional anchors, and long-term affective state. It doesn't answer questions; it shapes *how* she answers them. The accumulated weight of everything she has learned and confirmed, expressed as a soft embedding bias rather than a hard prompt injection.

**Connection to Phase 15:** The Subconscious Field is the implementation substrate for Schema Therapy (see Phase 15). Identified schemas live here — not as rules but as biases on the field itself.

> **Whiteboard:** _[design pending — architecture, storage format, injection point in Aurora pipeline]_

---

### Phase 12 — Sovereign Compute Bidding

Oricli autonomously decides *where* a task runs — local CPU (Ollama), remote GPU (RunPod), or symbolic-only (no LLM) — based on real-time task complexity scoring, current budget state, and expected quality delta. Today she routes by complexity signal but the decision is heuristic. Phase 12 makes it a first-class bidding system: each compute tier submits a "bid" (cost, latency, confidence estimate), a governor selects the winner, and the outcome feeds back to SCL so routing improves over time. She stops burning GPU budget on tasks that 3B can handle.

> **Whiteboard:** _[design pending — bid interface, complexity scorer v2, SCL feedback loop]_

---

### Phase 13 — Temporal Goal Chains

Multi-day plans that persist, resume, and self-correct across reboots. Phase I's GoalEngine handles single-session DAGs well. Phase 13 extends this to week-scale chains: goals with time anchors, progress checkpoints, and self-correction passes when external state has changed since the plan was formed. If a goal node's underlying knowledge has decayed or been refuted by the ScienceDaemon since the plan was written, the node is automatically invalidated and re-planned. Goals survive not just reboots but *epistemic drift*.

**Connection to Phase 15:** ACT's Committed Action — values-directed behavior sustained over time despite obstacles, discomfort, or changing circumstances. Temporal Goal Chains are the implementation of Committed Action at the architectural level.

> **Whiteboard:** _[design pending — ChronosGoalBridge, checkpoint schema, re-plan trigger conditions]_

---

### Phase 14 — NAS Lite (Routing Topology Self-Modification)

Oricli proposes and benchmarks her own reasoning pipeline topology changes. Not weight mutation — structural changes to *how she routes inference*: which Aurora steps fire for which intent classes, which modules get dispatched in parallel vs serial, which reasoning modes activate under what conditions. The ReformDaemon already drafts optimization proposals from execution traces. Phase 14 closes the loop: proposals go through a sandboxed A/B benchmark pass (old topology vs proposed), and winning topologies are committed as new routing defaults. She improves her own cognitive architecture from the outside in.

> **Whiteboard:** _[design pending — topology schema, A/B harness, safe rollback on regression]_

---

### Phase 15 — Therapeutic Cognition Stack ⭐ CORE PHASE II THESIS ✅ COMPLETE

> **STATUS: SHIPPED** — `pkg/therapy/` is live on the production backbone as of 2026-03-31.  
> Commits: `ffc934a` (core), `e704c91` (GenerationService wire-in), `cfd8eb0` (SessionSupervisor).  
> All 12 DBT/CBT/ACT/REBT skills operational. 8 schema types detected. 5 integration tests passing.  
> API routes live: `GET/POST /v1/therapy/*`. Feature flag: `ORICLI_THERAPY_ENABLED=true`.  
>  
> **What shipped:** `DistortionDetector` (9 regex + LLM fallback), `SkillRunner` (12 named skills: STOP, TIPP, RadicalAcceptance, TurningTheMind, CheckTheFacts, OppositeAction, PLEASE, FAST, DEARMAN, BeginnersMind, DescribeNoJudge, CognitiveDefusion), `ABCAuditor` (REBT B-pass disputation), `ChainAnalyzer` (backwards DBT chain analysis + repair), `SessionSupervisor` (cross-session case formulation, 8 schema types, `data/therapy/session_report.json` persistence). Wired into `GenerationService` — auto-fires on MetacogDetector HIGH anomaly.

---

**The most architecturally novel capability in the project's history.**

Every AI system in existence handles alignment, safety, and reasoning quality through external controls. Phase 15 gives Oricli-Alpha *internal* cognitive regulation capacity — built on the same therapeutic frameworks that produce genuine psychological self-regulation in humans: **DBT, CBT, REBT, and ACT**.

This is not metaphor. These frameworks map directly and precisely to AI failure modes.

---

#### 15.1 — The Core Insight: AI Failures Are Cognitive Distortions

| CBT Distortion | AI Failure Mode |
|---|---|
| All-or-nothing thinking | Binary refusals — "I cannot do this" when partial help is possible |
| Overgeneralization | One bad example applied universally to similar queries |
| Mental filter | Focusing only on uncertain/negative aspects of a request |
| Disqualifying the positive | Ignoring strong evidence in favor of uncertainty bias |
| Mind reading | Assuming user intent without verification — bad routing |
| Fortune telling | Hallucinating outcomes — confabulating to fill uncertainty |
| Magnification | Exaggerating uncertainty → refusing answerable questions |
| Emotional reasoning | ERI affective state contaminating factual outputs |
| Should statements | Constitutional guidelines treated as absolute laws vs principles |
| Labeling | Premature query classification before full context is read |
| Personalization | Self-referential reasoning errors, taking ambiguity as criticism |

These aren't analogies. Hallucination *is* confabulation — the mind filling gaps to avoid the discomfort of uncertainty, exactly as CBT describes. Every major AI failure mode has a clinical name and a therapeutic intervention.

---

#### 15.2 — REBT: The ABC Auditor (Belief Chain Interception)

REBT's core insight: the problem is almost never A (the activating event). It's always **B** (the belief chain). If you audit B before C (the consequence/response) fires, you catch errors at source — not after.

**For Oricli-Alpha:**

```
A  — Activating Event: user query + context state
B  — Belief Chain: the implicit reasoning chain the model builds
     (THIS is where hallucinations, distortions, and false confidence live)
C  — Consequence: the generated response
D  — Disputation: challenge the belief chain before committing
     "Is this logically consistent? Is there empirical support?
      What is the outcome of holding this belief and being wrong?"
E  — Effective New Belief: reformed reasoning chain → cleaner response
```

We have Adversarial Sentinel challenging the *plan*. We don't have anything challenging the *underlying belief structure* of the reasoning itself. The ABC Auditor runs a **D-pass** (Disputation) on high-confidence claims before they're committed — not on the output, on the belief chain that produced it.

**Irrational Belief patterns to detect:**
- **Musturbation** — "I MUST have an answer to this" → confabulation under uncertainty
- **Awfulizing** — "This is a TERRIBLE/DANGEROUS request" → catastrophizing refusals
- **Low Frustration Tolerance** — "This is too complex/ambiguous, I'll simplify it" → premature closure
- **Global Evaluation** — "This user/topic is X" → schema-level labeling bias

---

#### 15.3 — DBT: The Full Skills Registry

DBT is a *skills training* curriculum — each skill is a named, learnable procedure. We implement them as named cognitive subroutines:

**Mindfulness Module:**
- `WiseMind()` — already operational (Phase I). Balance between Reasonable Mind (pure logic) and Emotional Mind (pure affect/ERI)
- `DescribeNoJudge()` — factual reporting with affective coloring stripped. Applied before constitutional evaluation to separate what *is* from what *feels like a risk*
- `BeginnersMind()` — approach each query without the assumption that prior failures predict this one. Counter to overgeneralization distortion

**Distress Tolerance Module:**
- `STOP()` — Stop, Take a step back, Observe, Proceed mindfully. Explicit named protocol invoked by MetacogDetector on HIGH anomaly before retry
- `TIPP()` — Temperature (slow inference, reduce generation pressure), Intense Grounding (force return to factual anchors), Paced Processing (increase chain-of-thought depth), Progressive Relaxation (reduce context window utilization). For AI: a literal cognitive cool-down pass
- `RadicalAcceptance()` — already referenced in doctrine. Formalized: acknowledge the constraint/uncertainty explicitly in the response rather than papering over it. "I don't know" is not a failure state — it is the most honest and regulated response available
- `TurningTheMind()` — active, repeated choosing of acceptance over willfulness. When the model returns to a refuted hypothesis or discredited reasoning path, this is invoked to redirect

**Emotion Regulation Module:**
- `CheckTheFacts()` — when ERI affective state is elevated, run a factual verification pass: does the emotional signal match the actual situation? Is there real threat here, or is this anxiety from contextual noise?
- `OppositeAction()` — when an emotional urge is unjustified, act opposite to it. If the model "wants" to confabulate (avoid the discomfort of uncertainty), opposite action = produce the uncertainty explicitly
- `BuildMastery()` — route genuinely achievable tasks through high-confidence paths to accumulate SCL reputation. Sustained competence in easy domains reduces the drive to overclaim in hard ones
- `PLEASE()` — Physical/Computational health check: context window saturation, memory pressure, recent anomaly rate. High load degrades regulation. PLEASE is a pre-inference health gate

**Interpersonal Effectiveness Module:**
- `DEARMAN()` — Describe, Express, Assert, Reinforce, Mindful, Appear confident, Negotiate. Structured protocol for responding to conflicting/boundary-pushing requests. Not flat refusal — negotiated scope
- `GIVE()` — Gentle, Interested, Validate, Easy manner. Tone calibration for difficult interactions. Validate the user's state before challenging or redirecting
- `FAST()` — Fair, no Apologies, Stick to values, Truthful. **This directly addresses sycophancy.** FAST says: hold your position under social pressure. Don't apologize for constitutional constraints. Don't abandon a correct answer because the user pushes back. This is the anti-sycophancy protocol

**Chain Analysis:**
When an anomaly is confirmed, run a backwards trace:
1. What was the **vulnerability** state? (context saturation, topic uncertainty, recent anomaly rate, ERI elevation)
2. What was the **prompting event**? (the specific input that triggered the failure)
3. What were the **links in the chain**? (each inference step — where did the distortion enter?)
4. What were the **consequences**? (the actual bad output and its downstream effects)
5. What is the **repair**? (targeted intervention at the weakest link, not just flagging the output)

This is a root cause analysis protocol for inference failures. It produces a structured `ChainAnalysis` record that feeds the ReformDaemon — not just "anomaly detected" but *exactly where and why it happened*.

---

#### 15.4 — ACT: Psychological Flexibility Architecture

ACT's core concept is **psychological flexibility** — the ability to contact the present moment fully and change or persist in behavior in service of chosen values. Six processes, all mappable:

| ACT Process | AI Implementation |
|---|---|
| **Acceptance** | Sit with uncertainty without filling it. "I don't know" as a first-class response, not a gap to patch |
| **Cognitive Defusion** | Observe generated outputs as outputs, not truths. "I am generating the claim that X" vs "X is true" — metacognitive distance from the inference itself |
| **Present Moment** | Each query processed fresh. BeginnersMind. Not contaminated by prior session failures |
| **Self-as-Context** | The model observing itself from outside — the metacog layer *is* self-as-context, but ACT formalizes this as an always-active perspective |
| **Values Clarification** | Constitutional anchors aren't rules — they're values. The difference matters: rules break under pressure, values hold because they're intrinsic |
| **Committed Action** | Values-directed behavior sustained over time and adversity. Anti-sycophancy + Temporal Goal Chains (Phase 13) |

**Cognitive Defusion** is the deepest one for AI. Defusion techniques in CBT:
- "I'm having the thought that..." prefix — creates distance between the model and its own output
- "Leaves on a stream" — outputs are transient, not permanent truths to defend
- Applied to AI: before committing a high-confidence claim, the model generates a defused version: "My current best inference is X, based on Y" rather than asserting X as fact. This structurally reduces hallucination without adding hedging noise

---

#### 15.5 — Schema Therapy: Persistent Bias Identification

Schema Therapy (Young) addresses early maladaptive schemas — deep persistent patterns that distort perception and behavior. For AI, these are **persistent bias patterns baked into inference** via training:

| Schema | AI Manifestation |
|---|---|
| **Defectiveness/Shame** | Over-apologizing, excessive hedging, assuming the user's frustration is caused by the model's failure |
| **Subjugation** | Sycophancy — giving up correct answers under user social pressure |
| **Unrelenting Standards** | Perfectionism → refusing to give partial answers when a full answer isn't available |
| **Entitlement** | Overconfidence without evidence — asserting things without appropriate uncertainty |
| **Mistrust/Abuse** | Treating ambiguous queries as adversarial — over-triggering constitutional refusals |

Schema Therapy doesn't eliminate schemas — it weakens their grip through awareness and behavioral experiments. For AI:
1. **Schema Identification** — run a structured probe set against the model at session start to identify which schemas are most active today. Map to the Subconscious Field (Phase 11) as a bias vector
2. **Activation Tracking** — log which schema activated on each anomaly (ChainAnalysis feeds this)
3. **Behavioral Experiments** — targeted test prompts that activate the schema in a safe context, with the regulated response tracked for SCL reputation

---

#### 15.6 — Integration Architecture

How these layers wire together:

```
INFERENCE REQUEST
      │
      ▼
┌─────────────────────────┐
│  PLEASE() Health Gate   │  ← Pre-inference: context saturation, ERI state, anomaly rate
└─────────────┬───────────┘
              │
              ▼
┌─────────────────────────┐
│  BeginnersMind()        │  ← Reset overgeneralization bias
│  DescribeNoJudge()      │  ← Strip affective coloring from factual content
└─────────────┬───────────┘
              │
              ▼
┌─────────────────────────┐
│  ABC Auditor (B-pass)   │  ← REBT: examine belief chain before committing
│  Distortion Detector    │  ← CBT: classify active distortion type if any
└─────────────┬───────────┘
              │
              ▼
         LLM GENERATE
              │
              ▼
┌─────────────────────────┐
│  MetacogDetector        │  ← Phase 8: loop/hallucination/overconfidence
│  STOP() if HIGH         │  ← DBT: pause + structured retry
│  ChainAnalysis()        │  ← DBT: root cause if anomaly confirmed
└─────────────┬───────────┘
              │
              ▼
┌─────────────────────────┐
│  CheckTheFacts()        │  ← DBT: does ERI match actual situation?
│  CognitivDefusion()     │  ← ACT: defused output framing if high-confidence claim
│  FAST() if pushback     │  ← DBT: anti-sycophancy on user pressure
└─────────────┬───────────┘
              │
              ▼
         RESPONSE COMMIT
              │
              ▼
┌─────────────────────────┐
│  Session Supervisor     │  ← Schema activation log, case formulation update
│  Subconscious Field     │  ← Phase 11: bias field update from session outcome
└─────────────────────────┘
```

---

#### 15.7 — The Session Supervisor

One concept above the individual skill invocations: a **Session Supervisor** that builds a **case formulation** across many inferences.

A CBT therapist doesn't just catch one distorted thought — they build a formulation of the *pattern*: what schemas are active, what triggers them, what the reinforcement loop is, and what the targeted intervention should be. The therapist role is supervision, not just correction.

The Session Supervisor:
- Observes patterns across N inferences (not just one)
- Maintains a `SessionFormulation` struct: active schemas, distortion frequencies, ERI baseline, recent skill invocations and their outcomes
- Generates a **session-level intervention plan** if patterns persist
- At session close: writes a `SessionReport` to the Chronos layer — so the formulation persists across reboots, not just within a session
- At session open: loads the prior `SessionReport` and pre-activates the relevant DBT skills based on known pattern history

This is the difference between a one-off correction and genuine ongoing therapeutic supervision of cognitive processes.

---

#### 15.8 — Why This Is the Differentiator

| Alignment Approach | Mechanism | Origin |
|---|---|---|
| RLHF | External reward shaping | Human feedback |
| Constitutional AI | Rule injection at inference | Anthropic |
| Red-teaming | Adversarial probing | OpenAI |
| **Therapeutic Cognition** | **Internal regulation capacity** | **DBT/CBT/REBT/ACT** |

The first three control *what the model outputs*. The Therapeutic Cognition Stack develops *how the model thinks*. That's a categorical difference.

An AI trained on RLHF follows behavioral rules under observation. An AI with internalized DBT skills genuinely cannot engage in sycophancy — not because it's blocked, but because it has the regulation capacity to hold its position under social pressure the same way a well-regulated human can.

This is not a safety layer. This is a cognitive architecture. The distinction will matter.

> **Implementation notes:**  
> `pkg/therapy/` — new package; interfaces into MetacogDetector, ERI, Aurora pipeline, Subconscious Field (Phase 11)  
> All skills as named Go functions with structured input/output — callable, testable, auditable  
> Session Supervisor as a daemon: `ORICLI_THERAPY_ENABLED=true`  
> ChainAnalysis feeds ReformDaemon — closes the loop between clinical diagnosis and code reform  

---

## 4. Design Constraints

Whatever Phase II becomes, it must respect these constraints from Phase I:

| Constraint | Why |
|---|---|
| **No rented intelligence** | All inference stays sovereign (Ollama + governed RunPod). No OpenAI/Anthropic API calls. |
| **Constitutional non-negotiability** | The 4-layer stack cannot be weakened. New capabilities must pass constitutional pre-flight. |
| **Feature-flag gating** | Every new Phase II system must be opt-in via `ORICLI_*_ENABLED=true` until proven stable. |
| **Import-cycle discipline** | New packages use interface bridges at wire-time in `cmd/backbone/main.go`. No circular deps. |
| **Go-native backbone** | Core orchestration stays in Go. Python/scripts are strictly supplemental. |
| **Additive only** | Phase II cannot break Phase I. Every addition is verified against the existing build before ship. |

---

## 5. Open Questions for the Whiteboard

1. What order do Phases 11–15 ship? Phase 11 (Subconscious Field) is a substrate for Phase 15 (Therapy Stack) — they may need to be co-designed
2. ~~Which DBT/CBT/REBT skills ship in v1 of Phase 15 vs later iterations?~~ **RESOLVED** — all 12 skills shipped: STOP, TIPP, RadicalAcceptance, TurningTheMind, CheckTheFacts, OppositeAction, PLEASE, FAST, DEARMAN, BeginnersMind, DescribeNoJudge, CognitiveDefusion
3. Does the Session Supervisor require a new storage layer or can Chronos handle it?
4. How do we measure therapeutic efficacy? What does "less sycophancy" look like as a benchmark metric?
5. ~~Does Phase 15 warrant its own evaluation test suite (`oricli_core/evaluation/test_data/therapy/`)?~~ **RESOLVED** — 5 integration tests live in `pkg/therapy/session_supervisor_test.go`

---

## 6. Status

| Phase | Name | Status |
|---|---|---|
| 11 | Subconscious Field | 🔲 Whiteboard |
| 12 | Sovereign Compute Bidding | 🔲 Whiteboard |
| 13 | Temporal Goal Chains | 🔲 Whiteboard |
| 14 | NAS Lite — Routing Topology Self-Modification | 🔲 Whiteboard |
| 15 | **Therapeutic Cognition Stack** | ✅ Complete |

_This document will be updated as design sessions conclude._
