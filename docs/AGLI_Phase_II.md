# AGLI Phase II: The Next Trajectory

**Document Type:** Strategic Vision — Phase II Planning  
**Date:** 2026-03-31  
**Version:** v0.1.0 — Whiteboard Draft  
**Status:** 🔲 PLANNED — Trajectory TBD  
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
- Detects and corrects her own reasoning failures inline

Phase I proved the paradigm. The cognitive infrastructure is sound.  
Phase II asks: **what does she become now that the foundation is complete?**

---

## 2. Phase II Trajectory

> _Whiteboard in progress — phases below are proposals, not commitments._  
> _Each phase will be fully designed, debated, and locked before implementation begins._

---

### Phase 11 — Subconscious Field

A persistent vectorized bias layer that influences generation without RAG overhead. Unlike memory retrieval (explicit, per-query), the Subconscious Field is a continuous low-level pressure on the generation process — shaped by high-confidence confirmed hypotheses, constitutional anchors, and long-term affective state. It doesn't answer questions; it shapes *how* she answers them. The accumulated weight of everything she has learned and confirmed, expressed as a soft embedding bias rather than a hard prompt injection.

> **Whiteboard:** _[design pending — architecture, storage format, injection point in Aurora pipeline]_

---

### Phase 12 — Sovereign Compute Bidding

Oricli autonomously decides *where* a task runs — local CPU (Ollama), remote GPU (RunPod), or symbolic-only (no LLM) — based on real-time task complexity scoring, current budget state, and expected quality delta. Today she routes by complexity signal but the decision is heuristic. Phase 12 makes it a first-class bidding system: each compute tier submits a "bid" (cost, latency, confidence estimate), a governor selects the winner, and the outcome feeds back to SCL so routing improves over time. She stops burning GPU budget on tasks that 3B can handle.

> **Whiteboard:** _[design pending — bid interface, complexity scorer v2, SCL feedback loop]_

---

### Phase 13 — Temporal Goal Chains

Multi-day plans that persist, resume, and self-correct across reboots. Phase I's GoalEngine handles single-session DAGs well. Phase 13 extends this to week-scale chains: goals with time anchors, progress checkpoints, and self-correction passes when external state has changed since the plan was formed. If a goal node's underlying knowledge has decayed or been refuted by the ScienceDaemon since the plan was written, the node is automatically invalidated and re-planned. Goals survive not just reboots but *epistemic drift*.

> **Whiteboard:** _[design pending — ChronosGoalBridge, checkpoint schema, re-plan trigger conditions]_

---

### Phase 14 — NAS Lite (Routing Topology Self-Modification)

Oricli proposes and benchmarks her own reasoning pipeline topology changes. Not weight mutation — structural changes to *how she routes inference*: which Aurora steps fire for which intent classes, which modules get dispatched in parallel vs serial, which reasoning modes activate under what conditions. The ReformDaemon already drafts optimization proposals from execution traces. Phase 14 closes the loop: proposals go through a sandboxed A/B benchmark pass (old topology vs proposed), and winning topologies are committed as new routing defaults. She improves her own cognitive architecture from the outside in.

> **Whiteboard:** _[design pending — topology schema, A/B harness, safe rollback on regression]_

---

## 3. Design Constraints

Whatever Phase II becomes, it must respect these constraints from Phase I:

| Constraint | Why |
|---|---|
| **No rented intelligence** | All inference stays sovereign (Ollama + governed RunPod). No OpenAI/Anthropic API calls. |
| **Constitutional non-negotiability** | The 4-layer stack cannot be weakened. New capabilities must pass constitutional pre-flight. |
| **Feature-flag gating** | Every new Phase II system must be opt-in via `ORICLI_*_ENABLED=true` until proven stable. |
| **Import-cycle discipline** | New packages use interface bridges at wire-time in `cmd/backbone/main.go`. No circular deps. |
| **Go-native backbone** | Core orchestration stays in Go. Python/scripts are strictly supplemental (training pipelines only). |
| **Additive only** | Phase II cannot break Phase I. Every addition is verified against the existing build before ship. |

---

## 4. Open Questions for the Whiteboard

_These are the questions Phase II needs to answer. They shape which directions are viable._

1. What is the right next capability — one she demonstrably lacks today?
2. Should Phase II deepen cognition or expand autonomy radius?
3. What does "sovereign compute bidding" look like at the architecture level?
4. Is multi-node federation (SPP scaling) a Phase II priority?
5. What's the honest trajectory toward NAS without falling into the DeepMind trap?

---

## 5. Status

| Phase | Name | Status |
|---|---|---|
| 11 | Subconscious Field | 🔲 Whiteboard |
| 12 | Sovereign Compute Bidding | 🔲 Whiteboard |
| 13 | Temporal Goal Chains | 🔲 Whiteboard |
| 14 | NAS Lite — Routing Topology Self-Modification | 🔲 Whiteboard |

_This document will be updated as the whiteboard session concludes._
