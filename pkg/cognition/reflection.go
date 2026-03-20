package cognition

import (
	"context"
	"fmt"
	"log"
	"strings"
	"sync"
)

// --- Pillar 33: Reasoning Reflection & Correction ---
// Ported from Aurora's ReasoningReflectionService.swift.
// Enables the system to review, identify errors, and correct its own reasoning steps.

type ReflectionTrigger struct {
	ShouldReflect bool
	Reason        string
}

type Correction struct {
	StepIndex  int
	Issue      string
	Suggestion string
}

type ReflectionEngine struct {
	MaxDepth int
	DepthMap map[string]int
	Mu       sync.Mutex
}

func NewReflectionEngine() *ReflectionEngine {
	return &ReflectionEngine{
		MaxDepth: 2,
		DepthMap: make(map[string]int),
	}
}

// ShouldTrigger checks if the current reasoning path requires a reflection pass.
func (e *ReflectionEngine) ShouldTrigger(confidence float64, thoughts []string) ReflectionTrigger {
	if confidence < 0.6 {
		return ReflectionTrigger{ShouldReflect: true, Reason: fmt.Sprintf("Low confidence: %.2f", confidence)}
	}

	// Detect Contradictions (Ported from Swift hasContradictions)
	contradictionPairs := [][]string{{"yes", "no"}, {"true", "false"}, {"is", "is not"}}
	fullText := strings.ToLower(strings.Join(thoughts, " "))
	for _, pair := range contradictionPairs {
		if strings.Contains(fullText, pair[0]) && strings.Contains(fullText, pair[1]) {
			return ReflectionTrigger{ShouldReflect: true, Reason: "Detected potential logical contradiction."}
		}
	}

	// Detect Shallow Reasoning
	if len(thoughts) > 0 && len(fullText)/len(thoughts) < 50 {
		return ReflectionTrigger{ShouldReflect: true, Reason: "Reasoning density is too low (shallow thinking)."}
	}

	return ReflectionTrigger{ShouldReflect: false}
}

// ReflectAndCorrect performs a meta-review of thoughts and returns improved versions.
func (e *ReflectionEngine) ReflectAndCorrect(ctx context.Context, sessionID string, query string, thoughts []string, gen *GeneratorOrchestrator) ([]string, bool) {
	e.Mu.Lock()
	depth := e.DepthMap[sessionID]
	if depth >= e.MaxDepth {
		log.Printf("[Reflection] Max depth reached for %s, skipping.", sessionID)
		e.Mu.Unlock()
		return thoughts, false
	}
	e.DepthMap[sessionID] = depth + 1
	e.Mu.Unlock()

	log.Printf("[Reflection] Analyzing reasoning path for: %s (Depth: %d)", query, depth+1)

	// 1. Generate Reflection Analysis (Simulated Meta-Review)
	// In full impl, this asks the Generator to "Review these steps: [steps]"
	issue := "Step 2 is missing a causal link."
	suggestion := "Explicitly state the relationship between X and Y."
	
	correction := Correction{
		StepIndex:  1, // 0-indexed
		Issue:      issue,
		Suggestion: suggestion,
	}

	// 2. Perform Surgical Correction
	improvedThoughts := make([]string, len(thoughts))
	copy(improvedThoughts, thoughts)
	
	if correction.StepIndex < len(improvedThoughts) {
		log.Printf("[Reflection] Correcting Step %d: %s", correction.StepIndex+1, correction.Issue)
		original := improvedThoughts[correction.StepIndex]
		improvedThoughts[correction.StepIndex] = fmt.Sprintf("%s [CORRECTED: %s]", original, correction.Suggestion)
	}

	return improvedThoughts, true
}

func (e *ReflectionEngine) ClearDepth(sessionID string) {
	e.Mu.Lock()
	defer e.Mu.Unlock()
	delete(e.DepthMap, sessionID)
}
