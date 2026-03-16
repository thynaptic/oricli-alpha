package service

import (
	"fmt"
	"log"
	"time"
)

type CodeExplanationResult struct {
	Success     bool                   `json:"success"`
	Explanation string                 `json:"explanation,omitempty"`
	Answer      string                 `json:"answer,omitempty"`
	Audience    string                 `json:"audience,omitempty"`
	DetailLevel string                 `json:"detail_level,omitempty"`
	Metadata    map[string]interface{} `json:"metadata"`
}

type CodeExplanationService struct {
	Orchestrator *GoOrchestrator
}

func NewCodeExplanationService(orch *GoOrchestrator) *CodeExplanationService {
	return &CodeExplanationService{Orchestrator: orch}
}

func (s *CodeExplanationService) ExplainCode(code string, audience string, detailLevel string) (*CodeExplanationResult, error) {
	startTime := time.Now()
	log.Printf("[CodeExplanation] Explaining code (audience: %s, detail: %s)", audience, detailLevel)

	prompt := fmt.Sprintf("Explain the following Python code to a %s. Provide a %s level of detail.\n\n```python\n%s\n```", audience, detailLevel, code)
	
	res, err := s.Orchestrator.Execute("cognitive_generator.generate_response", map[string]interface{}{"input": prompt}, 60*time.Second)
	if err != nil {
		return nil, fmt.Errorf("explanation generation failed: %w", err)
	}

	explanation := res.(map[string]interface{})["text"].(string)

	return &CodeExplanationResult{
		Success:     true,
		Explanation: explanation,
		Audience:    audience,
		DetailLevel: detailLevel,
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
		},
	}, nil
}

func (s *CodeExplanationService) AnswerCodeQuestion(code string, question string) (*CodeExplanationResult, error) {
	startTime := time.Now()
	log.Printf("[CodeExplanation] Answering question about code: %s", question)

	prompt := fmt.Sprintf("Answer the following question about this Python code:\nQuestion: %s\n\nCode:\n```python\n%s\n```", question, code)
	
	res, err := s.Orchestrator.Execute("cognitive_generator.generate_response", map[string]interface{}{"input": prompt}, 60*time.Second)
	if err != nil {
		return nil, fmt.Errorf("answer generation failed: %w", err)
	}

	answer := res.(map[string]interface{})["text"].(string)

	return &CodeExplanationResult{
		Success: true,
		Answer:  answer,
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
		},
	}, nil
}
