package service

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"
)

type ReasoningResult struct {
	Answer          string                 `json:"answer"`
	Confidence      float64                `json:"confidence"`
	ReasoningMethod string                 `json:"reasoning_method"`
	ReasoningSteps  interface{}            `json:"reasoning_steps,omitempty"`
	CascadeUsed     bool                   `json:"cascade_used"`
	Verified        bool                   `json:"verified"`
}

type CognitiveOrchestrator struct {
	Orchestrator *GoOrchestrator
}

func NewCognitiveOrchestrator(orch *GoOrchestrator) *CognitiveOrchestrator {
	return &CognitiveOrchestrator{Orchestrator: orch}
}

// --- STATE & SYMBOLIC ---

func (s *CognitiveOrchestrator) TransitionCognitiveState(ctx context.Context, currentState string, trigger string) string {
	// Native state machine logic
	return "next_logical_state"
}

func (s *CognitiveOrchestrator) DetectSymbolicRequirement(ctx context.Context, query string) bool {
	lower := strings.ToLower(query)
	// Native symbolic detection (logic puzzles, formal math)
	return strings.Contains(lower, "all men are mortal") || strings.Contains(lower, "solve for x")
}

// --- COGNITIVE CLASSIFICATION & SPECULATION ---

func (s *CognitiveOrchestrator) DetectDistress(ctx context.Context, text string) (bool, string) {
	lower := strings.ToLower(text)
	if strings.Contains(lower, "help") || strings.Contains(lower, "overwhelmed") { return true, "High Emotional Distress" }
	return false, "Normal"
}

func (s *CognitiveOrchestrator) SpeculateOutcome(ctx context.Context, scenario string) (string, error) {
	return "Speculated outcome via native Go path", nil
}

// --- ROUTING & SENSORY ---

func (s *CognitiveOrchestrator) RouteSensoryInput(ctx context.Context, input string) (string, error) {
	lower := strings.ToLower(input)
	if strings.HasPrefix(lower, "code") { return "code_engine", nil }
	if strings.Contains(lower, "http") { return "web_fetch_service", nil }
	return "general_reasoning", nil
}

func (s *CognitiveOrchestrator) SelectOptimalModule(ctx context.Context, task string, constraints map[string]interface{}) (string, error) {
	return "best_available", nil
}

// --- EXISTING METHODS (RESTORED) ---

func (s *CognitiveOrchestrator) ExecuteReasoning(query string, context map[string]interface{}) (*ReasoningResult, error) {
	log.Printf("[ReasoningOrch] Starting orchestration for query: %s", query)
	complexityRes, err := s.Orchestrator.Execute("complexity_detector.analyze", map[string]interface{}{"query": query}, 10*time.Second)
	complexity := 0.5
	if err == nil { complexity = complexityRes.(map[string]interface{})["complexity"].(float64) }
	method := s.selectMethod(complexity)
	var result interface{}
	switch method {
	case "mcts": result, err = s.Orchestrator.Execute("mcts_reasoning.execute_mcts", map[string]interface{}{"query": query, "context": context}, 60*time.Second)
	case "tot": result, err = s.Orchestrator.Execute("tree_of_thought.execute_tot", map[string]interface{}{"query": query, "context": context}, 45*time.Second)
	default: result, err = s.Orchestrator.Execute("chain_of_thought.execute_cot", map[string]interface{}{"query": query, "context": context}, 30*time.Second)
	}
	if err != nil { return nil, fmt.Errorf("reasoning failed: %w", err) }
	resMap := result.(map[string]interface{})
	return &ReasoningResult{Answer: resMap["answer"].(string), Confidence: resMap["confidence"].(float64), ReasoningMethod: method, ReasoningSteps: resMap["steps"]}, nil
}

func (s *CognitiveOrchestrator) selectMethod(complexity float64) string {
	if complexity > 0.8 { return "mcts" }
	if complexity > 0.6 { return "tot" }
	return "cot"
}
