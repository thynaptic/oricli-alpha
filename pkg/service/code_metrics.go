package service

import (
	"log"
	"fmt"
	"strings"
	"sync"
	"time"
)

type CodeMetrics struct {
	LinesOfCode           int     `json:"lines_of_code"`
	FunctionCount         int     `json:"functions"`
	ClassCount            int     `json:"classes"`
	ImportCount           int     `json:"imports"`
	AverageFunctionLength float64 `json:"average_function_length"`
	OverallScore          float64 `json:"overall_score"`
}

type ComplexityMetrics struct {
	Cyclomatic int `json:"cyclomatic"`
	Cognitive  int `json:"cognitive"`
}

type CodeMetricsResult struct {
	Success         bool              `json:"success"`
	Complexity      ComplexityMetrics `json:"complexity"`
	Maintainability float64           `json:"maintainability"`
	Statistics      CodeMetrics       `json:"statistics"`
	Summary         string            `json:"summary"`
	Metadata        map[string]interface{} `json:"metadata"`
}

type CodeMetricsService struct {
	Orchestrator *GoOrchestrator
}

func NewCodeMetricsService(orch *GoOrchestrator) *CodeMetricsService {
	return &CodeMetricsService{Orchestrator: orch}
}

func (s *CodeMetricsService) CalculateMetrics(code string) (*CodeMetricsResult, error) {
	startTime := time.Now()
	log.Printf("[CodeMetrics] Calculating metrics for code snippet")

	lines := strings.Split(code, "\n")
	loc := len(lines)

	// Naive concurrent counters for demonstration
	var wg sync.WaitGroup
	var funcCount, classCount, importCount int
	var mu sync.Mutex

	wg.Add(3)
	go func() {
		defer wg.Done()
		count := 0
		for _, line := range lines {
			if strings.Contains(line, "def ") { count++ }
		}
		mu.Lock(); funcCount = count; mu.Unlock()
	}()
	go func() {
		defer wg.Done()
		count := 0
		for _, line := range lines {
			if strings.Contains(line, "class ") { count++ }
		}
		mu.Lock(); classCount = count; mu.Unlock()
	}()
	go func() {
		defer wg.Done()
		count := 0
		for _, line := range lines {
			if strings.Contains(line, "import ") || strings.Contains(line, "from ") { count++ }
		}
		mu.Lock(); importCount = count; mu.Unlock()
	}()
	wg.Wait()

	// Heuristic scores
	cyclomatic := (funcCount * 2) + (loc / 20)
	cognitive := (funcCount * 3) + (classCount * 5)
	maintainability := 100.0 - float64(cyclomatic+cognitive)/5.0
	if maintainability < 0 { maintainability = 0 }

	return &CodeMetricsResult{
		Success: true,
		Complexity: ComplexityMetrics{
			Cyclomatic: cyclomatic,
			Cognitive:  cognitive,
		},
		Maintainability: maintainability,
		Statistics: CodeMetrics{
			LinesOfCode:   loc,
			FunctionCount: funcCount,
			ClassCount:    classCount,
			ImportCount:   importCount,
			OverallScore:  maintainability,
		},
		Summary: fmt.Sprintf("Calculated metrics for %d lines of code. Maintainability score: %.2f.", loc, maintainability),
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
		},
	}, nil
}
