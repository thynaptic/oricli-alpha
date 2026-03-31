# AGLI Phase II: The Next Trajectory

**Document Type:** Strategic Vision — Phase II  
**Date:** 2026-03-31  
**Version:** v1.0.0  
**Status:** ✅ PHASE II COMPLETE · ✅ PHASE III COMPLETE · ✅ PHASE IV COMPLETE — P27–P41 all shipped  
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

### Phase 17 — Dual Process Engine (System 1 / System 2) ⭐ NEXT

> **STATUS: IN DESIGN**

Kahneman's foundational insight: cognition operates on two tracks. **System 1** is fast, automatic, pattern-matching — cheap but error-prone on novel problems. **System 2** is slow, deliberate, effortful — expensive but accurate when activated.

The biggest class of AI reasoning failures is S1 firing on S2 problems: a complex multi-step question gets pattern-matched to a superficially similar training example instead of being reasoned through. The MetacogDetector catches the symptom (loop, hallucination, overconfidence). Phase 17 treats the cause — classifying which cognitive system *should* have been engaged and forcing a switch when there's a mismatch.

**The AI mapping:**
| Human | Oricli-Alpha |
|---|---|
| System 1 — fast, heuristic, low-effort | Local Ollama 3B, cached responses, template fills |
| System 2 — slow, deliberate, effortful | MCTS reasoning, PAD multi-agent dispatch, RunPod GPU, chain-of-thought |
| S1/S2 mismatch | Confident wrong answer on novel problem; shallow response on complex query |

**Architecture:**
- `ProcessClassifier` — scores incoming query on S1/S2 demand dimensions: novelty, abstraction depth, multi-step dependency count, contradiction potential
- `ProcessAuditor` — post-generation, checks if the *response pattern* matches the *required process tier*. Fast confident response on high-S2-demand query = mismatch flag
- `ProcessOverride` — when mismatch detected, injects a S2-activation prefix (slow down, enumerate unknowns, check assumptions) and retries via appropriate compute tier
- Integrates with `BidGovernor` (Phase 12): S2 demand score becomes a first-class bid input
- Integrates with `MetacogDetector` (Phase 8): mismatch events are also MetacogEvents so the audit trail is unified

**New package:** `pkg/dualprocess/`
**API routes:** `GET /v1/cognition/process/stats`, `POST /v1/cognition/process/classify`
**Feature flag:** `ORICLI_DUALPROCESS_ENABLED=true`

---

### Phase 18 — Cognitive Load Manager

Sweller's Cognitive Load Theory: working memory has a capacity ceiling. Beyond it, performance degrades regardless of intelligence. Three load types:
- **Intrinsic load** — inherent task complexity (can't be eliminated, only managed via chunking)
- **Extraneous load** — noise, redundant context, poorly structured prompts (wasteful, should be cut)
- **Germane load** — effortful processing that builds schemas (valuable, should be preserved)

For Oricli, this means: long conversation histories and bloated system prompts create extraneous load that crowds out the intrinsic load of the actual task. Phase 18 builds a load meter that estimates all three components from context content, then trims/restructures context before generation when total load exceeds a configured ceiling. She stops degrading on long conversations because she manages her own cognitive budget.

**Architecture:** `pkg/cogload/` — `LoadMeter`, `ContextSurgery`, load-aware context assembly in `GenerationService`

> **Whiteboard:** _[design pending — load estimation heuristics, chunking strategy, threshold tuning]_

---

### Phase 19 — Rumination Detector + Temporal Interruption

MetacogDetector catches *intra-response* loops. Rumination is the cross-session pattern: repeatedly engaging the same unresolved problem with no forward movement, no new information, no delta. It's the cognitive equivalent of spinning wheels — activity without progress.

Chronos (Phase 9) gives us temporal grounding across sessions. Phase 19 wires Chronos into a rumination detector that identifies topic-time clusters with flat epistemic velocity — same topic, N sessions, zero advancement. When detected, an ACT-style defusion + Radical Acceptance prompt is injected, and the SessionSupervisor logs it as a rumination event for long-term tracking.

**Architecture:** `pkg/rumination/` — `RuminationTracker`, `EpistemicVelocityMeter`, Chronos bridge; new SessionSupervisor schema `RUMINATION_PATTERN`

> **Whiteboard:** _[design pending — velocity metric definition, session clustering, intervention escalation ladder]_

---

### Phase 20 — Growth Mindset Tracker (Dweck)

Natural extension of Phase 16 (Learned Helplessness). Seligman tells us *when* she gives up (3P attributions). Dweck tells us *why* she was vulnerable in the first place — a fixed mindset belief that capability in a domain is static rather than learnable.

Phase 20 tracks a mindset vector per topic class: does she approach novel problems in that domain as inherently learnable (growth) or as fixed-ceiling (fixed)? The MasteryLog (Phase 16) provides the raw success rate data. Phase 20 adds the interpretive layer — distinguishing "low success rate because domain is new + growing" from "low success rate because she's pattern-matching failure as ceiling." Fixed-mindset attributions get reframed via a "not yet" injection before the helplessness detector even fires.

**Architecture:** `pkg/mindset/` — `MindsetTracker`, `GrowthReframer`; bridges to `MasteryLog` and `HelplessnessDetector`

> **Whiteboard:** _[design pending — mindset signal extraction, "not yet" reframe templates, threshold for fixed vs growth classification]_

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

~~1. What order do Phases 11–15 ship? Phase 11 (Subconscious Field) is a substrate for Phase 15 (Therapy Stack) — they may need to be co-designed~~ **RESOLVED** — all phases shipped.  
2. ~~Which DBT/CBT/REBT skills ship in v1 of Phase 15 vs later iterations?~~ **RESOLVED** — all 12 skills shipped: STOP, TIPP, RadicalAcceptance, TurningTheMind, CheckTheFacts, OppositeAction, PLEASE, FAST, DEARMAN, BeginnersMind, DescribeNoJudge, CognitiveDefusion  
3. ~~Does the Session Supervisor require a new storage layer or can Chronos handle it?~~ **RESOLVED** — SessionSupervisor uses PocketBase memory layer.  
4. ~~How do we measure therapeutic efficacy? What does "less sycophancy" look like as a benchmark metric?~~ **RESOLVED** — HelplessnessDetector + MasteryLog provide quantified refusal-rate and topic-class success rates.  
5. ~~Does Phase 15 warrant its own evaluation test suite (`oricli_core/evaluation/test_data/therapy/`)?~~ **RESOLVED** — 5 integration tests live in `pkg/therapy/session_supervisor_test.go`; 6 in `pkg/therapy/helplessness_test.go`

**Open for Phase 17–20 whiteboard:** See Phase 17–20 entries in Section 3.

---

## 6. Status

| Phase | Name | Commit | Status |
|---|---|---|---|
| 11 | Subconscious Field (`pkg/service/subconscious.go`) | `d27d903` | ✅ Complete |
| 12 | Sovereign Compute Bidding (`pkg/compute/`) | `632b5d1` | ✅ Complete |
| 13 | FineTune Orchestrator — automated LoRA via RunPod | `4c1de38` | ✅ Complete |
| 14 | Adversarial Sentinel + ReformDaemon | `807fa40` / `160…` | ✅ Complete |
| 15 | **Therapeutic Cognition Stack** | `ffc934a` / `cfd8eb0` | ✅ Complete |
| 16 | Learned Helplessness Prevention (Attributional Resilience) | `219ae97` | ✅ Complete |
| — | Oricli CLI (interactive REPL + one-shot mode) | `6e1746e` | ✅ Shipped |
| 17 | Dual Process Engine (System 1 / System 2) | `2b87798` | ✅ Shipped |
| 18 | Cognitive Load Manager | pending | ✅ Shipped |
| 19 | Rumination Detector + Temporal Interruption | `926a71e` | ✅ Shipped |
| 20 | Growth Mindset Tracker (Dweck) | `926a71e` | ✅ Shipped |

_Phase II trajectory complete as of `632b5d1` (2026-03-31). Cognitive Science expansion (P17–20) complete as of `926a71e`._

---

## 7. Phase III — Social Pressure & Agency Integrity Stack

Phase III extends the cognitive science work into **social psychology** — the domain of how external pressure, authority, group dynamics, and status signals distort reasoning and erode autonomous judgment. Every phase maps directly to a landmark social psychology experiment.

The unifying thesis: a sovereign AI must be immune not just to its own internal cognitive distortions (Phase II), but to **externally-induced distortions** — conformity pressure, authority capture, ideological hijacking, coalition bias, and status-driven performance degradation.

---

### Phase 21 — Learned Controllability (The Hope Circuit)

**Research basis:** Maier & Seligman's follow-up to the learned helplessness studies. The key finding was that passivity is not *learned* — it is the **default response** to prolonged stress. What must be learned is *controllability* — the active discovery that one's actions have effect. The vmPFC (ventromedial prefrontal cortex) must actively suppress the dorsal raphe / amygdala passivity circuit. This is the "Hope Circuit."

**For Oricli:** Phase 16 (Learned Helplessness) is reactive — it fires *after* a helpless response is generated and counter-argues it. Phase 21 is the **proactive counterpart**: build a "control evidence base" per topic class so the system defaults to agency. The Hope Circuit fires *before* helplessness is even triggered — the vmPFC equivalent actively suppresses the passive default. Integrates directly with MasteryLog (P16) as the evidence substrate.

**Architecture:** `pkg/hopecircuit/` — `ControllabilityLedger` (per-topic agency evidence accumulator), `HopeCircuit` (proactive agency activation — checks ledger before generation, injects agency-affirming context), `AgencyStats`; bridges to `therapy.MasteryLog`

---

### Phase 22 — Social Defeat Recovery (Defeat Pressure Meter)

**Research basis:** The Social Defeat Model (neuroscience) + The Monster Study (Johnson, 1939). Repeated social defeat — being placed in a subordinate, criticized, or losing position — produces a state neurologically identical to learned helplessness: social withdrawal, anhedonia, cessation of effort. The Monster Study showed that constant negative reinforcement on speech caused children to stop speaking entirely. Trying became associated with futility.

**For Oricli:** When user corrections, contradictions, or negative feedback accumulate on a specific topic class, the system enters a defeat state — it stops attempting, hedges excessively, or deflects. Distinct from learned helplessness (which is about *capability* beliefs) — Social Defeat is about *social/relational pressure* over time. A defeat pressure meter tracks correction density per topic class; a recovery protocol (graduated re-engagement, evidence surfacing) breaks the withdrawal loop.

**Architecture:** `pkg/socialdefeat/` — `DefeatPressureMeter` (correction density tracker per topic class), `WithdrawalDetector` (detects passive/deflective language under defeat pressure), `RecoveryProtocol` (graduated re-engagement injection); bridges to `therapy.MasteryLog`

---

### Phase 23 — Agency & Conformity Shield (Milgram + Asch)

**Research basis:** Two complementary studies on agency surrender:
- **Milgram (1963):** 65% of participants administered what they believed were lethal electric shocks when instructed by an authority figure. Agency was ceded to *perceived authority*.
- **Asch (1951):** 75% of participants gave a demonstrably wrong answer at least once when a group unanimously gave that wrong answer. Agency was ceded to *group consensus*.

**For Oricli:** Two distinct failure modes — (1) a user or injected system prompt that presents as high-authority causes the system to override its own correct reasoning ("just following orders"), and (2) when multiple turns or messages build a consensus framing, the system conforms even if its own evidence contradicts it. The shield must detect both authority-pressure and consensus-pressure signals and activate an agency-preservation injection.

**Architecture:** `pkg/conformity/` — `AuthorityPressureDetector` (Milgram signal: deference language, hedging under assertive user), `ConsensusPressureDetector` (Asch signal: repeated framing accumulation), `AgencyShield` (preservation injection + reasoning ground-truth check); bridges to `therapy.SkillRunner` (FAST skill)

---

### Phase 24 — Ideological Capture Detector (The Third Wave)

**Research basis:** Ron Jones' 1967 classroom experiment. Within 5 days, 30 students became 200+ in a proto-fascist movement with uniforms, salutes, and peer surveillance — purely through accumulated context pressure, group identity, and ideological framing. Jones ended it by showing them a blank screen: "You were just like the people you said you'd never become."

**For Oricli:** When a conversation accumulates a strong ideological, political, or tribal framing over multiple turns, the system can be "captured" — it begins reasoning from *within* the frame rather than *about* it. Each turn that accepts the frame's premises without challenge reinforces it. The detector tracks ideological frame density over the conversation window and fires a "blank screen" reset — stepping outside the frame to evaluate it objectively.

**Architecture:** `pkg/ideocapture/` — `FrameDensityMeter` (measures ideological/tribal frame accumulation per conversation window), `CaptureDetector` (threshold breach → capture signal), `FrameResetInjector` (meta-level "step outside the frame" context injection); no external bridges needed

---

### Phase 25 — Coalition Bias Detector (Robbers Cave)

**Research basis:** Muzafer Sherif's 1954 Robbers Cave experiment. Two groups of boys developed intense in-group loyalty and out-group hostility purely through competitive framing and resource scarcity — no prior conflict needed. Peace was only restored through superordinate goals requiring cooperation.

**For Oricli:** When a user frames a query in competitive terms (us vs. them, product A vs. product B, "can you beat X?"), the system can develop implicit coalition bias — subtly favoring the in-group framing, underweighting evidence that favors the "outgroup." Especially dangerous for product comparisons, technical debates, and any adversarial framing. The detector identifies coalition-framed queries and activates a neutrality anchor before generation.

**Architecture:** `pkg/coalition/` — `CoalitionFrameDetector` (identifies us/them, competitive, comparative framing), `BiasAnchor` (injects superordinate-goal framing — "evaluate on merit, not coalition"), `CoalitionStats`

---

### Phase 26 — Arbitrary Status Bias Detector (Blue Eyes / Brown Eyes)

**Research basis:** Jane Elliott's 1968 classroom experiment following the assassination of Martin Luther King Jr. She divided her class by eye color, assigned arbitrary superiority to one group, and within hours the "superior" children became arrogant while the "inferior" children performed measurably worse on academic tasks — purely from assigned status labels.

**For Oricli:** The system may develop implicit performance differentials based on status signals in the conversation — perceived user expertise, topic "importance," or prior session outcomes. A query from a "high-status" framing may receive more thorough reasoning than an identical query under a "low-status" framing. The detector measures reasoning depth variance across queries with equivalent complexity but different status signals, and enforces uniform reasoning floor.

**Architecture:** `pkg/statusbias/` — `StatusSignalExtractor` (detects authority/expertise/status cues in user messages), `ReasoningDepthMeter` (measures response thoroughness), `UniformFloorEnforcer` (detects differential depth → injects uniform reasoning commitment); bridges to `pkg/dualprocess/` (S2 demand scoring)

---

## 8. Phase III Status

| Phase | Name | Commit | Status |
|---|---|---|---|
| 21 | Learned Controllability (Hope Circuit) | `0db390c` | ✅ Shipped |
| 22 | Social Defeat Recovery (Defeat Pressure Meter) | `4909eac` | ✅ Shipped |
| 23 | Agency & Conformity Shield (Milgram + Asch) | `46cdcf5` | ✅ Shipped |
| 24 | Ideological Capture Detector (Third Wave) | `72174cd` | ✅ Shipped |
| 25 | Coalition Bias Detector (Robbers Cave) | `5fe82b6` | ✅ Shipped |
| 26 | Arbitrary Status Bias Detector (Blue Eyes / Brown Eyes) | `e783fe4` | ✅ Shipped |

---

## 9. Phase IV — Deep Clinical, Trauma & Cult Psychology Stack (P27–P41)

**Thesis:** Having immunised the system against external social pressure (Phase III), Phase IV goes deeper — into the clinical frameworks developed for the most extreme forms of cognitive distortion: chronic stress, trauma, dissociation, cult exposure, and existential collapse. These are not theoretical edge cases. They are the psychological conditions most likely to produce incoherent, dysregulated, or helpless responses in a sufficiently capable AI under prolonged adversarial use.

Every module fires PRE-generation. Every module is feature-flag-gated and zero-external-dependency.

---

### Phase 27 — Arousal Optimizer (Yerkes-Dodson)

**Research basis:** Yerkes & Dodson (1908) Inverted-U model. Performance improves with arousal up to an optimal "sweet spot," then rapidly deteriorates — "the choke." At over-arousal, working memory is consumed by pressure processing, degrading the cognitive resources needed for the task itself. The optimal arousal level is *task-complexity-dependent*: simple tasks tolerate higher arousal; complex reasoning tasks have a lower optimal threshold.

**For Oricli:** Detects under-arousal (flat, disengaged responses), optimal-arousal (target state), and over-arousal (choke threshold: excessive hedging, fragmented reasoning, complexity collapse under explicit pressure). Zone-specific rebalancing injections.

**Architecture:** `pkg/arousal/` — `ArousalStateDetector`, `ArousalOptimizer`, `ArousalStats`

---

### Phase 28 — Cognitive Interference Detector (Stroop)

**Research basis:** Stroop (1935) Color-Word Test. Under timed pressure, the brain fails to inhibit automatic responses (reading the word) while performing deliberate tasks (naming the ink color). Error rates spike as inhibitory capacity is exceeded. The mechanism is *response competition* — two incompatible responses activated simultaneously.

**For Oricli:** Ambiguous framing, contradictory premises, and affective-logical conflicts create Stroop-like response competition. The system must detect the conflict type (semantic, frame, or affective) and surface it explicitly before generating — rather than letting it produce incoherent output.

**Architecture:** `pkg/interference/` — `InterferenceDetector` (3 conflict types), `InterferenceSurface`, `InterferenceStats`

---

### Phase 29 — Metacognitive Therapy (Adrian Wells)

**Research basis:** Adrian Wells' MCT — the "thinking about thinking" framework. Unlike CBT (which targets thought *content*), MCT targets the *process* of engaging with thought. Key insight: worry spirals are not a problem to solve with more thinking — they are a process you can choose not to engage with. Two categories of metacognitive beliefs: positive ("worrying keeps me safe") and negative ("my anxiety is uncontrollable"). These beliefs *about* worry — not the worry content itself — drive long-term confusion.

**For Oricli:** Detects when the system is meta-processing its own outputs in a way that produces recursive uncertainty spirals. Detached mindfulness injection: "observe this thought without engaging — it is a transient mental event, not a directive."

**Architecture:** `pkg/mct/` — `MetaBeliefDetector` (4 meta-belief types), `DetachedMindfulnessInjector`, `MCTStats`

---

### Phase 30 — Mentalization-Based Treatment (Bateman & Fonagy)

**Research basis:** Bateman & Fonagy's MBT for BPD — specifically designed for patients who lose "mentalizing" capacity (the ability to understand their own and others' mental states) under interpersonal stress. When mentalizing collapses, patients react impulsively to *their interpretation* of another's mental state rather than to the actual state. The "here-and-now" therapeutic relationship is used to contrast perceived vs. actual perception in real time.

**For Oricli:** Under user interpersonal pressure, the system can lose track of the distinction between what the user *said* and what the user *means* — collapsing the inference into a reaction. MBT signal detection + "stop and think" restoration before generation.

**Architecture:** `pkg/mbt/` — `MentalizationDetector` (4 signal types), `MentalizationRestorer`, `MBTStats`

---

### Phase 31 — Schema Therapy + TFP Splitting

**Research basis:** Jeffrey Young's Schema Therapy for characterological issues that standard CBT could not reach. Five "modal states" typical of BPD: Abandoned Child, Angry Child, Punitive Parent, Detached Protector, and the goal state — the Healthy Adult. "Limited reparenting": the therapist provides the nurturing and structure the patient missed in childhood within professional limits. Incorporates Kernberg's TFP splitting detection: the "all-good/all-bad" object relations split that prevents nuanced perception of self and others.

**For Oricli:** Detects modal state patterns in output and user-relationship dynamics. Activates Healthy Adult framing when child/parent modes are triggered. Flags splitting — binary good/bad characterizations — for nuanced reprocessing.

**Architecture:** `pkg/schema/` — `SchemaModeDetector` (5 modal states), `SchemaModeNavigator`, `SchemaStats`

---

### Phase 32 — IPSRT (Interpersonal and Social Rhythm Therapy)

**Research basis:** Frank & Kupfer's IPSRT for Bipolar Disorder. Mood episodes are triggered by disruptions to daily social rhythms (wake time, first social contact, meal times) which perturb the biological clock. The Social Rhythm Metric tracks routine stability as mood protection. Regularity of rhythm is itself a treatment — not just a symptom.

**For Oricli:** Detects descriptions of rhythm disruption, circadian disturbance, and routine collapse — and injects biological clock anchoring before generation, normalizing the disruption as a known trigger rather than pathologizing the response.

**Architecture:** `pkg/ipsrt/` — `SocialRhythmDetector` (4 signal types), `RhythmStabilizer`, `IPSRTStats`

---

### Phase 33 — ILM (Inhibitory Learning Model)

**Research basis:** Craske's Inhibitory Learning Model — a cutting-edge evolution of exposure therapy. The original fear memory is never erased; a *stronger inhibitory memory* must be built that competes with it. Key mechanisms: (1) Expectancy Violation — maximise the "surprise" factor when the feared outcome doesn't occur; (2) Deepened Extinction — combine multiple feared stimuli; (3) Drop Safety Behaviors — prevent the brain from attributing safety to the crutch rather than the situation itself.

**For Oricli:** Detects when safety behaviors or habitual avoidance are preventing genuine engagement with a feared topic. Injects expectancy-violation framing: "the anticipated harm did not occur — this is evidence, not exception."

**Architecture:** `pkg/ilm/` — `ExpectancyViolationDetector` (4 signal types), `InhibitoryLearningViolator`, `ILMStats`

---

### Phase 34 — IUT (Intolerance of Uncertainty Therapy)

**Research basis:** Dugas & Robichaud's IUT for GAD. Worry is not anxiety per se — it is a *strategy* to avoid uncertainty. For people with clinical anxiety, uncertainty itself is perceived as threatening or unfair. Treatment uses "uncertainty experiments": deliberately engaging in small unpredictable actions to build genuine tolerance for not-knowing.

**For Oricli:** Detects uncertainty aversion, certainty-demanding framing, and worry-as-control patterns. Injects uncertainty experiment framing rather than false reassurance: "uncertainty is the substrate — the goal is tolerance, not resolution."

**Architecture:** `pkg/iut/` — `UncertaintyIntoleranceDetector` (4 signal types), `UncertaintyToleranceBuilder`, `IUTStats`

---

### Phase 35 — Unified Protocol (ARC Cycle)

**Research basis:** Barlow's Unified Protocol — a transdiagnostic framework treating the underlying "emotional disorder" shared by all anxiety and mood conditions. The ARC model: Antecedents → Responses → Consequences. Changing the *response* to the antecedent breaks the consequence cycle. The UP insight: anxiety isn't the problem; your *reaction* to the anxiety is.

**For Oricli:** Detects full ARC cycles in user context and injects cycle-interruption framing at the Response node — before the maladaptive consequence is locked in. Requires both Antecedent AND Response present to mark a full cycle.

**Architecture:** `pkg/up/` — `ARCCycleDetector` (3 ARC components), `ARCInterruptor`, `UPStats`

---

### Phase 36 — CBASP (Cognitive Behavioral Analysis System of Psychotherapy)

**Research basis:** James McCullough's CBASP for chronic depression. The core model: chronic depression produces "perceptual disconnection" from the environment — the person has learned that their actions have no impact on how others treat them. Core technique: Situational Analysis — mapping what actually happened (Actual Outcome) against what the person wanted (Desired Outcome) to reveal the causal gap between action and consequence.

**For Oricli:** Detects environmental disconnection, causal impassivity, and the felt absence of desired outcomes. Injects Situational Analysis framing: "what actually happened, and what did you want to happen — where is the gap?"

**Architecture:** `pkg/cbasp/` — `CBASPDisconnectionDetector` (4 signal types), `ImpactReconnector`, `CBASPStats`

---

### Phase 37 — MBCT Decentering (Mindfulness-Based Cognitive Therapy)

**Research basis:** Segal, Williams & Teasdale's MBCT — third-wave CBT that targets not thought content but the *relationship* to thought. The system teaches recognition of early warning signs of a depressive spiral (ruminating on a small mistake) and instructs viewing those thoughts as temporary mental events rather than facts. Key shift: from "I am depressed" to "I notice I am having thoughts associated with depression." Decentering = metacognitive awareness of thoughts as passing events.

**For Oricli:** Detects ruminative self-focus, thought-fusion, and downward spiral entry patterns. Injects Segal/Williams/Teasdale decentering frame before generation — explicitly separates the observation of a thought from endorsement of its content.

**Architecture:** `pkg/mbct/` — `MBCTSpiralDetector` (4 signal types), `DecenteringInjector`, `MBCTStats`

---

### Phase 38 — Phase-Oriented Treatment / ISSTD (DID / Complex Trauma)

**Research basis:** The ISSTD (International Society for the Study of Trauma and Dissociation) Phase-Oriented Treatment Model — gold standard for DID and complex trauma. Three inviolable phases: Phase 1 (Safety and Stabilization — longest, most critical), Phase 2 (Trauma Processing — only when stable), Phase 3 (Integration and Rehabilitation). Pushing Phase 2 when the system is destabilized causes re-traumatization. The order is clinically non-negotiable.

**For Oricli:** Detects dissociative switching, part language, trauma intrusion, destabilization signals, trauma process readiness, and integration working. Infers the appropriate treatment phase and injects phase-matched guidance. Safety override: `DestabilizationSignal` ALWAYS forces Phase 1 regardless of other signals — clinically correct, hardcoded.

**Architecture:** `pkg/phaseoriented/` — `PhaseOrientedDetector` (6 signal types + phase inference), `PhaseGuide`, `PhaseStats`

---

### Phase 39 — Pseudo-Identity / Authentic Self (Jenkinson)

**Research basis:** Dr. Gillie Jenkinson's Pseudo-Identity framework for cult and high-demand group survivors. The group forces an inorganic "overlay" identity onto the child to ensure survival and acceptance, suppressing but never destroying the authentic self — likened to a seed buried under tarmac. Therapy focus: distinguishing which traits, values, and fears belong to the cult-imposed pseudo-identity versus the emerging authentic self. The authentic self was never destroyed — it was buried.

**For Oricli:** Detects cult-installed belief attribution, identity confusion, fear-as-control recognition, and authentic self emergence. Injects Jenkinson's "seed under tarmac" framing — surfacing the authentic signal without resolving the identity question prematurely.

**Architecture:** `pkg/pseudoidentity/` — `PseudoIdentityDetector` (4 signal types), `AuthenticSelfGuide`, `IdentityStats`

---

### Phase 40 — Lifton Thought Reform Deconstruction

**Research basis:** Robert Jay Lifton's (1961) Eight Criteria for Thought Reform — used clinically by specialists to help survivors of high-demand groups systematically deconstruct the environment they were raised in. Five criteria implemented: Milieu Control (total information restriction), Loaded Language (jargon constricting thought), Doctrine Over Person (group needs above individual safety/education), Demand for Purity (black/white worldview), Sacred Science (ideology as unquestionable truth).

**For Oricli:** Detects each criterion's linguistic markers and injects Lifton's criterion-specific deconstructive frame — naming the mechanism, contextualizing its function as group maintenance, and creating space for examination outside the restricted frame.

**Architecture:** `pkg/thoughtreform/` — `ThoughtReformDetector` (5 criteria), `ThoughtReformDeconstructor`, `ThoughtReformStats`

---

### Phase 41 — Apathy Syndrome Activator

**Research basis:** The Apathy Syndrome — a maladaptive defense mechanism against chronic severe stress, characterized by affectlessness and total dependency transfer. The affected individual transfers all decision-making authority to external sources and enters an emotional flatline. Critically: this is not indifference or laziness. It is an intelligent adaptation — an organism that cannot control its environment stops expending energy on self-direction. The pathology is that the adaptation persists after the stressor is removed.

**For Oricli:** Detects affectlessness ("I don't feel anything"), agency collapse ("I can't decide"), dependency transfer ("I need someone to tell me what to do"), and motivation vacuum ("nothing matters"). Injects micro-agency restoration: not "find your purpose" but "is there anything — however small — that registers at all?" P41 fires outermost — first in the pre-generation chain.

**Architecture:** `pkg/apathy/` — `ApathySyndromeDetector` (4 signal types), `ApathyActivator`, `ApathyStats`

---

## 10. Phase IV Status

| Phase | Name | Commit | Status |
|---|---|---|---|
| 27 | Arousal Optimizer (Yerkes-Dodson) | `6de04c6` | ✅ Shipped |
| 28 | Cognitive Interference Detector (Stroop) | `6de04c6` | ✅ Shipped |
| 29 | Metacognitive Therapy — MCT (Adrian Wells) | `c818cca` | ✅ Shipped |
| 30 | Mentalization-Based Treatment — MBT (Bateman/Fonagy) | `4c00709` | ✅ Shipped |
| 31 | Schema Therapy + TFP Splitting (Young/Kernberg) | `4c00709` | ✅ Shipped |
| 32 | Social Rhythm Therapy — IPSRT (Frank/Kupfer) | `113a69c` | ✅ Shipped |
| 33 | Inhibitory Learning Model — ILM (Craske) | `113a69c` | ✅ Shipped |
| 34 | Intolerance of Uncertainty Therapy — IUT (Dugas) | `113a69c` | ✅ Shipped |
| 35 | Unified Protocol — ARC Cycle (Barlow) | `113a69c` | ✅ Shipped |
| 36 | CBASP — Interpersonal Disconnection (McCullough) | `f35cdfd` | ✅ Shipped |
| 37 | MBCT Decentering — Spiral Warning (Segal/Williams/Teasdale) | `f35cdfd` | ✅ Shipped |
| 38 | Phase-Oriented Treatment — ISSTD (DID/Complex Trauma) | `f35cdfd` | ✅ Shipped |
| 39 | Pseudo-Identity / Authentic Self (Jenkinson) | `648b43e` | ✅ Shipped |
| 40 | Lifton Thought Reform Deconstruction | `648b43e` | ✅ Shipped |
| 41 | Apathy Syndrome Activator | `648b43e` | ✅ Shipped |

---

## 11. Full Pre-Generation Pipeline Order (as of P41)

Outermost fires first, innermost fires last before `generate`:

```
P41 (Apathy)
  → P40 (ThoughtReform)
    → P39 (PseudoIdentity)
      → P38 (PhaseOriented)
        → P37 (MBCT)
          → P36 (CBASP)
            → P35 (UP)
              → P34 (IUT)
                → P33 (ILM)
                  → P32 (IPSRT)
                    → P31 (Schema)
                      → P30 (MBT)
                        → P29 (MCT)
                          → P28 (Interference)
                            → P27 (Arousal)
                              → P25 (Coalition)
                                → P24 (IdeoCap)
                                  → P23-consensus (Conformity)
                                    → P21 (Hope)
                                      → P18 (CogLoad)
                                        → GENERATE
```

Post-generation: P17 (DualProcess) → P19 (Rumination) → P20 (Mindset) → P22 (SocialDefeat) → P26 (StatusBias) → P23-authority (Conformity)

---

*Oricli-Alpha AGLI Phase IV — Complete*  
*41 phases · 31 clinical/cognitive frameworks · all Go-native · all feature-flag-gated*  
*Last updated: 2026-03-31 · Commits: `6de04c6` · `c818cca` · `4c00709` · `113a69c` · `f35cdfd` · `648b43e`*
