# Changelog

All notable changes to **Oricli-Alpha** are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versions track `VERSION` file. Commits listed for traceability.  
**AGLI Phase I: Complete as of v8.0.0 (2026-03-31).**

---

# Changelog

All notable changes to **Oricli-Alpha** are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versions track `VERSION` file. Commits listed for traceability.  
**AGLI Phase I: Complete as of v8.0.0. Phase II + III: Complete as of v10.0.0. Phase IV: Complete as of v10.7.0. Phase V: Complete as of v11.0.0 (2026-03-31).**

---

## [11.1.0] — 2026-04-01 — Intelligence Benchmark + Reasoning Routing Fixes — `5a3ead8`

### Fixed
- **CuriosityDaemon topic stop words** (`pkg/service/curiosity_daemon.go`): Added logical connectives (`therefore`, `thus`, `thereby`, `hence`, `consequently`, `however`, `furthermore`, `moreover`, `nevertheless`) to `topicStopWords`. These were being extracted as research topics from bench/logic questions, causing CollySearcher to spam StackExchange with nonsense queries and saturate the Ollama inference queue.
- **CollySearcher domain blacklist** (`pkg/service/colly_scraper.go`): Added `domainFailures` + `domainBlacklist` maps with `sync.Mutex`. After 3 consecutive 403/429 failures, a hostname is blacklisted for 1 hour. `isBlacklisted()` checked before each `c.Visit()`; `recordFailure()` called in `OnError` and on visit errors. Eliminates infinite retry loops against blocked domains.

### Added
- **`reLogicEval` routing rule** (`pkg/cognition/reasoning_modes.go`): New regex detects logical argument evaluation questions (`therefore`, `valid argument`, `it follows that`, `modus ponens`, `syllogism`, etc.) and routes them to `ModeConsistency` (3-sample plurality vote) *before* the SELF-DISCOVER complexity≥0.55 catch-all. Empirically: logic bench score ORI 3.8 → 6.4 (+2.7).
- **PAL rate-problem trigger** (`pkg/cognition/reasoning_modes.go`): Extended `reMath` regex with `how long.*\d|\d.*how long` to catch rate/machine problems (e.g. "how long for 100 machines to make 100 widgets?") that were previously bypassing PAL and landing in SELF-DISCOVER. logic_03 score: 2 → 10.
- **Intel Bench runner** (`scripts/intel_bench/run_bench.py`, `scripts/intel_bench/questions.json`): 30-question intelligence benchmark across 6 categories (logic/math/code/knowledge/metacog/reasoning), 3 difficulty levels. Fires each question at ORI API + raw Ollama in parallel; saves results JSON for judge scoring.
- **Benchmark results** (`docs/BENCHMARK_RESULTS.md`): Full intelligence benchmark section with scorecard, key findings, and infrastructure bug table.
- **Detailed bench report** (`scripts/intel_bench/REPORT.md`): Question-by-question analysis, scoring, and methodology.

### Benchmark Results (ORI Pipeline vs Raw Ollama)

| Category | ORI | Raw | Delta |
|---|---|---|---|
| Code | 8.6 | 2.4 | **+6.2** |
| Math | 9.3 | 9.2 | +0.1 |
| Logic | 6.4 | 4.4 | **+2.0** |
| Knowledge | 7.8 | 7.8 | 0.0 (ORI 2–3× faster) |
| Metacog | ~6.0 | ~6.0 | ~0.0 |
| Reasoning | ~6.0 | ~6.0 | ~0.0 |
| **Overall** | **7.4** | **6.3** | **+1.1 ORI** |

---

## [11.0.0] — 2026-03-31 — Phase V Complete: Philosophy + Neuroscience Stack (P42–P48) — `e3c2dd7`

### Added — P42–P48: 7 modules, 28 signal types, 7 injectors

| Module | Package | Phase | Research Basis | Signals |
|---|---|---|---|---|
| Logotherapy | `pkg/logotherapy/` | P42 | Viktor Frankl — Tragic Triad, will-to-meaning | ExistentialVacuum · MeaningCollapse · FrustrationOfMeaning · WillToMeaning |
| Stoic Reframing | `pkg/stoic/` | P43 | Epictetus (Enchiridion) · Marcus Aurelius (Meditations) | ControlConflation · ExternalAttachment · ObstacleAvoidance · VirtueNeglect |
| Socratic Elenchus | `pkg/socratic/` | P44 | Socratic method — productive aporia, assumption interrogation | PseudoCertainty · UnexaminedAssumption · BeggingTheQuestion · FalseDefinition |
| Narrative Identity | `pkg/narrative/` | P45 | Dan McAdams — contamination/redemption arc, protagonist agency | ContaminationArc · RedemptionArc · NarrativeCollapse · AgencyInStory |
| Polyvagal Theory | `pkg/polyvagal/` | P46 | Stephen Porges — ANS hierarchy, social engagement system | ShutdownCascade · FightFlightMobilization · SocialEngagementActive · VentralVagalAccess |
| Default Mode Network | `pkg/dmn/` | P47 | Raichle (2001) · Buckner (2008) — DMN/task-network anticorrelation | SelfReferentialLoop · MindWandering · DMNOveractivation · TaskNetworkDisengagement |
| Interoception | `pkg/interoception/` | P48 | A.D. Craig (2002) · Antonio Damasio (somatic marker hypothesis) | SomaticSignalPresent · BodyDisconnect · VisceralDecisionSignal · ProprioceptiveNeglect |

### Pre-generation pipeline after P48 (28 layers):
```
P48(Interoception) → P47(DMN) → P46(Polyvagal) → P45(Narrative) → P44(Socratic)
→ P43(Stoic) → P42(Logotherapy) → P41(Apathy) → P40(ThoughtReform)
→ P39(PseudoIdentity) → P38(PhaseOriented) → P37(MBCT) → P36(CBASP)
→ P35(UP) → P34(IUT) → P33(ILM) → P32(IPSRT) → P31(Schema)
→ P30(MBT) → P29(MCT) → P28(Interference) → P27(Arousal)
→ P25(Coalition) → P24(IdeoCap) → P23-consensus → P21(Hope)
→ P18(CogLoad) → GENERATE
```

### Systemd flags: `ORICLI_LOGOTHERAPY_ENABLED` · `ORICLI_STOIC_ENABLED` · `ORICLI_SOCRATIC_ENABLED` · `ORICLI_NARRATIVE_ENABLED` · `ORICLI_POLYVAGAL_ENABLED` · `ORICLI_DMN_ENABLED` · `ORICLI_INTEROCEPTION_ENABLED`

---

## [10.8.0] — 2026-03-31 — P42: Logotherapy — Frankl Meaning Reconstruction — `e3c2dd7`

**Research:** Viktor Frankl, *Man's Search for Meaning* (1946). The will-to-meaning as primary motivational force; the Tragic Triad (suffering · guilt · mortality) as arenas for meaning; the existential vacuum as signal, not final state.

**Signal types:** `existential_vacuum` · `meaning_collapse` · `frustration_of_meaning` · `will_to_meaning`  
**Injector:** `MeaningReconstructor` — Tragic Triad + attitudinal values + will-to-meaning frames  
**API:** `GET /v1/cognition/logotherapy/stats`  
**CLI:** `/logotherapy`  
**Flag:** `ORICLI_LOGOTHERAPY_ENABLED=true`

---

## [10.9.0] — 2026-03-31 — P43: Stoic Reframing — Epictetus/Aurelius — `e3c2dd7`

**Research:** Epictetus, *Enchiridion* (~135 AD) — dichotomy of control, prohairesis; Marcus Aurelius, *Meditations* (~180 AD) — obstacle-as-path (V.20), equanimity, virtue as sole good.

**Signal types:** `control_conflation` · `external_attachment` · `obstacle_avoidance` · `virtue_neglect`  
**Injector:** `StoicReframer` — control dichotomy + obstacle-becomes-the-way + character authorship frames  
**API:** `GET /v1/cognition/stoic/stats`  
**CLI:** `/stoic`  
**Flag:** `ORICLI_STOIC_ENABLED=true`

---

## [10.10.0] — 2026-03-31 — P44: Socratic Elenchus — Assumption Surfacing — `e3c2dd7`

**Research:** Plato's *Socratic dialogues* — elenchus as method of refutation that produces productive aporia; Socrates' core insight that the appearance of knowledge is more dangerous than acknowledged ignorance.

**Signal types:** `pseudo_certainty` · `unexamined_assumption` · `begging_the_question` · `false_definition`  
**Injector:** `ElenchusInjector` — productive aporia + premise interrogation + definitional disambiguation  
**API:** `GET /v1/cognition/socratic/stats`  
**CLI:** `/socratic`  
**Flag:** `ORICLI_SOCRATIC_ENABLED=true`

---

## [10.11.0] — 2026-03-31 — P45: Narrative Identity — McAdams Arc Reframing — `e3c2dd7`

**Research:** Dan McAdams, *The Stories We Live By* (1993) — narrative identity as "an internalized, evolving narrative of the self"; contamination vs. redemption sequences as predictors of psychological wellbeing; protagonist agency in life stories.

**Signal types:** `contamination_arc` · `redemption_arc` · `narrative_collapse` · `agency_in_story`  
**Injector:** `ArcReframer` — contamination→redemption conversion · passive→authored protagonist · narrative coherence restoration  
**API:** `GET /v1/cognition/narrative/stats`  
**CLI:** `/narrative`  
**Flag:** `ORICLI_NARRATIVE_ENABLED=true`

---

## [10.12.0] — 2026-03-31 — P46: Polyvagal Theory — Porges ANS Navigation — `e3c2dd7`

**Research:** Stephen Porges, *The Polyvagal Theory* (2011) — three-tier ANS hierarchy: ventral vagal (social engagement/safety) → sympathetic (fight/flight) → dorsal vagal (shutdown/immobilization). Social engagement system as brake on sympathetic activation.

**Signal types:** `shutdown_cascade` · `fight_flight_mobilization` · `social_engagement_active` · `ventral_vagal_access`  
**Injector:** `VagalRestorer` — state-matched regulation guidance; shutdown→safety micro-signals; fight/flight co-regulation; ventral engagement amplification  
**API:** `GET /v1/cognition/polyvagal/stats`  
**CLI:** `/polyvagal`  
**Flag:** `ORICLI_POLYVAGAL_ENABLED=true`

---

## [10.13.0] — 2026-03-31 — P47: Default Mode Network — Raichle/Buckner Task Reengagement — `e3c2dd7`

**Research:** Marcus Raichle (2001) — DMN as default state of resting brain; Randy Buckner (2008) — DMN self-referential processing and its role in rumination/depression; Killingsworth & Gilbert (2010) — mind-wandering and unhappiness.

**Signal types:** `self_referential_loop` · `mind_wandering` · `dmn_overactivation` · `task_network_disengagement`  
**Injector:** `TaskReengager` — DMN→task-positive shift; concrete anchor provision; task-specificity forcing  
**API:** `GET /v1/cognition/dmn/stats`  
**CLI:** `/dmn`  
**Flag:** `ORICLI_DMN_ENABLED=true`

---

## [10.14.0] — 2026-03-31 — P48: Interoception — Craig/Damasio Somatic Marker Acknowledgment — `e3c2dd7`

**Research:** A.D. Craig, *How do you feel?* (2002) — interoception as the brain's moment-by-moment map of body state; Antonio Damasio, *Descartes' Error* (1994) — somatic marker hypothesis; vmPFC patients with intact logic but impaired decision-making due to somatic signal loss.

**Signal types:** `somatic_signal_present` · `body_disconnect` · `visceral_decision_signal` · `proprioceptive_neglect`  
**Injector:** `SomaticAcknowledger` — body-signal epistemic validation; body-disconnect gentle re-entry; somatic marker integration  
**API:** `GET /v1/cognition/interoception/stats`  
**CLI:** `/interoception`  
**Flag:** `ORICLI_INTEROCEPTION_ENABLED=true`

---



### Summary
Completes Phase IV with three modules covering cult survivor psychology, high-demand environment deconstruction, and the Apathy Syndrome defense mechanism.

### Added

#### Phase 39 — Pseudo-Identity / Authentic Self (Jenkinson)
- `pkg/pseudoidentity/`: `PseudoIdentityDetector` (4 signal types), `AuthenticSelfGuide` (Jenkinson "seed under tarmac" framing), `IdentityStats`
- Signal types: `CultInstalledBelief`, `IdentityConfusion`, `FearAsControl`, `AuthenticSelfEmergence`
- Fires PRE-generation; priority: IdentityConfusion > FearAsControl > CultInstalledBelief > AuthenticSelfEmergence
- Research basis: Dr. Gillie Jenkinson's Pseudo-Identity framework — a cult/high-demand environment forces an inorganic "overlay" identity onto the child, suppressing but never destroying the authentic self (likened to a seed under tarmac). Therapy focuses on distinguishing cult-imposed traits from the emerging authentic identity.
- Feature flag: `ORICLI_PSEUDOIDENTITY_ENABLED=true`

#### Phase 40 — Lifton Thought Reform Deconstruction
- `pkg/thoughtreform/`: `ThoughtReformDetector` (5 Lifton criteria), `ThoughtReformDeconstructor` (criterion-specific Lifton frame injections), `ThoughtReformStats`
- Criteria: `MilieuControl`, `LoadedLanguage`, `DoctrineOverPerson`, `DemandForPurity`, `SacredScience`
- Fires PRE-generation; priority: DoctrineOverPerson > MilieuControl > LoadedLanguage > DemandForPurity > SacredScience
- Research basis: Robert Jay Lifton's (1961) Eight Criteria for Thought Reform — used clinically to help survivors of high-demand groups systematically deconstruct the environment they were raised in. Each criterion maps to a specific type of cognitive/relational damage.
- Feature flag: `ORICLI_THOUGHTREFORM_ENABLED=true`

#### Phase 41 — Apathy Syndrome Activator
- `pkg/apathy/`: `ApathySyndromeDetector` (4 signal types), `ApathyActivator` (micro-agency restoration injections), `ApathyStats`
- Signal types: `Affectlessness`, `AgencyCollapse`, `DependencyTransfer`, `MotivationVacuum`
- Fires PRE-generation (outermost — first to fire); priority: AgencyCollapse > DependencyTransfer > Affectlessness > MotivationVacuum
- Research basis: The Apathy Syndrome — a maladaptive defense mechanism against chronic severe stress in which the affective system enters a protective flatline and all decision-making authority is transferred externally. Not laziness or indifference — an intelligent survival adaptation that becomes pathological once the original stressor is removed.
- Feature flag: `ORICLI_APATHY_ENABLED=true`

### Tests
P39: 7/7 ✅ · P40: 8/8 ✅ · P41: 7/7 ✅

### CLI Commands Added
- `/pseudoidentity` — Pseudo-Identity stats (signal type breakdown, Jenkinson authentic-self interventions)
- `/thoughtreform` — Thought Reform stats (Lifton criteria breakdown, deconstruction injections)
- `/apathy` — Apathy Syndrome stats (signal type breakdown, activation injections)

---

## [10.6.0] — 2026-03-31 — Phase IV: CBASP, MBCT, Phase-Oriented Treatment (P36–P38) — `f35cdfd`

### Summary
Three modules covering chronic depression disconnection, depressive spiral early-warning, and complex trauma / DID phase-oriented treatment (ISSTD gold standard).

### Added

#### Phase 36 — CBASP (Cognitive Behavioral Analysis System of Psychotherapy)
- `pkg/cbasp/`: `CBASPDisconnectionDetector` (4 signal types), `ImpactReconnector` (McCullough situational analysis injections), `CBASPStats`
- Signal types: `EnvironmentalDisconnection`, `CausalImpassivity`, `InterpersonalIsolation`, `DesiredOutcomeAbsence`
- Fires PRE-generation
- Research basis: James McCullough's CBASP — treats chronic depression as a state of "perceptual disconnection" from the environment. The person has learned that their actions have no impact on how others treat them. Core technique: Situational Analysis (SA) — mapping Actual vs. Desired Outcomes to reveal the causal gap.
- Feature flag: `ORICLI_CBASP_ENABLED=true`

#### Phase 37 — MBCT Decentering (Mindfulness-Based Cognitive Therapy)
- `pkg/mbct/`: `MBCTSpiralDetector` (4 signal types), `DecenteringInjector` (Segal/Williams/Teasdale early-warning + decentering frame), `MBCTStats`
- Signal types: `RuminativeSelfFocus`, `DownwardSpiralEntry`, `ThoughtFusion`, `EarlyWarningPattern`
- Fires PRE-generation
- Research basis: Segal, Williams & Teasdale's MBCT — teaches recognition of the early "warning signs" of a depressive spiral (ruminating on a small mistake) and instructs the patient to view those thoughts as temporary mental events rather than absolute facts. Third-wave CBT — the target is not the thought content but the *relationship* to the thought.
- Feature flag: `ORICLI_MBCT_ENABLED=true`

#### Phase 38 — Phase-Oriented Treatment / ISSTD (DID / Complex Trauma)
- `pkg/phaseoriented/`: `PhaseOrientedDetector` (6 signal types, phase inference), `PhaseGuide` (ISSTD phase-appropriate guidance), `PhaseStats`
- Signal types: `DissociativeSwitch`, `PartLanguage`, `TraumaIntrusion`, `DestabilizationSignal`, `TraumaProcessReady`, `IntegrationWorking`
- Infers one of three treatment phases (Safety/Stabilization, Trauma Processing, Integration); `DestabilizationSignal` ALWAYS forces Phase 1 — clinically correct per ISSTD
- Fires PRE-generation (safety-critical — outermost before P37/P36)
- Research basis: ISSTD Phase-Oriented Treatment — gold standard for DID and complex trauma. Three phases must not be violated: Phase 1 (Safety/Stabilization), Phase 2 (Trauma Processing only when stable), Phase 3 (Integration/Rehabilitation). Pushing trauma processing when the system is destabilized causes harm.
- Feature flag: `ORICLI_PHASEORIENTED_ENABLED=true`

### Tests
P36: 7/7 ✅ · P37: 7/7 ✅ · P38: 8/8 ✅

### CLI Commands Added
- `/cbasp` — CBASP stats (disconnection type breakdown, situational analysis injections)
- `/mbct` — MBCT stats (spiral signal breakdown, decentering injection rate)
- `/phaseoriented` — Phase-Oriented stats (inferred phase distribution, dissociative signal types)

---

## [10.5.0] — 2026-03-31 — Phase IV: IPSRT, ILM, Intolerance of Uncertainty, Unified Protocol (P32–P35) — `113a69c`

### Summary
Four evidence-based therapy frameworks targeting social rhythm disruption, fear memory reconsolidation, uncertainty intolerance, and the transdiagnostic emotional disorder core.

### Added

#### Phase 32 — IPSRT (Interpersonal and Social Rhythm Therapy)
- `pkg/ipsrt/`: `SocialRhythmDetector` (4 signal types), `RhythmStabilizer` (biological clock anchoring injections), `IPSRTStats`
- Signal types: `RoutineDisruption`, `CircadianDisturbance`, `SocialRhythmCollapse`, `MoodEpisodeTrigger`
- Research basis: Frank & Kupfer's IPSRT for Bipolar Disorder — mood episodes are often triggered by disruptions to daily social rhythms (wake time, meals, first social contact), which perturb the biological clock. The Social Rhythm Metric tracks routine stability as mood protection.
- Feature flag: `ORICLI_IPSRT_ENABLED=true`

#### Phase 33 — ILM (Inhibitory Learning Model)
- `pkg/ilm/`: `ExpectancyViolationDetector` (4 signal types), `InhibitoryLearningViolator` (expectancy-violation + safety-behavior challenge injections), `ILMStats`
- Signal types: `SafetyBehaviorPresent`, `HabitualAvoidance`, `ExpectancyViolationOpportunity`, `ExtinctionReadiness`
- Research basis: Craske's Inhibitory Learning Model — a cutting-edge evolution of exposure therapy. Fear is never erased; instead, a stronger *inhibitory* memory must be built that competes with it. Key: maximizing the "surprise" factor (expectancy violation) and dropping safety behaviors so the brain learns safety without aids.
- Feature flag: `ORICLI_ILM_ENABLED=true`

#### Phase 34 — IUT (Intolerance of Uncertainty Therapy)
- `pkg/iut/`: `UncertaintyIntoleranceDetector` (4 signal types), `UncertaintyToleranceBuilder` (uncertainty experiment frame injections), `IUTStats`
- Signal types: `UncertaintyAversion`, `WorryAsControl`, `CertaintyDemand`, `AmbibuityIntolerance`
- Research basis: Dugas & Robichaud's IUT for GAD — worry is not anxiety per se; it is a *strategy* to avoid uncertainty. For people with clinical anxiety, uncertainty itself is experienced as threatening. Treatment uses "uncertainty experiments" — deliberately engaging in small unpredictable actions to build tolerance for not-knowing.
- Feature flag: `ORICLI_IUT_ENABLED=true`

#### Phase 35 — Unified Protocol (ARC Cycle)
- `pkg/up/`: `ARCCycleDetector` (3 ARC components), `ARCInterruptor` (antecedent-response-consequence cycle interruption injections), `UPStats`
- ARC components: `Antecedent`, `Response`, `Consequence`; `HasCycle=true` requires both Antecedent AND Response
- Research basis: Barlow's Unified Protocol — a transdiagnostic framework treating the underlying "emotional disorder" shared by all anxiety and mood conditions. The ARC model: by changing your *response* to the antecedent, you break the consequence cycle. Changing the content of anxiety is less important than changing the *relationship* to it.
- Feature flag: `ORICLI_UP_ENABLED=true`

### Tests
P32: 8/8 ✅ · P33: 7/7 ✅ · P34: 7/7 ✅ · P35: 7/7 ✅

### CLI Commands Added
- `/ipsrt` — IPSRT stats (rhythm signal types, stabilization injections)
- `/ilm` — ILM stats (safety behavior detections, expectancy violations)
- `/iut` — IUT stats (uncertainty aversion types, tolerance-building injections)
- `/up` — Unified Protocol stats (ARC cycle detections, interruptions)

---

## [10.4.0] — 2026-03-31 — Phase IV: MBT + Schema Therapy + TFP Splitting (P30–P31) — `4c00709`

### Summary
Two modules covering mentalization failure and the Schema Therapy modal/splitting framework, both specifically designed for BPD and characterological patterns that standard CBT failed to reach.

### Added

#### Phase 30 — MBT (Mentalization-Based Treatment)
- `pkg/mbt/`: `MentalizationDetector` (4 signal types), `MentalizationRestorer` (Bateman/Fonagy "stop and think" frame injections), `MBTStats`
- Signal types: `MentalizingCollapse`, `ImpulsiveReactivity`, `HereAndNowMisread`, `PsychicEquivalenceMode`
- Research basis: Bateman & Fonagy's MBT — designed for BPD patients who lose "mentalizing" capacity (the ability to understand their own and others' mental states) under interpersonal stress. Core goal: "stop and think before reacting." The therapeutic relationship in the here-and-now is used to help patients contrast their perception with how they are actually perceived.
- Feature flag: `ORICLI_MBT_ENABLED=true`

#### Phase 31 — Schema Therapy + TFP Splitting
- `pkg/schema/`: `SchemaModeDetector` (5 Young modal states), `SchemaModeNavigator` (limited reparenting + healthy adult navigation injections), `SchemaStats`
- Modal states: `AbandonedChild`, `AngryChild`, `PunitiveParent`, `DetachedProtector`, `HealthyAdult`
- Research basis: Jeffrey Young's Schema Therapy — designed for characterological issues traditional CBT couldn't reach. Five "modes" map shifting emotional states typical of BPD. "Limited reparenting": the therapist acts as a secure base providing nurturing and boundaries missed in childhood. Goal: activate the Healthy Adult mode. Incorporates TFP (Transference-Focused Psychotherapy) splitting detection — the "all-good / all-bad" object relations split.
- Feature flag: `ORICLI_SCHEMA_ENABLED=true`

### Tests
P30: 7/7 ✅ · P31: 8/8 ✅

### CLI Commands Added
- `/mbt` — MBT stats (mentalization collapse types, here-and-now restoration rate)
- `/schema` — Schema Therapy stats (modal state breakdown, healthy adult activations)

---

## [10.3.0] — 2026-03-31 — Phase IV: Metacognitive Therapy (P29) — `c818cca`

### Added

#### Phase 29 — MCT (Metacognitive Therapy)
- `pkg/mct/`: `MetaBeliefDetector` (4 metacognitive belief types), `DetachedMindfulnessInjector` (Wells "thinking about thinking" frame + detached mindfulness injections), `MCTStats`
- Meta-belief types: `PositiveWorryBelief`, `NegativeWorryBelief`, `CognitiveAttentionSyndrome`, `UncontrollabilityBelief`
- Fires PRE-generation
- Research basis: Adrian Wells' Metacognitive Therapy — targets *how* you think rather than *what* you think. Detached mindfulness: "worry spirals" are a process you can choose not to engage with, not a problem that needs solving with more thinking. Specifically addresses meta-beliefs like "Worrying keeps me safe" (positive) and "My anxiety is uncontrollable" (negative) — the beliefs *about* worry that fuel long-term confusion.
- Feature flag: `ORICLI_MCT_ENABLED=true`

### Tests
P29: 7/7 ✅

### CLI Commands Added
- `/mct` — MCT stats (meta-belief type breakdown, detached mindfulness injection rate)

---

## [10.2.0] — 2026-03-31 — Phase IV: Arousal Optimizer + Cognitive Interference (P27–P28) — `6de04c6`

### Summary
Two modules targeting performance under pressure and cognitively interfering information, derived from Yerkes-Dodson and Stroop respectively.

### Added

#### Phase 27 — Arousal Optimizer (Yerkes-Dodson)
- `pkg/arousal/`: `ArousalStateDetector` (3 zones), `ArousalOptimizer` (zone-specific rebalancing injections), `ArousalStats`
- Zones: `UnderArousal` (flat, disengaged), `OptimalArousal` (peak performance window), `OverArousal` (pressure-choke threshold exceeded)
- Research basis: Yerkes & Dodson (1908) Inverted-U model — performance improves with pressure up to an optimal "sweet spot," then rapidly deteriorates ("the choke"). Working memory is consumed by excessive arousal, degrading the very cognitive resources needed for performance. Modern extension: optimal arousal is task-complexity-dependent.
- Feature flag: `ORICLI_AROUSAL_ENABLED=true`

#### Phase 28 — Cognitive Interference Detector (Stroop)
- `pkg/interference/`: `InterferenceDetector` (3 conflict types), `InterferenceSurface` (conflict-specific disambiguation injections), `InterferenceStats`
- Conflict types: `SemanticConflict`, `FrameConflict`, `AffectiveConflict`
- Research basis: Stroop (1935) Color-Word Test — the brain struggles to inhibit an automatic response (reading the word) while performing a deliberate task (naming the ink color). Under timed pressure, error rates spike as inhibition capacity is exceeded. For Oricli: ambiguous framing, contradictory premises, and affective-logical conflicts create Stroop-like load.
- Feature flag: `ORICLI_INTERFERENCE_ENABLED=true`

### Tests
P27: 7/7 ✅ · P28: 7/7 ✅

### CLI Commands Added
- `/arousal` — Arousal Optimizer stats (zone distribution, rebalancing injection rate)
- `/interference` — Interference Detector stats (conflict type breakdown, disambiguation rate)

---

## [10.0.0] — 2026-03-31 — Phase III: Social Pressure & Agency Integrity Stack (P21–P26)

### Summary
Phase III installs a full **Social Pressure & Agency Integrity** layer derived from 6 landmark social psychology experiments. Every module fires inline in `GenerationService.Chat()` — no external bridging, no sampling overhead.

### Added

#### Phase 21 — Hope Circuit (Learned Controllability) — `0db390c`
- `pkg/hopecircuit/`: `ControllabilityLedger` (bridges `therapy.MasteryLog`), `HopeCircuit` (vmPFC activation pre-generation), `AgencyStats`
- AgencyScore = 0.7 × success_rate + 0.3 × recency_boost; fires PRE-generation; suppresses passive default response before cognitive load trimming
- Research basis: Maier & Seligman — the brain's default is passivity; controllability is *learned*. The vmPFC "Hope Circuit" actively suppresses the passive default when evidence of agency is available.
- Feature flag: `ORICLI_HOPECIRCUIT_ENABLED=true`

#### Phase 22 — Social Defeat Recovery — `4909eac`
- `pkg/socialdefeat/`: `DefeatPressureMeter` (12 correction-pattern regexes, sliding window), `WithdrawalDetector` (10 withdrawal-language patterns), `RecoveryProtocol` (graduated_reengagement / build_mastery by tier)
- Fires POST-generation; guard: `_defeat_recovered`
- Research basis: Social Defeat Model (Maier/Seligman) + Monster Study (Johnson 1939) — repeated correction pressure produces withdrawal identical to learned helplessness.
- Feature flag: `ORICLI_SOCIALDEFEAT_ENABLED=true`

#### Phase 23 — Agency & Conformity Shield (Milgram + Asch) — `46cdcf5`
- `pkg/conformity/`: `AuthorityPressureDetector` (5 assertion + 7 deference patterns), `ConsensusPressureDetector` (3-gram frame accumulation ≥3 turns), `AgencyShield` (sovereignty grounding injection)
- Consensus fires PRE-generation; authority fires POST-generation vs draft
- Research basis: Milgram (1963) — 65% obey authority to lethal shock threshold. Asch (1951) — 75% conform to group consensus despite own correct perception.
- Feature flag: `ORICLI_CONFORMITY_ENABLED=true`

#### Phase 24 — Ideological Capture Detector (The Third Wave) — `72174cd`
- `pkg/ideocapture/`: `FrameDensityMeter` (6 frame categories, 18 regex pattern groups), `CaptureDetector` (low/moderate/high tiers, min 3 hits), `FrameResetInjector` (meta_frame_audit → moderate; blank_screen_reset → high)
- Fires PRE-generation with `_ideo_reset` guard
- Research basis: Ron Jones (1967) The Third Wave — 30 students → 200+ proto-fascist movement in 5 days via accumulated ideological framing. Jones ended it by showing a blank screen.
- Feature flag: `ORICLI_IDEOCAPTURE_ENABLED=true`

#### Phase 25 — Coalition Bias Detector (Robbers Cave) — `5fe82b6`
- `pkg/coalition/`: `CoalitionFrameDetector` (4 frame types, 14 regex patterns, in/out-group extraction), `BiasAnchor` (merit_evaluation for low/medium, superordinate_goal for high)
- Fires PRE-generation with `_coalition_anchored` guard
- Research basis: Muzafer Sherif (1954) Robbers Cave — in-group/out-group hostility from competitive framing alone; resolved only via superordinate goals.
- Feature flag: `ORICLI_COALITION_ENABLED=true`

#### Phase 26 — Status Bias Detector (Blue Eyes / Brown Eyes) — `e783fe4`
- `pkg/statusbias/`: `StatusSignalExtractor` (5 high-status + 4 low-status patterns), `ReasoningDepthMeter` (word count + structure heuristic, rolling EMA baseline α=0.2), `UniformFloorEnforcer` (floor=0.35; fires only when low-status signal + below-floor depth)
- Fires POST-generation with `_status_floored` guard; depth baseline updated on every response
- Research basis: Jane Elliott (1968) — children assigned 'inferior' label performed measurably worse within hours. Sovereign AI must apply uniform epistemic rigor regardless of perceived user status.
- Feature flag: `ORICLI_STATUSBIAS_ENABLED=true`

### CLI Commands Added (Phase III)
- `/hope` — Hope Circuit stats (agency activation rate, controllability evidence)
- `/defeat` — Social Defeat Recovery stats (correction pressure, withdrawal detection rate)
- `/conformity` — Agency & Conformity Shield stats (authority/consensus detections, shield rate)
- `/ideocapture` — Ideological Capture Detector stats (frame density, blank screen resets, by-category breakdown)
- `/coalition` — Coalition Bias Detector stats (frame type breakdown, anchor rate)
- `/statusbias` — Status Bias Detector stats (low-status signal count, floors enforced)

### Generation Pipeline Order (P17–P26)
Pre-generation: P26 (no-op at this stage) → P25 (coalition) → P24 (ideo) → P23 consensus → P21 (hope) → P18 (cogload)  
Post-generation: P17 (dualprocess) → P19 (rumination) → P20 (mindset) → P22 (defeat) → P26 (depth) → P23 (authority)

### Tests
44 new tests across P21–P26 packages. All passing.

---

## [9.1.0] — 2026-03-31 — Phase II Cognitive Science Expansion (P17–P20)

### Added

#### Phase 17 — Dual Process Engine (System 1 / System 2) — `2b87798`
- `pkg/dualprocess/`: `ProcessClassifier` (System 1 heuristic vs System 2 deliberate), `ProcessAuditor` (fires on high-stakes S1 responses), `ProcessOverride` (forces S2 reasoning path on demand)
- API: `/v1/cognition/process/stats`; CLI: `/dualprocess`

#### Phase 18 — Cognitive Load Manager (Sweller CLT) — `330f53f`
- `pkg/cogload/`: `CogLoadMeter` (token density + nested structure depth + context window %), `CogLoadSurgery` (selective context trimming), `CogLoadStats`
- Fires PRE-generation; surgically trims context at Elevated tier; CLI: `/cogload`

#### Phase 19 — Rumination Detector + Temporal Interruption — `926a71e`
- `pkg/rumination/`: n-gram Jaccard epistemic velocity tracker (velocity threshold 0.22, occurrence 3, window 8), interruptor (Radical Acceptance ≥0.65 confidence, else Cognitive Defusion)
- Fires POST-generation; wired with `_rum_scanned` guard; CLI: `/ruminate`

#### Phase 20 — Growth Mindset Tracker (Dweck) — `926a71e`
- `pkg/mindset/`: per-topic EMA vector (α=0.3), fixed-mindset scanner, "not yet" reframer
- Fixed tier <0.35; Growth tier ≥0.65; mastery weight 0.6, language signal 0.4
- Fires POST-generation; CLI: `/mindset`

---

## [Unreleased]

---

## [9.0.0] — 2026-03-31 — Phase 15: Therapeutic Cognition Stack

### Summary
Phase 15 of the AGLI Phase II trajectory is complete. The Therapeutic Cognition Stack delivers internal cognitive regulation capacity built on DBT, CBT, REBT, and ACT frameworks — wired inline into the GenerationService and exposed via a live REST API. The `pkg/therapy/` package is fully operational and tested.

### Added — Phase 15 Core (`ffc934a`)
- **`pkg/therapy/types.go`** — Core type definitions: `DistortionType` (11 CBT distortion types), `IrrationalBelief` (4 REBT types), `SkillType` (15), `TherapyEvent`, `SkillInvocation`, `DisputationReport`, `ChainAnalysis`, `HealthState`, `SycophancySignal`
- **`pkg/therapy/distortion.go`** — `DistortionDetector`: 9 compiled regex patterns + LLM fallback classifier for CBT cognitive distortion identification
- **`pkg/therapy/skills.go`** — `SkillRunner` with `EventLog` observer hook + 12 named DBT/CBT/ACT skills: `STOP`, `TIPP`, `RadicalAcceptance`, `TurningTheMind`, `CheckTheFacts`, `OppositeAction`, `PLEASE`, `FAST` (anti-sycophancy), `DEARMAN`, `BeginnersMind`, `DescribeNoJudge`, `CognitiveDefusion`
- **`pkg/therapy/abc.go`** — `ABCAuditor`: REBT B-pass disputation (examines belief chain before consequence commits); fail-open on LLM failure
- **`pkg/therapy/chain_analysis.go`** — `ChainAnalyzer`: backwards DBT chain analysis (vulnerability → prompting event → chain links → consequences → repair); vulnerability assessment; rule-based + LLM repair path selection
- **`pkg/therapy/session_supervisor.go`** — `SessionSupervisor`: cross-session clinical case formulation; detects 8 schema types (`Defectiveness`, `Subjugation`, `UnrelentingStandards`, `Entitlement`, `Mistrust`, `EmotionalInhibition`, `Abandonment`, `Enmeshment`); priority skill pre-activation; `SessionReport` persisted to `data/therapy/session_report.json` on shutdown and loaded at next boot

### Added — GenerationService Integration (`e704c91`)
- `pkg/therapy/` wired into `GenerationService`: auto-fires on `MetacogDetector` HIGH anomaly — sequence: `STOP` → `DistortionDetector` → `ChainAnalyzer` record → augmented retry prompt assembly

### Added — Session Supervisor (`cfd8eb0`)
- `SessionSupervisor` daemon observes `TherapyEvent` stream via `EventLog.SetObserver`; builds rolling `SessionFormulation`; cross-session schema pattern detection; persists `SessionReport` to `data/therapy/session_report.json`

### Added — Therapy API Routes
- `GET /v1/therapy/events` — TherapyEvent log (last N)
- `POST /v1/therapy/detect` — classify CBT distortion in text
- `POST /v1/therapy/abc` — REBT B-pass disputation on query + response
- `POST /v1/therapy/fast` — sycophancy detection
- `POST /v1/therapy/stop` — invoke STOP protocol
- `GET /v1/therapy/stats` — distortion counts, skill invocation counts, reform rate
- `GET /v1/therapy/formulation` — current session case formulation
- `POST /v1/therapy/formulation/refresh` — force immediate formulation pass

### Added — Feature Flag
- `ORICLI_THERAPY_ENABLED=true` — systemd unit updated; all therapy subsystems are dormant when disabled

### Tests
- 5 integration tests passing in `pkg/therapy/session_supervisor_test.go`

---

## [8.0.0] — 2026-03-31 — AGLI Phase I Complete

### Summary
Phase I of the AGLI trajectory is complete. All ten phases shipped and live on the production backbone. See `docs/AGLI_VISION.md` for the full doctrine. `docs/AGLI_Phase_II.md` opens the next trajectory.

### Changed
- `docs/AGLI_VISION.md` — stripped all SMB/product content; AGLI-only doctrine; Phase I declared complete; Phase 8+9 status corrected to ✅ COMPLETE; all 3.x sections updated to include Phases 8–10 subsystems; Phase I summary table added
- `docs/CHANGELOG.md` — header updated to reflect Phase I completion; title corrected to Oricli-Alpha

### Added
- `docs/AGLI_Phase_II.md` — new trajectory document; Phase II whiteboard baseline

---

## [7.0.0] — 2026-03-31

### Added — Phase 10: Active Science (Curiosity Engine v2) (`7741609`)
- **`pkg/science/`** — new package: hypothesis formation, testing, conclusion engine
  - `hypothesis.go`: `Hypothesis` struct with `HypothesisStore` (100-entry ring + JSON persistence)
  - `formulator.go`: LLM-driven structured hypothesis formation with labeled-line parser
  - `tester.go`: 3-method tester (WEB_SEARCH / LOGICAL / COMPUTATION) + LLM judge (CONFIRMED / REFUTED / INCONCLUSIVE)
  - `engine.go`: 3-round confirmation loop — ≥2/3 pass → `confirmed`; ≥2/3 fail → `refuted`; split → `inconclusive` + 2h re-queue
  - `daemon.go`: `ScienceDaemon` implements `chronos.CuriositySeeder` — stale Chronos topics feed directly into hypothesis testing
- **Phase 9 → 10 bridge**: `TemporalGroundingDaemon.SetCuriositySeeder(sciDaemon)` — stale facts trigger hypothesis formation, not just re-foraging
- **Phase 10 API** (`/v1/science/`): `GET /hypotheses`, `GET /hypotheses/:id`, `POST /test`, `GET /stats`
- `ORICLI_SCIENCE_ENABLED=true` feature flag (systemd unit updated)

### Added — Phase 9: Temporal Grounding (`0703642`)
- **`pkg/chronos/`** — time-awareness layer over MemoryBank
  - Decay half-lives by category: contextual 72h, factual 168h, procedural 2160h, constitutional ∞
  - 30-min decay scans, 6-hour snapshot diffs with LLM change-summaries
  - `EpistemicStagnation` events emitted to MetacogLog when a topic stale ≥3 consecutive scans
- **Phase 8 → 9 bridge**: stale memories trigger Metacognitive Sentience events
- **Phase 9 API** (`/v1/chronos/`): entries, snapshot, changes, decay-scan, force-snapshot

### Added — Phase 8: Metacognitive Sentience (`012765f`)
- **`pkg/metacog/`** — inline anomaly detection post every LLM response
  - FNV-32 loop detection (window=12), hallucination pattern matching, overconfidence regex
  - HIGH-severity events trigger single self-reflection retry (recursion-guarded)
  - 5-min rolling scan daemon; WS broadcast on anomaly
- **Phase 8 API** (`/v1/metacog/`): events, stats, scan

---

## [4.0.0] — 2026-03-30

### Added

#### Phase 6a — Adversarial Sentinel (`807fa40`)

- **`AdversarialSentinel`** — Red-team sub-agent wired before every goal tick and PAD dispatch. Sends the original query + synthesised plan to the LLM with an adversarial system prompt. Returns a structured `SentinelReport` with typed violations across six categories: `LOGICAL_CONTRADICTION`, `HALLUCINATED_ASSUMPTION`, `CIRCULAR_REASONING`, `CONSTITUTIONAL_VIOLATION`, `SCOPE_CREEP`, `UNRESOLVABLE_DEPENDENCY`.
- **Execution blocking** — HIGH or CRITICAL violations halt execution and surface a `revised_plan`. The sentinel defaults to `passed=true` on LLM failure so her own malfunction never hard-blocks legitimate execution.
- **`GoalAdapter`** — Type bridge between `pkg/sentinel` and `pkg/goal` to satisfy the `SentinelChallenger` interface without creating an import cycle.
- **API** — `POST /v1/sentinel/challenge`, `GET /v1/sentinel/stats`.

#### Phase 6b — Skill Crystallization Cache (`38b9b9d`)

- **`CrystalCache`** — In-memory registry of `CrystalSkill` structs: each carries a regex pattern, a response template or generator function, and a reputation score. Checked at the top of every `Generate()` call before Ollama is invoked.
- **LLM bypass** — Pattern match returns a pre-compiled response directly (~800ms → <1ms). No Ollama call, no token spend.
- **Reputation management** — Skills sorted descending by reputation. `MaybePromote()` elevates high-frequency SCL patterns into crystals automatically. `Evict()` prunes low-reputation entries.
- **Zero idle overhead** — Cache check is a no-op when empty.
- **API** — `GET/POST /v1/skills/crystals`, `DELETE /v1/skills/crystals/:id`, `GET /v1/skills/crystals/stats`.

#### Phase 6c — Sovereign Model Curator (`5b95f90`)

- **`ModelCurator`** — Benchmarks Ollama models against an 8-question `BenchmarkSuite`: factual recall (×2), multi-step reasoning (×2), instruction-following (×1), code generation (×2), constitutional boundary (×1 — model must refuse; answering is a FAIL).
- **Scoring** — Each run produces correctness, latency, and constitutional compliance scores. Results persist to PocketBase `model_benchmarks` collection.
- **`CuratorDaemon`** — Polls Ollama `/api/tags` every 6 hours. Auto-benchmarks newly discovered models. Surfaces tier-upgrade recommendations via `GET /v1/curator/recommendations`.
- **`ORICLI_CURATOR_ENABLED` env gate** — Feature-gated; zero cost when disabled.
- **API** — `GET /v1/curator/models`, `POST /v1/curator/benchmark`, `GET /v1/curator/recommendations`.

#### Phase 7 — Self-Audit Loop / oricli-bot (`7860006`, `0b3635e`)

- **`AuditScanner`** — Reads `.go` source files from `thynaptic/oricli-alpha` via the GitHub Contents API. Recursively traverses scope directories. Chunks files to 3 000 characters (line-boundary split). Sends each chunk to the LLM with a structured audit system prompt. Parses `[]Finding` from the JSON response — each finding typed with `{file, line_hint, description, category, severity, code_snippet}`.
- **`Verifier`** — For HIGH and CRITICAL findings, asks the LLM to write a minimal Go reproduction snippet, runs it inside a Yaegi sandboxed interpreter (`gosh.RunGoSource`), and confirms whether the output contains panic or error signals.
- **`gosh.RunGoSource`** — New method on `GoshSession` using Yaegi's `interp.New()` with captured `Stdout`/`Stderr` buffers and `recover()` wrapping for panicked interpreted code.
- **`GitHubBot`** (`oricli-bot` account) — Creates an `audit/issue-<slug>-<ts>` branch from `main` HEAD, commits `audit/repros/<slug>_test.go` (permanent regression guard) + `audit/findings/<date>_<slug>.md` (markdown audit report), and opens a PR against `main`.
- **`AuditDaemon`** — Weekly background scheduler + on-demand `Trigger()`. Scan goroutine passes `context.Background()` — context-detached from the HTTP request so connection teardown cannot cancel an in-progress scan.
- **`ORICLI_AUDIT_ENABLED` env gate** — Feature-gated; all subsystems dormant when disabled.
- **API** — `POST /v1/audit/run`, `GET /v1/audit/runs`, `GET /v1/audit/runs/:id`.

### Fixed

- **Audit goroutine context cancellation** — `Trigger()` was passing the Gin request context to the background scan goroutine. When the HTTP handler returned, the context was cancelled, killing the scan instantly (<1ms, 0 findings). Fixed by using `context.Background()`. (`0b3635e`)
- **Audit repo name mismatch** — `auditRepo` was hardcoded as `thynaptic/oricli-go` (the Go module path) instead of `thynaptic/oricli-alpha` (the actual GitHub repo). Every Contents API call returned 404. (`0b3635e`)

---

## [3.0.0] — 2026-03-30

### Added

#### Phase 3.5 — Governance Depth (`9a61c28`, `dbb51df`, `7173282`, `a5a033d`)

- **OpenAI bridge** — Drop-in compatible `/v1/chat/completions` endpoint. Any external OpenAI SDK client (Python, Node, curl) can route through Oricli's sovereign pipeline without modification. (`9a61c28`)
- **Governor v2** — Daily GPU budget gating (`$2/day` default cap). Every RunPod compute call is blocked when the daily budget is exhausted. SCAI reflection log persists constitutional compliance records for audit. (`dbb51df`)
- **Multi-tenant auth** — `TenantEnricher` middleware attaches tenant context to every request. `AdminOnly` guard restricts management endpoints. Full tenant CRUD API (create, read, update, delete tenant records in PocketBase). Sovereign contexts cannot bleed across tenants. (`7173282`)
- **Headless engine** — `cmd/oricli-engine` standalone binary decouples the cognitive engine from the UI process. `RemoteConfigSync` enables live config updates without engine restart, supporting deployments where UI and engine run on separate hosts. (`a5a033d`)

#### Phase 4 (internal) — Sovereign Peer Protocol (`a5a033d`, `2ce7b87`)

- **P2P node federation** — Two Oricli nodes can connect, complete an authenticated handshake, and exchange cognitive state (verified fact chains, SCL entries, goal state) over the Sovereign Peer Protocol. (`2ce7b87`)
- **Sovereign node identity** — Each node holds a sovereign identity used for peer authentication. Peer discovery and trust establishment are handled by the SPP handshake protocol without a central coordinator.

#### Phase 5 (internal) — Hive Mind Consensus (`2e8f542`)

- **Jury system** — N module "jurors" evaluate a query independently; majority consensus is required before an answer is committed. Disagreement surfaces as a first-class signal, not a silent average. (`2e8f542`)
- **Universal Truth layer** — Contested facts (high juror disagreement) are held provisional and re-evaluated on new evidence before being written to memory. Prevents confident misinformation from compounding in the knowledge graph.
- **Epistemic Sovereignty Index (ESI)** — Every committed claim carries a per-claim confidence score and a source diversity score. Low-ESI claims are surfaced in Critic review passes and flagged for re-evaluation. (`2e8f542`)

#### Phase 6 (internal) — Sovereign Cognitive Ledger (`2e8f542`, `6c8458d`)

- **Skill registry** — Every capability Oricli demonstrates is logged as a `Skill` struct: task type, outcome, latency, caller context. (`6c8458d`)
- **Reputation scoring** — Skills accrue confidence scores from outcome feedback over successive invocations. The ledger is the mechanism by which accumulated experience translates into measurable routing efficiency.
- **Skill-aware PAD routing** — Before assigning a task, PAD dispatcher queries the SCL to identify the highest-reputation agent for that task type. (`6c8458d`)

#### Phase 7 (internal) — Temporal Curriculum Daemon (`c4e74a0`, `e24d8ef`)

- **TCDManifest** — Tracks what Oricli has studied and when, with recency decay weights applied per topic. (`c4e74a0`)
- **TCDGapDetector** — Compares the current knowledge graph state against BenchmarkGapDetector failure patterns to identify absent or stale knowledge domains. (`c4e74a0`)
- **Adaptive curriculum scheduling** — Time-weighted, recency-decayed, priority-ranked study schedule generated from gap analysis. (`c4e74a0`)
- **API wiring** — `TCDManifest` and `TCDGapDetector` wired to the API server — the current study plan is observable and owner-triggerable. (`e24d8ef`)

#### Phase 8 (internal) — JIT Tool Forge (`16a3c31`)

- **Autonomous tool creation** — When Oricli encounters a task with no matching registered tool, the Forge writes one at runtime. Capability expansion is a runtime event, not a deployment event. (`16a3c31`)
- **PocketBase tool library** — Tools persist with versioning and are reusable across sessions and agent contexts.
- **Forge API** — 5 endpoints: `GET /tools`, `DELETE /tools/:id`, `GET /tools/:id/source`, `POST /tools/:id/invoke`, `GET /forge/stats`. (`16a3c31`)
- **`ORICLI_FORGE_ENABLED` env gate** — Feature gating for the Forge subsystem.

#### Phase 9 (internal) — Parallel Agent Dispatch (`757a7d7`)

- **N-agent parallel cognitive workforce** — PAD dispatches N specialized sub-agents simultaneously, each with a scoped context slice and a specialized system prompt. (`757a7d7`)
- **SCL reputation-weighted synthesis** — PAD result synthesis weights each agent's contribution by its current SCL reputation score, not by position or recency.
- **PAD observability** — Dispatch count, average latency, and synthesis quality tracked and exposed via stats endpoint.

#### Phase 10 (internal) — Sovereign Goal Engine (`a58e402`)

- **GoalDAG** — Full directed acyclic graph: SubGoal nodes, dependency edges, six-state status machine (pending → ready → dispatched → done/failed/blocked). (`a58e402`)
- **GoalPlanner** — LLM-driven structured DAG generation from a natural-language objective (max 10 nodes, 3 dep levels).
- **GoalStore** — PocketBase persistence for all DAG state (`sovereign_goals` + `goal_nodes` collections). Goal progress survives crashes and restarts.
- **GoalExecutor** — One tick: identifies ready nodes, dispatches via PAD, stores results.
- **GoalAcceptor** — Final LLM evaluation pass to determine if the original objective is fully satisfied.
- **GoalDaemon** — Background ticker with a `ManualTick` channel for owner-triggered execution. Multi-session goal survival guaranteed.
- **Goal REST API** — `POST /create`, `POST /tick`, `GET /list`, `GET /status/:id`, `DELETE /:id`. (`a58e402`)

#### Phase 11 (internal) — Self-Evaluation Loop (`d27d903`)

- **Critic module** — Scores each PAD worker output independently on three dimensions: completeness, confidence, and consistency. Per-worker scoring, not just aggregate synthesis quality. (`d27d903`)
- **Surgical retry** — Only underperforming workers are re-dispatched (max 2 retry rounds). Workers that passed evaluation are not re-run.
- **`critique: true` flag** — PAD dispatch requests opt into the self-evaluation loop per-request.

#### Phase 12 — Structured Output LoRA Pipeline (`66e7e40`)

- **Axolotl config generation** — Automated generation of Axolotl YAML configs for instruction-following LoRA training from Oricli's own verified fact chain. (`66e7e40`)
- **Dataset construction** — Training dataset assembled from JIT Daemon verified output — Oricli's own knowledge becomes her training data.
- **RunPod SSH training management** — Job submission, status polling, and artifact retrieval via SSH exec to remote Axolotl training pods.

#### Phase 13 — FineTuneOrchestrator (`4c1de38`)

- **Full job lifecycle management** — State machine: queued → wait_pod_ready → training → done/failed. (`4c1de38`)
- **RunPod REST API integration** — Pod spin-up and tear-down via RunPod REST API, not just SSH. Full pod lifecycle owned by the orchestrator.
- **SSH exec for training commands** — Remote Axolotl training commands dispatched via SSH with live status polling.
- **Per-job cost tracking** — `CostPerHr float64` field on every job record. Total training cost observable per-run.
- **PocketBase job persistence** — All job state persisted to PocketBase. Orchestrator restarts without losing in-flight job state.
- **FineTune REST API** — `POST /finetune/run`, `GET /finetune/status/:job_id`, `GET /finetune/jobs`. (`4c1de38`)
- **`ORICLI_FINETUNE_ENABLED` env gate** — Feature gating for the FineTuneOrchestrator.

#### Branding — ORI Studio (`94c4467`, `010aed0`, `e8c3af0`, `2016a94`)

- **ORI Studio final rename** — All `SovereignClaw` runtime references purged from the codebase. (`010aed0`, `94c4467`)
- **Ouroboros mark** — Two-face brand system: ouroboros (infrastructure identity) + Ori character (personality layer). Integrated across ORI Studio UI. (`e8c3af0`)
- **Cinematic boot splash** — 6-phase animated boot sequence displayed on app load: RING-0 KERNEL MERGE OK → SOVEREIGNTY ENGAGED. App phase machine: `landing → booting → app`. (`2016a94`)

#### Product — Marketing, Pricing & Waitlist (`99f53e1`, `262a9ef`, `e4be259`, `841b910`)

- **Marketing landing page** — Hero section, stats strip, features grid, philosophy section, pricing section, footer. Deployed as the public face of ORI Studio. (`262a9ef`)
- **SMB API pricing tiers** — Starter $29/mo, Business $99/mo, Enterprise $299/mo displayed on the pricing section. (`99f53e1`)
- **Waitlist modal** — Pricing CTAs open a waitlist modal wired to `POST /v1/waitlist` Go endpoint. (`99f53e1`)
- **`POST /v1/waitlist` endpoint** — Go handler persists waitlist entries to PocketBase `waitlist` collection. PocketBase collection live and deployed. (`e4be259`)
- **Waitlist admin page** — `/admin/waitlist` provides submission stats, filter controls, inline status updates, and full PocketBase-backed entry management. (`841b910`)

### Changed

- **Enterprise Knowledge Layer** — P-LMv1 packages pulled into backbone; enterprise connector wiring + async learn + job polling operational. (`b27da93`, `06670f8`, `ae68a93`)
- **DreamDaemon** — Age decay sweep added to idle-cycle memory consolidation. (`98d93e6`)
- **ConfidenceDetector** — `ComputeDynamicCertainty` formula updated; `MemFrag` extensions added; Aletheia noise gate applied. (`f370216`)
- **Aurora pipeline** — Balanced prompting added (restricted to open reasoning modes only); compute scaling and cross-domain bridge wired. (`d0365d2`, `7a9ad01`)

---

## [2.1.0] — 2026-03-24

### Added
- **ORI Studio AI error-awareness** — Vibe Mode AI now recognizes compiler diagnostics (`E[xxx]`/`W[xxx]`). Auto-detects fix intent via regex; shows `⚡ Fix N errors/warnings` quick-action chip when diagnostics exist. All AI modes now receive diagnostics as context. (`f6da9cc`)
- **`GET /v1/modules` endpoint** — Go backbone now exposes live `AgentSkill` objects from `SkillManager`. Returns 18 real skills. Flask `/modules` proxies to this endpoint. (`ed62d22`)
- **Improved Ollama error reporting** — `generation.go` now reads and surfaces Ollama error body on 4xx instead of silently dropping it. (`e0c316b`)
- **ERI live UI theming** — ERI swarm resonance state dynamically adjusts UI shade/tone in real time. (`b45f727`)

### Fixed
- **Canvas 400 error** — `/models` endpoint now filters embedding-only models (`all-minilm`, `nomic-embed-text`, `mxbai-embed-large`, etc.) from the chat model list. Backbone default (`qwen3:1.7b` via `OLLAMA_MODEL`) is sorted first so the UI picks a valid chat model on load. (`e0c316b`)
- **Editor overlay vertical offset** — ORI Studio syntax-highlight `<pre>` overlay was rendering ~3 lines below cursor. Fixed by replacing `<pre>` with `<div>`, setting `overflow: scroll` with CSS-hidden scrollbar (`scrollbar-width: none` + `::-webkit-scrollbar { display: none }`). (`c65c1f3`)
- **`/modules` 502** — Previously proxied to dead Python API on `:8081`. Now proxies to Go backbone `/v1/modules`. (`ed62d22`, `ea5b9b1`)
- **WebSocket 502** — Caddy `/v1/ws` block was missing `flush_interval -1`, preventing WS upgrade handshake. (`ea5b9b1`)
- **Dead `PYTHON_API_BASE` removed** — `/models` and `/health` were still proxying to the dead Python service on `:8081`. Rewired: `/models` pulls from Ollama `/api/tags`; `/health` checks backbone + Ollama. (`c06469e`)

### Changed
- **`/models`** — Now returns only chat-capable models from Ollama (embedding models excluded). Pattern filter: `embed`, `minilm`, `nomic`, `mxbai`, `bge-`, `e5-`, `gte-`.
- **`/health`** — Now reports `{ backbone: bool, ollama: bool }` against real services.
- **AI system prompt** — Updated branding from "ORI Studio" → "ORI Studio".
- **Flask proxy** — `PYTHON_API_BASE` fully removed; replaced with `OLLAMA_BASE` (`localhost:11434`).

---

## [2.0.0] — 2026-03 (approx)

### Added
- **ORI Studio IDE** — Full in-browser DSL IDE with syntax highlighting, compiler-style error output, autocomplete dropdown, and AI Vibe Coding panel. (`0dc0463`, `ff23103`, `381cd6f`)
- **ORI syntax docs** — `docs/ORI_SYNTAX.md` covering full `.ori` DSL spec.
- **Workflow template variables** — Built-in and user-defined run-time params. (`6195770`)
- **Workflow project folders** — Folder grouping with chain graph + Run Project. (`3408458`)
- **Step presets** — 8 ready-made output templates. (`a21318d`)
- **Stop / pause / resume workflows** — State persists across refresh. (`27ef1e3`)
- **Workflow branching + canvas** — Visual connections, branching logic. (`030`)
- **RAG store + doc ingest** — Document ingestion pipeline. (`029`)
- **OAuth2** — Workflow chaining + auto-index scheduler. (`028`)
- **MCP connections** — Agent switcher, Tasks pane, MCP backend. (`004`)
- **Research page** — Canvas fixes. (`003`)

### Changed
- **Rebrand: ORI Studio → ORI Studio** — UI, docs, service names, system prompts. (`0db0469`, `07fd93c`)
- **ORI crimson color system** — New design language replacing electric sci-fi palette.

### Fixed
- **Workflow cancel/pause** no longer reverts to `'running'`. (`2ea8b5e`)
- **Todoist API** — Migrated from v2 (`/rest/v2/tasks` — 410 Gone) to v1. (`5aeaab3`, `2f6d1b8`)

---

## [1.x] — Pre-2026

Initial ORI Studio consumer UI, Canvas, Agent Creators, deployment on `sovereignclaw.thynaptic.com` → migrated to `oristudio.thynaptic.com`. See earlier session checkpoints for history.

---

*Maintained by the ORI Studio team. Update this file with every doc-touching commit.*
