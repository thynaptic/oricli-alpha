package cognition

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"
)

// --- Pillar 25: Cognitive Generator Orchestrator ---
// Ported from Aurora's CognitiveGeneratorService.swift.
// Manages the lifecycle of generative tasks (Responses, Thoughts, Summaries).

type GenerationMethod string

const (
	MethodDirect    GenerationMethod = "direct"
	MethodChained   GenerationMethod = "chained"
	MethodReasoning GenerationMethod = "reasoning"
	MethodFallback  GenerationMethod = "fallback"
)

type ReasoningDepth string

const (
	DepthShallow ReasoningDepth = "shallow"
	DepthMedium  ReasoningDepth = "medium"
	DepthDeep    ReasoningDepth = "deep"
)

type GenResult struct {
	Text           string                 `json:"text"`
	Confidence     float64                `json:"confidence"`
	Method         GenerationMethod       `json:"method"`
	ReasoningDepth ReasoningDepth         `json:"reasoning_depth"`
	Diagnostic     map[string]interface{} `json:"diagnostic"`
}

type GenerationService interface {
	Generate(prompt string, options map[string]interface{}) (map[string]interface{}, error)
	Chat(messages []map[string]string, options map[string]interface{}) (map[string]interface{}, error)
}

type GeneratorOrchestrator struct {
	Engine     *SovereignEngine
	GenService GenerationService
}

func NewGeneratorOrchestrator(e *SovereignEngine) *GeneratorOrchestrator {
	return &GeneratorOrchestrator{Engine: e}
}

// GenerateResponse unifies orchestration, generation, and diagnostics.
func (g *GeneratorOrchestrator) GenerateResponse(ctx context.Context, input string, context string) (*GenResult, error) {
	log.Printf("[Generator] Orchestrating response for: %s", input)
	start := time.Now()

	// 1. Process through Sovereign Engine (Ported from Swift Orchestrator call)
	sovTrace, err := g.Engine.ProcessInference(ctx, input)
	if err != nil {
		return g.handleFallback(input, "sovereign_engine_fail"), nil
	}

	// 2. Determine Generation Method
	method := MethodDirect
	if len(input) > 100 || strings.Contains(strings.ToLower(input), "why") {
		method = MethodReasoning
	}

	// 3. Simulated Generation (In a full impl, this calls GenService)
	responseText := "PROCESSED_RESPONSE: " + input
	confidence := 0.92

	// 4. Final Output Audit (Adversarial)
	responseText, blocked := g.Engine.AuditOutput(responseText)
	if blocked {
		return &GenResult{
			Text:       responseText,
			Confidence: 1.0,
			Method:     MethodFallback,
		}, nil
	}

	return &GenResult{
		Text:       responseText,
		Confidence: confidence,
		Method:     method,
		Diagnostic: map[string]interface{}{
			"latency_ms": time.Since(start).Milliseconds(),
			"sov_trace":  sovTrace,
		},
	}, nil
}

// GenerateThoughts produces a thought graph for reasoning engines.
func (g *GeneratorOrchestrator) GenerateThoughts(ctx context.Context, query string, count int) []string {
	log.Printf("[Generator] Building thought graph (%d thoughts) for: %s", count, query)
	
	var thoughts []string
	for i := 1; i <= count; i++ {
		thoughts = append(thoughts, fmt.Sprintf("Thought %d: Analyzing potential path for %s", i, query))
	}
	return thoughts
}

// GenerateSummary produces a concise distillation of content.
func (g *GeneratorOrchestrator) GenerateSummary(content string, maxSentences int) string {
	sentences := strings.Split(content, ".")
	if len(sentences) <= maxSentences {
		return content
	}
	return strings.Join(sentences[:maxSentences], ".") + "."
}

func (g *GeneratorOrchestrator) handleFallback(input string, reason string) *GenResult {
	log.Printf("[Generator] CRITICAL: Using fallback for %s. Reason: %s", input, reason)
	return &GenResult{
		Text:       "I encountered a temporary cognitive block. Let's try again.",
		Confidence: 0.3,
		Method:     MethodFallback,
	}
}
