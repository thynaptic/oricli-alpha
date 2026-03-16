package service

import (
	"fmt"
	"log"
	"time"
)

type CodeIssue struct {
	Type        string `json:"type"`
	Description string `json:"description"`
	Line        int    `json:"line"`
	Severity    string `json:"severity"`
}

type CodeReviewResult struct {
	Success      bool                   `json:"success"`
	QualityScore int                    `json:"quality_score"`
	Issues       []CodeIssue            `json:"issues"`
	Suggestions  []string               `json:"suggestions"`
	Summary      string                 `json:"summary"`
	Metadata     map[string]interface{} `json:"metadata"`
}

type CodeReviewService struct {
	Orchestrator *GoOrchestrator
}

func NewCodeReviewService(orch *GoOrchestrator) *CodeReviewService {
	return &CodeReviewService{Orchestrator: orch}
}

func (s *CodeReviewService) ReviewCode(code string, reviewType string) (*CodeReviewResult, error) {
	startTime := time.Now()
	log.Printf("[CodeReview] Reviewing code (%s)", reviewType)

	// 1. Parallel Analysis Stages
	// We'll use the Orchestrator to dispatch to specialized modules (Go or Python sidecars)
	
	// Stage A: Metrics & Quality (Can be parallelized)
	metricsRes, err := s.Orchestrator.Execute("python_code_metrics.analyze_metrics", map[string]interface{}{"code": code}, 20*time.Second)
	if err != nil {
		return nil, fmt.Errorf("metrics stage failed: %w", err)
	}

	// Stage B: Security Analysis
	securityRes, err := s.Orchestrator.Execute("python_security_analysis.analyze_security", map[string]interface{}{"code": code}, 30*time.Second)
	if err != nil {
		log.Printf("[CodeReview] Security analysis failed (skipped): %v", err)
	}

	// Stage C: Optimization Reasoning
	optRes, err := s.Orchestrator.Execute("code_optimization_reasoning.analyze_optimization", map[string]interface{}{"code": code}, 30*time.Second)
	if err != nil {
		log.Printf("[CodeReview] Optimization reasoning failed (skipped): %v", err)
	}

	// 2. Synthesize Review (using the Go Synthesis Agent logic)
	// For now, we'll build a structured result from the module outputs
	
	mMap := metricsRes.(map[string]interface{})
	score := 100
	if s, ok := mMap["overall_score"].(float64); ok {
		score = int(s)
	} else if s, ok := mMap["overall_score"].(int); ok {
		score = s
	}

	issues := []CodeIssue{}
	if securityRes != nil {
		sMap := securityRes.(map[string]interface{})
		if findings, ok := sMap["findings"].([]interface{}); ok {
			for _, f := range findings {
				fMap := f.(map[string]interface{})
				issues = append(issues, CodeIssue{
					Type:        "security",
					Description: fMap["description"].(string),
					Severity:    fMap["severity"].(string),
				})
			}
		}
	}

	suggestions := []string{}
	if optRes != nil {
		oMap := optRes.(map[string]interface{})
		if opts, ok := oMap["suggestions"].([]interface{}); ok {
			for _, s := range opts {
				suggestions = append(suggestions, s.(string))
			}
		}
	}

	return &CodeReviewResult{
		Success:      true,
		QualityScore: score,
		Issues:       issues,
		Suggestions:  suggestions,
		Summary:      fmt.Sprintf("Review complete. Code quality score: %d.", score),
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
			"review_type":    reviewType,
		},
	}, nil
}
