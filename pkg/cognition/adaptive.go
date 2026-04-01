package cognition

import (
	"math"
	"strings"
)

// --- Pillar 7: Adaptive Budgeting & Complexity Detection ---
// Ported from Aurora's MCTSComplexityDetector.swift.
// Dynamically adjusts MCTS parameters and exploration constant based on deep reasoning signals.

type AdaptiveBudget struct {
	Iterations         int
	RolloutDepth       int
	Concurrency        int
	Complexity         float64
	ExplorationBenefit float64
	RequiresMCTS       bool
	NumPredict         int // dynamic inference-time compute scaling (Gemini Deep Think law)
}

// ScaledNumPredict returns the appropriate num_predict token budget for this
// complexity level. Implements the Gemini Deep Think inference-time scaling law:
// more compute at higher complexity → higher quality, scaling holds beyond Olympiad level.
func (b AdaptiveBudget) ScaledNumPredict() int {
	switch {
	case b.Complexity >= 0.80:
		return 2048 // PhD / research level — maximum reasoning depth
	case b.Complexity >= 0.60:
		return 1536 // Complex multi-step
	case b.Complexity >= 0.40:
		return 1024 // Standard reasoning
	default:
		return 512 // Conversational / simple factual
	}
}

// DetermineBudget analyzes the query and returns an optimized MCTS setup.
func DetermineBudget(query string) AdaptiveBudget {
	complexity, benefit, factors := AnalyzeComplexity(query)
	
	budget := AdaptiveBudget{
		Complexity:         complexity,
		ExplorationBenefit: benefit,
		RequiresMCTS:       complexity >= 0.4 && benefit >= 0.3,
	}

	// 1. Iteration Budget (Ported from Swift estimatedRolloutBudget)
	if complexity > 0.8 {
		budget.Iterations = 200 // Maximum reasoning
		budget.RolloutDepth = 5
		budget.Concurrency = 8
	} else if complexity > 0.6 {
		budget.Iterations = 150
		budget.RolloutDepth = 4
		budget.Concurrency = 6
	} else if complexity > 0.4 {
		budget.Iterations = 100
		budget.RolloutDepth = 3
		budget.Concurrency = 4
	} else {
		budget.Iterations = 50 // Minimum baseline for MCTS
		budget.RolloutDepth = 2
		budget.Concurrency = 2
	}

	// 2. Performance Optimization for short queries
	if len(query) < 100 && budget.Iterations > 80 {
		budget.Iterations = 80
		budget.RolloutDepth = 2
	}

	_ = factors // Factors can be used for logging if needed
	return budget
}

// AnalyzeComplexity calculates deep reasoning signals from the query.
func AnalyzeComplexity(query string) (float64, float64, []string) {
	lower := strings.ToLower(query)
	totalScore := 0.0
	explorationBenefit := 0.0
	var factors []string

	// Factor 1: Uncertainty (30% max)
	uncertaintyKeywords := map[string]float64{
		"uncertain": 0.25, "probability": 0.20, "likely": 0.15, "risk": 0.20, "estimate": 0.15, "odds": 0.15,
	}
	uScore := 0.0
	for kw, weight := range uncertaintyKeywords {
		if strings.Contains(lower, kw) {
			uScore += weight
		}
	}
	uScore = math.Min(uScore, 0.30)
	if uScore > 0 {
		totalScore += uScore
		explorationBenefit += uScore * 0.8
		factors = append(factors, "uncertainty")
	}

	// Factor 2: Sequential Decision (30% max)
	seqKeywords := []string{"step by step", "sequential", "decision tree", "plan step", "multi-stage"}
	sScore := 0.0
	for _, kw := range seqKeywords {
		if strings.Contains(lower, kw) {
			sScore += 0.20
		}
	}
	sScore = math.Min(sScore, 0.30)
	if sScore > 0 {
		totalScore += sScore
		explorationBenefit += sScore * 0.7
		factors = append(factors, "sequential_decision")
	}

	// Factor 3: Exploration/Exploitation (35% max)
	expKeywords := []string{"explore options", "try different", "experiment", "weigh options", "trade-off", "tradeoff", "tradeoffs", "trade-offs"}
	eScore := 0.0
	for _, kw := range expKeywords {
		if strings.Contains(lower, kw) {
			eScore += 0.20
		}
	}
	eScore = math.Min(eScore, 0.35)
	if eScore > 0 {
		totalScore += eScore
		explorationBenefit += eScore * 0.9
		factors = append(factors, "exploration_benefit")
	}

	// Factor 4: Game Theory
	if strings.Contains(lower, "game theory") || strings.Contains(lower, "nash equilibrium") || strings.Contains(lower, "optimal strategy") {
		totalScore += 0.25
		explorationBenefit += 0.25 * 0.85
		factors = append(factors, "game_theory")
	}

	// Factor 5: Multi-Path Reasoning
	if strings.Contains(lower, "multiple paths") || strings.Contains(lower, "scenario analysis") || strings.Contains(lower, "what if") {
		totalScore += 0.18
		explorationBenefit += 0.18 * 0.75
		factors = append(factors, "multi_path")
	}

	// Factor 6: Optimization
	if strings.Contains(lower, "optimize") || strings.Contains(lower, "maximize") || strings.Contains(lower, "minimize") {
		totalScore += 0.15
		explorationBenefit += 0.15 * 0.6
		factors = append(factors, "optimization")
	}

	// Factor 7: Length and Structure
	if len(query) > 500 {
		totalScore += 0.10
	}
	qCount := strings.Count(query, "?")
	if qCount > 1 {
		totalScore += 0.08 * float64(qCount-1)
	}

	// Factor 8: Conceptual / Explanatory Complexity (25% max)
	// Catches "explain why X", "why is X harder than Y", "compare A and B",
	// "difference between", "implications of", "how does X work" — all high-reasoning queries
	// that score zero on MCTS factors but genuinely need multi-step reasoning.
	conceptualKeywords := []string{
		"explain why", "why is ", "why does", "why do ", "why are ",
		"how does", "how do ", "how can ", "how would ",
		"compare ", "difference between", "vs ", " versus ",
		"implications of", "fundamentally", "choosing between",
		"when should", "when to use", "pros and cons",
		"advantages and disadvantages", "impact of", "effect of",
		"causes of", "reason for", "reason why",
	}
	cScore := 0.0
	for _, kw := range conceptualKeywords {
		if strings.Contains(lower, kw) {
			cScore += 0.12
		}
	}
	cScore = math.Min(cScore, 0.25)
	if cScore > 0 {
		totalScore += cScore
		explorationBenefit += cScore * 0.7
		factors = append(factors, "conceptual_complexity")
	}

	// Factor 9: Long-form explanatory queries (moderate length + open-ended)
	// A 100-300 char question asking "explain/why/how/compare" is structurally more
	// complex than a 500-char list of bullet points.
	wordCount := len(strings.Fields(query))
	if wordCount >= 15 && wordCount < 60 && cScore > 0 {
		totalScore += 0.12
		factors = append(factors, "medium_length_conceptual")
	}

	return math.Min(1.0, totalScore), math.Min(1.0, explorationBenefit), factors
}

// ApplyToConfig updates an existing MCTSConfig with adaptive budget parameters.
func (b *AdaptiveBudget) ApplyToConfig(cfg *MCTSConfig) {
	cfg.Iterations = b.Iterations
	cfg.RolloutDepth = b.RolloutDepth
	cfg.MaxConcurrency = b.Concurrency
	
	// Modulate Exploration Constant (UCB1C) based on exploration benefit
	// Default UCB1C is 1.25. If benefit is high, we increase it to 2.0+
	if b.ExplorationBenefit > 0.5 {
		cfg.UCB1C = 1.25 + (b.ExplorationBenefit * 0.75)
	}
}
