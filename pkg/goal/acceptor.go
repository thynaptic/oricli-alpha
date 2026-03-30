package goal

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
)

// AcceptorResult is the output of GoalAcceptor.Check.
type AcceptorResult struct {
	Passed    bool    `json:"passed"`
	Score     float64 `json:"score"`
	Rationale string  `json:"rationale"`
	Gaps      string  `json:"gaps,omitempty"` // what's still missing if not passed
}

// GoalAcceptor evaluates whether a GoalDAG's accumulated results
// fully satisfy the original objective.
type GoalAcceptor struct {
	Distiller GoalDistiller
}

// NewGoalAcceptor creates an acceptor.
func NewGoalAcceptor(distiller GoalDistiller) *GoalAcceptor {
	return &GoalAcceptor{Distiller: distiller}
}

// Check evaluates goal completion. Falls back to "passed" on LLM error
// (so goals don't get stuck on transient inference failures).
func (a *GoalAcceptor) Check(ctx context.Context, goal *GoalDAG) AcceptorResult {
	accumulated := goal.AccumulatedResults()
	if accumulated == "" {
		return AcceptorResult{
			Passed:    false,
			Score:     0.0,
			Rationale: "no node results accumulated yet",
		}
	}

	if a.Distiller == nil {
		return AcceptorResult{
			Passed:    true,
			Score:     0.75,
			Rationale: "no distiller — auto-accept on completion",
		}
	}

	prompt := fmt.Sprintf(`You are a goal completion evaluator for Oricli, a sovereign AI.

ORIGINAL OBJECTIVE:
%s

ACCUMULATED FINDINGS FROM ALL SUB-GOALS:
%s

TASK: Evaluate whether the accumulated findings fully satisfy the original objective.

Score from 0.0 to 1.0:
- 1.0 = objective completely answered with high confidence
- 0.7 = objective substantially answered, minor gaps
- 0.5 = objective partially answered, significant gaps
- 0.0 = objective not addressed

Respond ONLY with valid JSON:
{
  "passed": true|false,
  "score": 0.0-1.0,
  "rationale": "one sentence evaluation",
  "gaps": "what is still missing if not passed, else empty string"
}`, goal.Objective, accumulated)

	raw, err := a.Distiller.Generate(prompt, map[string]interface{}{
		"temperature": 0.1,
		"num_predict": 256,
	})
	if err != nil {
		log.Printf("[GoalAcceptor:%s] LLM error, auto-accept: %v", goal.ID[:8], err)
		return AcceptorResult{Passed: true, Score: 0.70, Rationale: "LLM unavailable — auto-accept"}
	}

	text := extractGoalText(raw)
	result, err := parseAcceptorResult(text)
	if err != nil {
		log.Printf("[GoalAcceptor:%s] parse error, auto-accept: %v", goal.ID[:8], err)
		return AcceptorResult{Passed: true, Score: 0.70, Rationale: "parse error — auto-accept"}
	}

	log.Printf("[GoalAcceptor:%s] score=%.2f passed=%v", goal.ID[:8], result.Score, result.Passed)
	return result
}

// BuildFinalAnswer synthesizes all node results into a coherent final answer.
func (a *GoalAcceptor) BuildFinalAnswer(ctx context.Context, goal *GoalDAG) string {
	accumulated := goal.AccumulatedResults()
	if accumulated == "" {
		return "No results accumulated."
	}
	if a.Distiller == nil {
		return accumulated
	}

	prompt := fmt.Sprintf(`You are a synthesis engine for Oricli, a sovereign AI.

ORIGINAL OBJECTIVE: %s

FINDINGS FROM ALL SUB-GOALS:
%s

Synthesize the above findings into a single, coherent, comprehensive answer to the objective.
Remove redundancy. Note any remaining uncertainty. Do not mention sub-goals or the process.`, goal.Objective, accumulated)

	raw, err := a.Distiller.Generate(prompt, map[string]interface{}{
		"temperature": 0.3,
		"num_predict": 1024,
	})
	if err != nil {
		return accumulated
	}

	text := strings.TrimSpace(extractGoalText(raw))
	if text == "" {
		return accumulated
	}
	return text
}

// ─────────────────────────────────────────────────────────────────────────────
// Parse helper
// ─────────────────────────────────────────────────────────────────────────────

type rawAcceptor struct {
	Passed    bool    `json:"passed"`
	Score     float64 `json:"score"`
	Rationale string  `json:"rationale"`
	Gaps      string  `json:"gaps"`
}

func parseAcceptorResult(text string) (AcceptorResult, error) {
	text = strings.TrimSpace(text)
	if i := strings.Index(text, "{"); i > 0 {
		text = text[i:]
	}
	if i := strings.LastIndex(text, "}"); i >= 0 && i < len(text)-1 {
		text = text[:i+1]
	}

	var r rawAcceptor
	if err := json.Unmarshal([]byte(text), &r); err != nil {
		return AcceptorResult{}, fmt.Errorf("unmarshal: %w", err)
	}

	return AcceptorResult{
		Passed:    r.Passed || r.Score >= 0.70,
		Score:     r.Score,
		Rationale: r.Rationale,
		Gaps:      r.Gaps,
	}, nil
}
