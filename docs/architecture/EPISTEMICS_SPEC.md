# Epistemics Engine — Spec

## What this is

A conjecture-criticism-synthesis loop that generates **explanations**, not predictions. Architecturally closes Deutsch's gap between LLM mimicry and genuine knowledge creation. ORI runs a dialectical 3-pass cycle per query: conjecture why → attack that explanation → refine what survived.

This is not a reasoning style tweak. It's a structural commitment to explanation-first inference.

---

## Package

```
pkg/epistemics/
  engine.go      — ConjectionEngine, main Run() loop, escalation logic
  conjecture.go  — pass 1: explanation generation (Haiku)
  criticism.go   — pass 2: adversarial attack (Haiku)
  synthesis.go   — pass 3: error-corrected output (Haiku or Sonnet)
  types.go       — ConjectionCycle, ExplanatoryResult, CriticismReport
  config.go      — env-based knobs
```

---

## The Loop

```
Input
  └─ Pass 1: Conjecture (Haiku)
       "What explains this? Not what predicts it — what CAUSES it."
       → candidate explanation
  └─ Pass 2: Criticism (Haiku, adversarial)
       "What is wrong with this explanation? Find contradictions,
        gaps, untestable claims, stronger alternatives."
       → CriticismReport { issues []string, severity float64 }
  └─ Pass 3: Synthesis
       severity < threshold → Haiku  (cheap, criticism was weak)
       severity ≥ threshold → Sonnet (criticism landed, need depth)
       "Produce an explanation that survives the valid criticisms.
        Preserve what held. Correct what didn't."
       → final explanation + trace
  └─ Optional iteration (max 2)
       If synthesis contradicts conjecture significantly → loop again
       Otherwise → return
```

Early-exit: if 2nd iteration produces semantically equivalent output, terminate.

---

## Types

```go
type ConjectionCycle struct {
    Query      string
    Context    []oracle.Message
    MaxIter    int     // default 2
    Threshold  float64 // criticism severity to escalate, default 0.65
}

type CriticismReport struct {
    Issues   []string
    Severity float64 // 0.0–1.0
}

type ExplanatoryResult struct {
    Explanation string
    Trace       ConjectionTrace
    TokensUsed  TokenUsage
}

type ConjectionTrace struct {
    Initial     string
    Criticisms  []string
    Refined     string
    Iterations  int
    Survived    bool // did conjecture survive with only minor corrections?
    Escalated   bool // did we use Sonnet for synthesis?
}
```

---

## Agent Personas

Two dedicated `.agent.md` files — these are injected as system prompts per pass, not reused from existing agents.

**`.github/agents/ori-conjecturer.agent.md`**
- Bold, generative, explanation-first
- Explicitly forbidden from hedging or predicting
- Must answer "what causes / why / how does this work" not "what comes next"

**`.github/agents/ori-critic.agent.md`**
- Adversarial. Job is to break the conjecture.
- Scores its own criticism by severity
- Looking for: internal contradictions, unfalsifiability, better competing explanations, scope errors

Synthesizer uses `ori-reasoner` (existing heavy agent) for Sonnet escalations, `ori-chat-fast` for Haiku synthesis pass.

---

## Env Config

| Var | Default | Notes |
|---|---|---|
| `ORI_EPISTEMICS_ENABLED` | `true` | kill switch |
| `ORI_EPISTEMICS_MAX_ITER` | `2` | max conjecture loops |
| `ORI_EPISTEMICS_ESCALATE_THRESHOLD` | `0.65` | criticism severity → Sonnet |
| `ORI_EPISTEMICS_TRACE` | `false` | include trace in API response |

---

## Integration Points

### 1. Oracle heavy route (primary)
`oracle/router.go` — `RouteHeavyReasoning` optionally pre-pipes through epistemics before returning.  
Trigger: query classified as explanatory (`why`, `how does`, `what causes`, `explain`).  
Oracle detects this in `Decide()`, sets `ExplanatoryMode: true` → epistemics runs first, result handed to final synthesis.

### 2. Swarm node (on-demand)
Swarm can spawn an epistemics cycle as a named contractor via Contract Net.  
Node name: `"epistemics"`. Any swarm node can request an epistemics pass on a subproblem result.

### 3. CuriosityDaemon (background)
Daemon accumulates observations → fires an epistemics cycle overnight on high-salience ones.  
Produces new `MemorySegment` tagged `source: epistemics` — feeds back into memory graph.

### 4. Direct API (optional, later)
`POST /v1/epistemics/run` — explicit caller access. Not priority for v1.

---

## Token Cost Per Cycle

| Pass | Model | In | Out | Cost |
|---|---|---|---|---|
| Conjecture | Haiku | ~1.5K | ~600 | ~$0.0036 |
| Criticism | Haiku | ~2.2K | ~600 | ~$0.0042 |
| Synthesis (weak crit) | Haiku | ~3.5K | ~1K | ~$0.0068 |
| Synthesis (strong crit) | Sonnet | ~3.5K | ~1K | ~$0.026 |
| **Total (Haiku path)** | | | | **~$0.014** |
| **Total (escalated)** | | | | **~$0.034** |

With cached system prompts (~10x cheaper on cached in-tokens): real cost is closer to **$0.010 / $0.028**.

| Load | $/month (Haiku) | $/month (escalated) |
|---|---|---|
| Daemon idle (20/day) | ~$6 | ~$17 |
| On-demand moderate (100/day) | ~$30 | ~$84 |
| Heavy session-bound (300/day) | ~$90 | ~$252 |

---

## What This Closes (Deutsch Scorecard)

| Gap | Before | After |
|---|---|---|
| Mimicry vs Creativity | LLM completes patterns | Conjecture pass generates novel explanation, not completion |
| Prediction vs Explanation | Token prediction | Loop is structurally explanation-oriented; criticism enforces it |
| Philosophical Bottleneck | No epistemological framework | Conjecture-criticism-error-correction IS the framework, baked in |
| AGI as Person | Already partial (sovereign, daemons) | Unchanged — not the target here |
| Doom Rejection | Already aligned | Unchanged |

---

## Build Order

1. `pkg/epistemics/types.go` — structs
2. `pkg/epistemics/config.go` — env knobs
3. `pkg/epistemics/conjecture.go` — pass 1 via `llm.Chat()`
4. `pkg/epistemics/criticism.go` — pass 2 via `llm.Chat()`
5. `pkg/epistemics/synthesis.go` — pass 3, escalation logic
6. `pkg/epistemics/engine.go` — `Run()`, loop, early-exit
7. Agent personas (2 files)
8. Oracle router hook (`ExplanatoryMode` flag in `Decide()`)
9. CuriosityDaemon integration
