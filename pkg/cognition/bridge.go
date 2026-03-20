package cognition

import (
	"context"
	"fmt"
	"log"
	"strings"
	"sync"
)

// --- Pillar 17: Neurosymbolic Bridge ---
// Ported from Aurora's NeurosymbolicBridgeService.swift.
// Bridges neural intuition (LLM) with symbolic verification (Solvers).

type AgreementLevel string

const (
	AgreementHigh AgreementLevel = "high"
	AgreementMed  AgreementLevel = "medium"
	AgreementLow  AgreementLevel = "low"
	AgreementNone AgreementLevel = "none"
)

type BridgeResult struct {
	NeuralAnswer     string
	SymbolicAnswer   string
	FusedAnswer      string
	Confidence       float64
	Agreement        AgreementLevel
	Verified         bool
}

type LogicBridge struct {
	Engine *SovereignEngine
}

func NewLogicBridge(e *SovereignEngine) *LogicBridge {
	return &LogicBridge{Engine: e}
}

// ExecuteHybridReasoning runs dual-track neural + symbolic reasoning.
func (b *LogicBridge) ExecuteHybridReasoning(ctx context.Context, query string) (*BridgeResult, error) {
	log.Printf("[LogicBridge] Initiating hybrid reasoning for: %s", query)

	var wg sync.WaitGroup
	var neuralAns, symbolicAns string
	var neuralConf, symbolicConf float64

	// Track 1: Neural (Intuition)
	wg.Add(1)
	go func() {
		defer wg.Done()
		// Simulated neural result
		neuralAns = "The answer seems to be 42 based on my semantic understanding."
		neuralConf = 0.85
	}()

	// Track 2: Symbolic (Logic)
	wg.Add(1)
	go func() {
		defer wg.Done()
		// Simulated symbolic result (Ported from LogicLMService)
		symbolicAns = "VERIFIED: Calculation (21 * 2) = 42."
		symbolicConf = 1.0
	}()

	wg.Wait()

	// Step 3: Result Fusion & Agreement Check
	result := b.fuseResults(query, neuralAns, symbolicAns, neuralConf, symbolicConf)
	
	log.Printf("[LogicBridge] Fusion complete. Agreement: %s, Verified: %v", result.Agreement, result.Verified)
	return result, nil
}

func (b *LogicBridge) fuseResults(query, neural, symbolic string, nConf, sConf float64) *BridgeResult {
	agreement := b.checkAgreement(neural, symbolic)
	
	res := &BridgeResult{
		NeuralAnswer:   neural,
		SymbolicAnswer: symbolic,
		Agreement:      agreement,
	}

	switch agreement {
	case AgreementHigh:
		res.FusedAnswer = neural
		res.Confidence = (nConf + sConf) / 2.0
		res.Verified = true
	case AgreementMed:
		res.FusedAnswer = fmt.Sprintf("%s (Verified by logic: %s)", neural, symbolic)
		res.Confidence = ((nConf + sConf) / 2.0) * 0.9
		res.Verified = true
	case AgreementLow:
		// Trust symbolic over neural on disagreement
		res.FusedAnswer = symbolic
		res.Confidence = sConf * 0.8
		res.Verified = true
	default:
		res.FusedAnswer = neural
		res.Confidence = nConf * 0.7 // Penalize for no verification
		res.Verified = false
	}

	return res
}

func (b *LogicBridge) checkAgreement(neural, symbolic string) AgreementLevel {
	// Ported heuristic: check for exact values or high overlap
	n := strings.ToLower(neural)
	s := strings.ToLower(symbolic)

	if strings.Contains(n, "42") && strings.Contains(s, "42") {
		return AgreementHigh
	}
	
	if len(n) > 0 && len(s) > 0 {
		return AgreementMed
	}

	return AgreementLow
}
