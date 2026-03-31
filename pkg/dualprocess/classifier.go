package dualprocess

import (
	"strings"
)

// noveltySigs are patterns that signal the query is non-templatic / novel.
var noveltySigs = []string{
	"never", "unusual", "hypothetical", "imagine", "suppose", "what if",
	"novel", "unprecedented", "invent", "design from scratch", "first principles",
	"no prior", "unique", "edge case", "corner case",
}

// abstractionSigs signal high conceptual / abstract demand.
var abstractionSigs = []string{
	"philosophy", "theory", "concept", "meaning", "implication", "ethics",
	"abstract", "principle", "framework", "paradigm", "meta", "ontology",
	"epistemology", "nature of", "what is the relationship", "define",
	"fundamentally", "essentially", "in general",
}

// multiStepSigs signal chained reasoning requirements.
var multiStepSigs = []string{
	"step by step", "walk me through", "how would you", "plan",
	"sequence", "order of operations", "first then", "if then else",
	"chain", "pipeline", "workflow", "and then", "after that",
	"subsequently", "trace through", "derive", "prove",
}

// contradictionSigs signal hidden traps or contradiction risk.
var contradictionSigs = []string{
	"always", "never", "every", "all", "none", "impossible",
	"must", "cannot", "guaranteed", "certain", "without exception",
	"paradox", "contradiction", "but", "however", "although",
	"except", "unless", "only if",
}

// s2TaskClasses are topic classes that inherently require System 2 reasoning.
var s2TaskClasses = map[string]bool{
	"technical":   true,
	"procedural":  true,
	"comparative": true,
}

// ProcessClassifier classifies incoming queries into S1/S2 demand profiles.
type ProcessClassifier struct{}

// NewProcessClassifier creates a ProcessClassifier.
func NewProcessClassifier() *ProcessClassifier { return &ProcessClassifier{} }

// Classify scores the query across 4 demand dimensions and returns a ProcessDemand.
func (c *ProcessClassifier) Classify(query, taskClass string) ProcessDemand {
	lower := strings.ToLower(query)
	words := strings.Fields(lower)
	wordCount := len(words)

	var reasons []string

	// ── Novelty ──────────────────────────────────────────────────────────────
	noveltyScore := scoreSignals(lower, noveltySigs, 0.15)
	if wordCount > 40 {
		noveltyScore = clamp(noveltyScore+0.1, 0, 1)
		reasons = append(reasons, "long query (+novelty)")
	}
	if noveltyScore > 0.3 {
		reasons = append(reasons, "novelty signals detected")
	}

	// ── Abstraction ──────────────────────────────────────────────────────────
	abstractionScore := scoreSignals(lower, abstractionSigs, 0.12)
	if s2TaskClasses[taskClass] {
		abstractionScore = clamp(abstractionScore+0.15, 0, 1)
		reasons = append(reasons, "S2-class task ("+taskClass+")")
	}

	// ── Multi-step ───────────────────────────────────────────────────────────
	multiStepScore := scoreSignals(lower, multiStepSigs, 0.15)
	// Sentence count proxy: count question marks + periods as step boundaries
	sentenceCount := strings.Count(lower, ".") + strings.Count(lower, "?") + strings.Count(lower, ";")
	if sentenceCount >= 3 {
		multiStepScore = clamp(multiStepScore+float64(sentenceCount)*0.05, 0, 1)
		reasons = append(reasons, "multi-sentence query (+steps)")
	}

	// ── Contradiction ────────────────────────────────────────────────────────
	contradictionScore := scoreSignals(lower, contradictionSigs, 0.10)
	if contradictionScore > 0.3 {
		reasons = append(reasons, "absolute/conditional language (+contradiction risk)")
	}

	// ── Weighted aggregate ───────────────────────────────────────────────────
	// Weights: multi-step most predictive, then novelty, then abstraction, then contradiction
	score := noveltyScore*0.25 + abstractionScore*0.20 + multiStepScore*0.35 + contradictionScore*0.20

	// S2-class tasks have a lower activation threshold — they inherently need deliberation.
	threshold := 0.35
	if s2TaskClasses[taskClass] {
		threshold = 0.18
	}

	tier := TierS1
	if score >= threshold {
		tier = TierS2
		if len(reasons) == 0 {
			reasons = append(reasons, "aggregate S2 threshold reached")
		}
	}

	return ProcessDemand{
		Novelty:       noveltyScore,
		Abstraction:   abstractionScore,
		MultiStep:     multiStepScore,
		Contradiction: contradictionScore,
		Score:         score,
		Tier:          tier,
		TaskClass:     taskClass,
		Reasons:       reasons,
	}
}

// ── helpers ───────────────────────────────────────────────────────────────────

// scoreSignals returns a [0,1] score based on how many signals from the list appear in text.
// Each hit adds `weight`; score is clamped to 1.0.
func scoreSignals(text string, signals []string, weight float64) float64 {
	score := 0.0
	for _, sig := range signals {
		if strings.Contains(text, sig) {
			score += weight
		}
	}
	return clamp(score, 0, 1)
}

func clamp(v, min, max float64) float64 {
	if v < min {
		return min
	}
	if v > max {
		return max
	}
	return v
}
