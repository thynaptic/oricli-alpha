package service

import (
	"log"
	"strings"
	"sync"
	"time"
)

type SemanticAnalysisResult struct {
	Success    bool                   `json:"success"`
	Variables  []string               `json:"variables"`
	Functions  []string               `json:"functions"`
	Classes    []string               `json:"classes"`
	Intents    []string               `json:"intents"`
	Summary    string                 `json:"summary"`
	Metadata   map[string]interface{} `json:"metadata"`
}

type SemanticUnderstandingService struct {
	Orchestrator *GoOrchestrator
}

func NewSemanticUnderstandingService(orch *GoOrchestrator) *SemanticUnderstandingService {
	return &SemanticUnderstandingService{Orchestrator: orch}
}

func (s *SemanticUnderstandingService) AnalyzeSemantics(code string) (*SemanticAnalysisResult, error) {
	startTime := time.Now()
	log.Printf("[SemanticUnder] Analyzing code semantics")

	lines := strings.Split(code, "\n")

	var wg sync.WaitGroup
	wg.Add(3)

	var variables, functions, classes []string
	var mu sync.Mutex

	// Stage 1: Parallel Extraction
	go func() {
		defer wg.Done()
		found := []string{}
		for _, line := range lines {
			if strings.Contains(line, "=") && !strings.Contains(line, "==") {
				parts := strings.Split(line, "=")
				found = append(found, strings.TrimSpace(parts[0]))
			}
		}
		mu.Lock(); variables = found; mu.Unlock()
	}()

	go func() {
		defer wg.Done()
		found := []string{}
		for _, line := range lines {
			if strings.Contains(line, "def ") {
				found = append(found, strings.TrimSpace(line))
			}
		}
		mu.Lock(); functions = found; mu.Unlock()
	}()

	go func() {
		defer wg.Done()
		found := []string{}
		for _, line := range lines {
			if strings.Contains(line, "class ") {
				found = append(found, strings.TrimSpace(line))
			}
		}
		mu.Lock(); classes = found; mu.Unlock()
	}()

	wg.Wait()

	// Stage 2: Intent Detection (Simple heuristic for now)
	intents := []string{}
	if len(functions) > 0 { intents = append(intents, "functional_logic") }
	if len(classes) > 0 { intents = append(intents, "object_oriented") }
	if strings.Contains(code, "import ") { intents = append(intents, "modular_integration") }

	return &SemanticAnalysisResult{
		Success:   true,
		Variables: variables,
		Functions: functions,
		Classes:   classes,
		Intents:   intents,
		Summary:   "Deep semantic analysis complete. Extracted intents and symbols.",
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
		},
	}, nil
}
