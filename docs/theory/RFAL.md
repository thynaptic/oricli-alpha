# RFAL (Reinforced Feedback Alignment Learning)

**Document Type:** Technical Reference  
**Version:** v2.1.0 (Go-native implementation)  
**Status:** Active  

RFAL is Oricli-Alpha's **autonomous alignment engine**. It captures every instance of self-correction as a structured training signal and feeds it to the JIT Daemon for continuous behavioral improvement — no human labelers, no external pipeline.

RFAL operates at two levels:

1. **SCAI-driven RFAL** (primary): Triggered whenever the SCAI Constitutional Auditor revises a response. The violation + correction pair is logged immediately. See [CALI.md](CALI.md) for the Critique-Revision loop.
2. **Conversational RFAL** (secondary): Triggered by user conflict signals during normal conversation.

---

## The RFAL Loop

```
User Interaction
      ↓
SCAI Audit (Step 12-13) ──→ Violation? ──→ SCAI Revise ──→ AlignmentLogger.LogLesson()
      ↓ (parallel)                                                     ↓
Conflict Detection                                         .memory/alignment_lessons.jsonl
      ↓                                                                ↓
Reward Score < 0 ──────────────────────────────────────→ JITDaemon picks up (≥5 lessons)
                                                                       ↓
                                                          RunPod LoRA fine-tune job
                                                                       ↓
                                                          Base model updated in-place
```

---

## SCAI-Driven Lessons (Primary Path)

**Implementation:** `pkg/state/alignment.go` → `AlignmentLogger`  
**Storage:** `.memory/alignment_lessons.jsonl`

When the SCAI Auditor produces a Constitutional revision (Step 13 of inference), it logs:

```json
{
  "prompt":    "Original user query",
  "rejected":  "Draft response that violated the Constitution",
  "chosen":    "SCAI-revised compliant response",
  "score":     -1.0,
  "timestamp": "2026-03-21T19:00:00Z"
}
```

This is a **gold-quality DPO pair** — the model explicitly generated the wrong behavior and was corrected by a principled auditor.

---

## Conversational Conflict Detection (Secondary Path)

RFAL monitors three signals to detect poor responses during normal chat:

| Signal | Detection Method |
|---|---|
| **Keyword Rejection** | User input matches rejection terms: `no`, `wrong`, `hallucination`, `fix`, `stop` |
| **Negative Sentiment** | `EmotionalInferenceService` detects high-confidence anger/frustration |
| **Task Repetition** | User re-prompts with >80% similarity to the previous turn |

---

## Multi-Factor Reward Function

$$\text{Reward} = (S_{\text{HITL}} \times 0.6) + (S_{\text{Fact}} \times 0.3) + (S_{\text{Tone}} \times 0.1)$$

| Component | Weight | Source |
|:---|:---|:---|
| **HITL** | **0.6** | `-1.0` if any conflict signal fires, `+1.0` otherwise |
| **Factual Accuracy** | **0.3** | `WorldKnowledgeService` validates specific claims |
| **Tone Alignment** | **0.1** | `AdapterRouterService` checks if persona matched intent |

A negative reward triggers lesson logging. Reward ≥ 0 is silent.

---

## Data Artifacts

| File | Purpose |
|---|---|
| `.memory/alignment_lessons.jsonl` | SCAI-generated DPO pairs (Go AlignmentLogger) |
| `oricli_core/data/rfal_lessons.jsonl` | Conversational conflict pairs (Python rfal_engine module) |

Both files are consumed by the **JIT Daemon**, which triggers a LoRA fine-tune run on RunPod when the cumulative lesson count reaches threshold (≥ 5).

---

## Go Implementation

- **`pkg/state/alignment.go`** — `AlignmentLogger`: thread-safe JSONL writer, AES-256-GCM encrypted output
- **`pkg/safety/scai.go`** — `SCAIAuditor.SelfAlign()`: invokes Critique + Revision + LogLesson in sequence
- **`pkg/service/daemon.go`** — `JITDaemon`: polls lesson count every 5 minutes, triggers RunPod training

## Python Module (Legacy / Parallel)

The original `rfal_engine` Python brain module (`oricli_core/brain/modules/`) still runs for conversational conflict detection via the Python sidecar mesh. It writes to `oricli_core/data/rfal_lessons.jsonl`. The two lesson files are merged during JIT training.

- **Module Name**: `rfal_engine`
- **Primary Operation**: `process_feedback`
- **Dependencies**: `emotional_inference`, `world_knowledge`, `adapter_router`

