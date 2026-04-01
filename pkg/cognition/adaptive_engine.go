package cognition

// Adaptive Reasoning Engine (ARE) — dual-track architecture.
//
// The ARE is the second track of ORI's reasoning system. It fires when a query
// is high-complexity but has no strong keyword signal for a specific fast-path
// mode (PAL, ReAct, LogicEval, etc.). Instead of committing to a single mode
// upfront, the ARE runs a multi-step loop that evaluates answer quality after
// each step and escalates to a different cognitive tool only if needed.
//
// Loop (max 3 steps):
//   Step 1: ModeConsistency — 3 independent samples + plurality vote (best standalone)
//   Step 2: ModeDebate      — adversarial synthesis → finalized via single LLM call
//   Step 3: ModeDiscover    — structured plan → finalized via single LLM call
//
// The ARE exits as soon as the Value function scores an answer ≥ 0.75, or when
// the budget is exhausted — always returning the best answer seen, never empty.
//
// Context design: the ARE uses context.WithoutCancel so that HTTP client
// disconnection doesn't kill reasoning mid-step. Each step gets its own
// timeout so the total ARE budget is bounded.
//
// References:
//   pkg/cognition/sovereign.go  — dispatch point (replaces ModeDiscover case)
//   pkg/cognition/self_discover.go, reasoning_engines.go — tool implementations

import (
	"context"
	"log"
	"math"
	"strings"
	"time"
)

// areStepTimeout is the per-step budget. Three steps × 90s = 4.5 min max.
const areStepTimeout = 90 * time.Second

// confidenceThreshold is the minimum Value score to accept an answer and stop.
const confidenceThreshold = 0.75

// areMaxSteps is the hard cap on reasoning iterations — prevents latency runaway.
const areMaxSteps = 3

// ReasoningStep records one iteration of the ARE loop.
type ReasoningStep struct {
	Mode      ReasoningMode
	Output    string
	Score     float64
	Elapsed   time.Duration
}

// ReasoningState tracks the full mutable context of an ARE run.
type ReasoningState struct {
	Stimulus   string
	Steps      []ReasoningStep
	Confidence float64
	BestAnswer string
	Budget     int
	triedModes map[ReasoningMode]bool
}

func newReasoningState(stimulus string) *ReasoningState {
	return &ReasoningState{
		Stimulus:   stimulus,
		Budget:     areMaxSteps,
		triedModes: make(map[ReasoningMode]bool),
	}
}

func (s *ReasoningState) tried(mode ReasoningMode) bool {
	return s.triedModes[mode]
}

func (s *ReasoningState) record(step ReasoningStep) {
	s.triedModes[step.Mode] = true
	s.Steps = append(s.Steps, step)
	if step.Score > s.Confidence {
		s.Confidence = step.Score
		s.BestAnswer = step.Output
	}
	s.Budget--
}

// ─── Adaptive Reasoning Engine ───────────────────────────────────────────────

// runAdaptive is the ARE entry point. It is called from sovereign.go in place
// of the old ModeDiscover dispatch for high-complexity / ambiguous queries.
func (e *SovereignEngine) runAdaptive(ctx context.Context, stimulus, composite string) (string, error) {
	state := newReasoningState(stimulus)
	log.Printf("[ARE] start — stimulus len=%d budget=%d", len(stimulus), areMaxSteps)

	// Detach from the HTTP request context so client disconnects don't kill
	// mid-step reasoning. Each step gets its own areStepTimeout.
	areBase := context.WithoutCancel(ctx)

	for state.Budget > 0 {
		// Check if the original request context is still live before starting a new step.
		// No point burning compute if the caller has already moved on.
		if ctx.Err() != nil && state.BestAnswer != "" {
			log.Printf("[ARE] parent ctx cancelled — returning best answer so far (%.2f)", state.Confidence)
			break
		}

		mode := arePolicy(state)
		if mode == ModeStandard {
			break
		}

		stepCtx, stepCancel := context.WithTimeout(areBase, areStepTimeout)
		start := time.Now()
		output, err := e.areExecute(stepCtx, mode, stimulus, composite)
		elapsed := time.Since(start)
		stepCancel()

		if err != nil {
			log.Printf("[ARE] step mode=%s err=%v elapsed=%s — skipping", mode, err, elapsed.Round(time.Millisecond))
			state.record(ReasoningStep{Mode: mode, Output: "", Score: 0, Elapsed: elapsed})
			continue
		}

		if strings.TrimSpace(output) == "" {
			log.Printf("[ARE] step mode=%s — empty output elapsed=%s — skipping", mode, elapsed.Round(time.Millisecond))
			state.record(ReasoningStep{Mode: mode, Output: "", Score: 0, Elapsed: elapsed})
			continue
		}

		score := areValue(output, stimulus)
		log.Printf("[ARE] step mode=%s score=%.2f elapsed=%s chars=%d",
			mode, score, elapsed.Round(time.Millisecond), len(output))

		state.record(ReasoningStep{Mode: mode, Output: output, Score: score, Elapsed: elapsed})

		if state.Confidence >= confidenceThreshold {
			log.Printf("[ARE] confidence threshold met (%.2f) after %d step(s)", state.Confidence, len(state.Steps))
			break
		}
	}

	if state.BestAnswer == "" {
		log.Printf("[ARE] all steps produced empty output — falling back to standard")
		return e.runStandard(ctx, stimulus, composite)
	}

	log.Printf("[ARE] done — steps=%d final_confidence=%.2f", len(state.Steps), state.Confidence)
	return state.BestAnswer, nil
}

// areExecute dispatches to the appropriate engine runner for the given mode.
// Runners that return composite enrichments (Discover, Debate) are finalized
// with a single direct LLM call so the ARE receives an actual answer to score.
// Runners that already produce final answers (Consistency) are used directly.
func (e *SovereignEngine) areExecute(ctx context.Context, mode ReasoningMode, stimulus, composite string) (string, error) {
	switch mode {
	case ModeConsistency:
		// Returns a final answer directly — no further LLM call needed.
		return e.runConsistency(ctx, stimulus, composite)

	case ModeDebate:
		// Returns a composite enrichment — finalize with one LLM call.
		enriched, err := e.runDebate(ctx, stimulus, composite)
		if err != nil || strings.TrimSpace(enriched) == "" || enriched == composite {
			return "", err
		}
		return e.areFinalizeWithLLM(ctx, stimulus, enriched)

	case ModeDiscover:
		// Returns a structured plan composite — finalize with one LLM call.
		enriched, err := e.runSelfDiscover(ctx, stimulus, composite)
		if err != nil || strings.TrimSpace(enriched) == "" || enriched == composite {
			return "", err
		}
		return e.areFinalizeWithLLM(ctx, stimulus, enriched)

	default:
		return "", nil
	}
}

// areFinalizeWithLLM calls the LLM once with an enriched composite as the
// system prompt to produce a final user-facing answer. Used by enrichment-style
// runners (Debate, Discover) so the ARE can score actual answer quality.
func (e *SovereignEngine) areFinalizeWithLLM(ctx context.Context, stimulus, enrichedComposite string) (string, error) {
	if e.GenService == nil {
		return "", nil
	}
	res, err := e.GenService.Generate(stimulus, map[string]interface{}{
		"num_ctx":     4096,
		"num_predict": 512,
		"temperature": 0.5,
		"system":      enrichedComposite,
	})
	if err != nil {
		return "", err
	}
	text, _ := res["response"].(string)
	return strings.TrimSpace(text), nil
}

// ─── Policy ───────────────────────────────────────────────────────────────────
//
// arePolicy selects the next cognitive tool based on the current ReasoningState.
// Rules are applied in order; first match wins. Returns ModeStandard to signal
// that no further escalation is useful (budget should be treated as exhausted).
//
// v1 policy (heuristic):
//   Step 1: Consistency — 3 independent votes, fastest standalone answer producer.
//   Step 2: Debate     — adversarial advocate/skeptic synthesis, then finalized.
//   Step 3: Discover   — structured plan, then finalized. Last resort (slowest).
func arePolicy(state *ReasoningState) ReasoningMode {
	// Step 1 — always start with Consistency (best standalone, returns final answer).
	if !state.tried(ModeConsistency) {
		return ModeConsistency
	}

	// Step 2 — if Consistency was low-confidence, try Debate.
	if state.Confidence < 0.60 && !state.tried(ModeDebate) {
		return ModeDebate
	}

	// Step 3 — if still uncertain, structured plan (Discover) as last resort.
	if state.Confidence < 0.60 && !state.tried(ModeDiscover) {
		return ModeDiscover
	}

	// Policy exhausted or confidence is acceptable — stop.
	return ModeStandard
}

// ─── Value Function ───────────────────────────────────────────────────────────
//
// areValue scores answer quality on [0.0, 1.0] using fast heuristics.
// No LLM call — must be < 1ms. Designed to distinguish empty/hedging/short
// answers (which warrant another step) from substantive ones (stop early).
func areValue(answer, _ string) float64 {
	if strings.TrimSpace(answer) == "" {
		return 0.0
	}

	score := 0.50 // non-empty baseline

	n := len(answer)
	switch {
	case n < 50:
		score = 0.20
	case n < 200:
		score = 0.50
	case n < 500:
		score = 0.62
	default:
		score = 0.70
	}

	lower := strings.ToLower(strings.TrimSpace(answer))

	// Penalise hedging openers — these usually precede an unhelpful response.
	hedges := []string{
		"i don't know", "i do not know", "i cannot", "i can't",
		"i'm not sure", "i am not sure", "i'm unable", "i am unable",
		"as an ai", "as a language model",
	}
	for _, h := range hedges {
		if strings.HasPrefix(lower, h) {
			score -= 0.30
			break
		}
	}

	// Reward structured output — lists, code blocks, headings signal substantive reasoning.
	if strings.Contains(answer, "\n- ") || strings.Contains(answer, "\n* ") ||
		strings.Contains(answer, "\n1.") || strings.Contains(answer, "```") ||
		strings.Contains(answer, "\n## ") || strings.Contains(answer, "\n**") {
		score += 0.08
	}

	// Reward answers that include explicit reasoning markers.
	reasoningMarkers := []string{"therefore", "because", "since", "thus", "this means", "as a result"}
	for _, m := range reasoningMarkers {
		if strings.Contains(lower, m) {
			score += 0.04
			break
		}
	}

	return math.Min(math.Max(score, 0.0), 1.0)
}
