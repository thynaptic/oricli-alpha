package cognition

import (
	"log"
	"math"
	"strings"
)

// --- Pillar 28: Self-Verification Audit ---
// Ported from Aurora's SelfVerificationService.swift.
// Cross-checks reasoning paths and calculates verified confidence.

type VerificationCheck struct {
	Method     string  `json:"method"`
	Answer     string  `json:"answer"`
	Agrees     bool    `json:"agrees"`
	Confidence float64 `json:"confidence"`
}

type VerificationResult struct {
	OriginalAnswer   string              `json:"original_answer"`
	VerifiedAnswer   string              `json:"verified_answer"`
	VerifiedConfidence float64           `json:"verified_confidence"`
	AllChecksAgree   bool                `json:"all_checks_agree"`
	Checks           []VerificationCheck `json:"checks"`
}

type AuditEngine struct {
	Engine *SovereignEngine
}

func NewAuditEngine(e *SovereignEngine) *AuditEngine {
	return &AuditEngine{Engine: e}
}

// VerifyAnswer runs cross-checks on a generated thought path.
func (a *AuditEngine) VerifyAnswer(query string, originalAnswer string, originalConfidence float64) *VerificationResult {
	log.Printf("[AuditEngine] Verifying answer for: %s", query)
	
	var checks []VerificationCheck
	
	// 1. Symbolic Cross-Check (Simulated)
	// In a full impl, this would call the logic bridge
	symbolicAns := "VERIFIED: Calculation matches."
	symbolicConf := 1.0
	checks = append(checks, VerificationCheck{
		Method:     "symbolic",
		Answer:     symbolicAns,
		Agrees:     a.compareAnswers(originalAnswer, symbolicAns),
		Confidence: symbolicConf,
	})

	// 2. Alternative Path (Simulated CoT check)
	alternativeAns := originalAnswer // Mocking agreement for now
	alternativeConf := 0.85
	checks = append(checks, VerificationCheck{
		Method:     "cot",
		Answer:     alternativeAns,
		Agrees:     a.compareAnswers(originalAnswer, alternativeAns),
		Confidence: alternativeConf,
	})

	// 3. Final Arbiter Logic
	allAgree := true
	totalConf := originalConfidence
	for _, c := range checks {
		if !c.Agrees {
			allAgree = false
			totalConf -= 0.15 // Disagreement penalty
		} else {
			totalConf += (c.Confidence * 0.1) // Agreement boost
		}
	}

	return &VerificationResult{
		OriginalAnswer:     originalAnswer,
		VerifiedAnswer:     originalAnswer, // For now, keep original
		VerifiedConfidence: math.Max(0.1, math.Min(1.0, totalConf)),
		AllChecksAgree:     allAgree,
		Checks:             checks,
	}
}

func (a *AuditEngine) compareAnswers(ans1, ans2 string) bool {
	a1 := strings.ToLower(strings.TrimSpace(ans1))
	a2 := strings.ToLower(strings.TrimSpace(ans2))

	if a1 == a2 {
		return true
	}

	// Semantic similarity (Jaccard-like keyword overlap)
	words1 := a.getKeywords(a1)
	words2 := a.getKeywords(a2)

	if len(words1) == 0 || len(words2) == 0 {
		return false
	}

	intersection := 0
	for w := range words1 {
		if _, ok := words2[w]; ok {
			intersection++
		}
	}

	// If overlap > 50%, consider agreeing
	return float64(intersection)/float64(len(words1)) > 0.5
}

func (a *AuditEngine) getKeywords(text string) map[string]bool {
	words := make(map[string]bool)
	parts := strings.Fields(text)
	for _, p := range parts {
		if len(p) > 3 {
			words[strings.Trim(p, ".,!?;:")] = true
		}
	}
	return words
}
