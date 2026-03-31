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

### Phase 11 — _(TBD)_

> **Whiteboard:** _[pending]_

---

### Phase 12 — _(TBD)_

> **Whiteboard:** _[pending]_

---

### Phase 13 — _(TBD)_

> **Whiteboard:** _[pending]_

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
| 11 | TBD | 🔲 Whiteboard |
| 12 | TBD | 🔲 Whiteboard |
| 13 | TBD | 🔲 Whiteboard |

_This document will be updated as the whiteboard session concludes._
