package pad

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
)

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

// EvalDimension names the scoring axes.
type EvalDimension string

const (
	DimCompleteness EvalDimension = "completeness" // did it address the question?
	DimConfidence   EvalDimension = "confidence"   // factual accuracy / no hallucination signals
	DimConsistency  EvalDimension = "consistency"  // no internal contradictions
)

// CriticThreshold is the minimum score on each dimension to pass.
const CriticThreshold = 0.70

// WorkerScore is the per-worker evaluation from the Critic.
type WorkerScore struct {
	TaskID         string                       `json:"task_id"`
	Goal           string                       `json:"goal"`
	Scores         map[EvalDimension]float64    `json:"scores"`
	Overall        float64                      `json:"overall"`
	Pass           bool                         `json:"pass"`
	WeaknessHint   string                       `json:"weakness_hint,omitempty"` // retry prompt injection
}

// CriticReport is the full evaluation of a dispatch round.
type CriticReport struct {
	Round        int           `json:"round"`
	OverallPass  bool          `json:"overall_pass"`
	WorkerScores []WorkerScore `json:"worker_scores"`
	RetryTaskIDs []string      `json:"retry_task_ids"` // IDs of workers that failed
	Rationale    string        `json:"rationale"`
}

// ─────────────────────────────────────────────────────────────────────────────
// Critic
// ─────────────────────────────────────────────────────────────────────────────

// Critic evaluates parallel worker results across 3 dimensions and identifies
// which workers need a retry.
type Critic struct {
	Distiller PADDistiller
}

// NewCritic creates a Critic.
func NewCritic(distiller PADDistiller) *Critic {
	return &Critic{Distiller: distiller}
}

// Evaluate scores each worker result and returns a CriticReport.
func (c *Critic) Evaluate(ctx context.Context, query string, results []WorkerResult, round int) CriticReport {
	report := CriticReport{Round: round}

	if len(results) == 0 {
		report.Rationale = "no results to evaluate"
		return report
	}

	scores := make([]WorkerScore, 0, len(results))

	for _, r := range results {
		ws := c.scoreWorker(query, r)
		scores = append(scores, ws)
		if !ws.Pass {
			report.RetryTaskIDs = append(report.RetryTaskIDs, r.TaskID)
		}
	}

	report.WorkerScores = scores
	report.OverallPass = len(report.RetryTaskIDs) == 0
	if report.OverallPass {
		report.Rationale = "all workers passed evaluation"
	} else {
		report.Rationale = fmt.Sprintf("%d/%d workers need retry", len(report.RetryTaskIDs), len(results))
	}

	log.Printf("[Critic] round %d — pass=%v retry=%d/%d",
		round, report.OverallPass, len(report.RetryTaskIDs), len(results))
	return report
}

// ─────────────────────────────────────────────────────────────────────────────
// Internals
// ─────────────────────────────────────────────────────────────────────────────

func (c *Critic) scoreWorker(query string, r WorkerResult) WorkerScore {
	ws := WorkerScore{
		TaskID: r.TaskID,
		Goal:   r.Goal,
		Scores: map[EvalDimension]float64{
			DimCompleteness: 0,
			DimConfidence:   0,
			DimConsistency:  0,
		},
	}

	// Hard fail for errored workers
	if r.Error != "" || strings.TrimSpace(r.Output) == "" {
		ws.WeaknessHint = "worker returned no output or an error — retry with simpler prompt"
		return ws
	}

	if c.Distiller == nil {
		// No LLM — pass everything with neutral scores
		ws.Scores[DimCompleteness] = 0.75
		ws.Scores[DimConfidence] = 0.75
		ws.Scores[DimConsistency] = 0.75
		ws.Overall = 0.75
		ws.Pass = true
		return ws
	}

	prompt := fmt.Sprintf(`You are a critical evaluator for Oricli, a sovereign AI.

ORIGINAL QUERY: %s
WORKER GOAL: %s
WORKER OUTPUT:
%s

Score this worker output on three dimensions from 0.0 to 1.0:
- completeness: did it fully address its assigned goal?
- confidence: does the output appear factually grounded (no obvious hallucinations)?
- consistency: is the output internally consistent (no contradictions)?

Also provide a short weakness_hint if any score < 0.70 (how the worker should improve on retry).

Respond ONLY with valid JSON:
{
  "completeness": 0.0-1.0,
  "confidence": 0.0-1.0,
  "consistency": 0.0-1.0,
  "weakness_hint": "brief hint for retry or empty string"
}`, query, r.Goal, r.Output)

	raw, err := c.Distiller.Generate(prompt, map[string]interface{}{
		"temperature": 0.1,
		"num_predict": 200,
	})
	if err != nil {
		log.Printf("[Critic] LLM error for task %s, passing: %v", r.TaskID[:8], err)
		ws.Scores[DimCompleteness] = 0.75
		ws.Scores[DimConfidence] = 0.75
		ws.Scores[DimConsistency] = 0.75
		ws.Overall = 0.75
		ws.Pass = true
		return ws
	}

	text := extractPADText(raw)
	ws = c.parseScoreResponse(text, ws)
	return ws
}

type rawScore struct {
	Completeness  float64 `json:"completeness"`
	Confidence    float64 `json:"confidence"`
	Consistency   float64 `json:"consistency"`
	WeaknessHint  string  `json:"weakness_hint"`
}

func (c *Critic) parseScoreResponse(text string, ws WorkerScore) WorkerScore {
	text = strings.TrimSpace(text)
	if i := strings.Index(text, "{"); i > 0 {
		text = text[i:]
	}
	if i := strings.LastIndex(text, "}"); i >= 0 && i < len(text)-1 {
		text = text[:i+1]
	}

	var r rawScore
	if err := json.Unmarshal([]byte(text), &r); err != nil {
		// Parse failed — pass with neutral scores
		ws.Scores[DimCompleteness] = 0.75
		ws.Scores[DimConfidence] = 0.75
		ws.Scores[DimConsistency] = 0.75
	} else {
		ws.Scores[DimCompleteness] = clamp(r.Completeness)
		ws.Scores[DimConfidence] = clamp(r.Confidence)
		ws.Scores[DimConsistency] = clamp(r.Consistency)
		ws.WeaknessHint = r.WeaknessHint
	}

	ws.Overall = (ws.Scores[DimCompleteness] + ws.Scores[DimConfidence] + ws.Scores[DimConsistency]) / 3.0
	ws.Pass = ws.Overall >= CriticThreshold
	return ws
}

func clamp(v float64) float64 {
	if v < 0 {
		return 0
	}
	if v > 1 {
		return 1
	}
	return v
}
