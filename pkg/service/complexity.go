package service

import (
	"fmt"
	"regexp"
	"strings"
)

type ComplexityFactor struct {
	Name         string  `json:"name"`
	Contribution float64 `json:"contribution"`
	Description  string  `json:"description"`
}

type ComplexityScore struct {
	Score             float64            `json:"score"`
	Factors           []ComplexityFactor `json:"factors"`
	RequiresCoT       bool               `json:"requires_cot"`
	RequiresToT       bool               `json:"requires_tot"`
	TimeoutMultiplier float64            `json:"timeout_multiplier"`
}

type ComplexityService struct {
	ReasoningKeywords map[string]float64
	MathPatterns      []*regexp.Regexp
	MultiPartKeywords []string
	DomainKeywords    map[string]float64
}

func NewComplexityService() *ComplexityService {
	return &ComplexityService{
		ReasoningKeywords: map[string]float64{
			"analyze": 0.25, "compare": 0.20, "calculate": 0.25, "derive": 0.30,
			"prove": 0.30, "explain why": 0.20, "step by step": 0.25, "reasoning": 0.20,
			"solve": 0.20, "evaluate": 0.20, "determine": 0.15, "find": 0.15,
		},
		MathPatterns: []*regexp.Regexp{
			regexp.MustCompile(`\d+\s*[+\-*/=<>≤≥]\s*\d+`),
			regexp.MustCompile(`\d+\s*\^\s*\d+`),
			regexp.MustCompile(`sqrt|√|∫|∑|∏|π|∞`),
			regexp.MustCompile(`(?i)equation|formula|theorem|proof|derivative|integral`),
		},
		MultiPartKeywords: []string{
			"first", "second", "third", "then", "next", "finally",
			"part a", "part b", "part 1", "part 2", "question 1", "question 2",
		},
		DomainKeywords: map[string]float64{
			"algorithm": 0.15, "complexity": 0.20, "optimization": 0.15,
			"architecture": 0.10, "hypothesis": 0.15, "experiment": 0.10,
			"theoretical": 0.15, "practical": 0.10,
		},
	}
}

func (s *ComplexityService) Analyze(query string) ComplexityScore {
	var factors []ComplexityFactor
	totalScore := 0.0
	queryLower := strings.ToLower(query)

	// 1. Length Factor
	lengthScore := float64(len(query)) / 500.0
	if lengthScore > 1.0 { lengthScore = 1.0 }
	lengthContrib := lengthScore * 0.15
	if lengthContrib > 0.05 {
		factors = append(factors, ComplexityFactor{"query_length", lengthContrib, fmt.Sprintf("Length: %d chars", len(query))})
		totalScore += lengthContrib
	}

	// 2. Reasoning Keywords
	keywordScore := 0.0
	var matched []string
	for kw, weight := range s.ReasoningKeywords {
		if strings.Contains(queryLower, kw) {
			keywordScore += weight
			matched = append(matched, kw)
		}
	}
	if keywordScore > 0.35 { keywordScore = 0.35 }
	if keywordScore > 0.05 {
		factors = append(factors, ComplexityFactor{"reasoning_keywords", keywordScore, "Matched: " + strings.Join(matched, ", ")})
		totalScore += keywordScore
	}

	// 3. Math Content
	mathScore := 0.0
	for _, re := range s.MathPatterns {
		if re.MatchString(query) {
			mathScore += 0.15
		}
	}
	if mathScore > 0.30 { mathScore = 0.30 }
	if mathScore > 0.05 {
		factors = append(factors, ComplexityFactor{"mathematical_content", mathScore, "Contains math symbols/terms"})
		totalScore += mathScore
	}

	// 4. Multi-part
	multiCount := 0
	for _, kw := range s.MultiPartKeywords {
		if strings.Contains(queryLower, kw) {
			multiCount++
		}
	}
	multiScore := float64(multiCount) * 0.10
	if multiScore > 0.20 { multiScore = 0.20 }
	if multiScore > 0.05 {
		factors = append(factors, ComplexityFactor{"multi_part_question", multiScore, fmt.Sprintf("Contains %d multi-part indicators", multiCount)})
		totalScore += multiScore
	}

	if totalScore > 1.0 { totalScore = 1.0 }

	return ComplexityScore{
		Score:             totalScore,
		Factors:           factors,
		RequiresCoT:       totalScore >= 0.6,
		RequiresToT:       totalScore >= 0.8,
		TimeoutMultiplier: s.getTimeoutMultiplier(totalScore),
	}
}

func (s *ComplexityService) getTimeoutMultiplier(score float64) float64 {
	if score < 0.4 { return 1.0 }
	if score < 0.6 { return 1.5 }
	if score < 0.8 { return 2.0 }
	return 3.0
}
