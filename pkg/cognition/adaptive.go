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
	expKeywords := []string{"explore options", "try different", "experiment", "weigh options", "trade-off"}
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
