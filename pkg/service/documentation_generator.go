package service

import (
	"fmt"
	"log"
	"time"
)

type DocumentationResult struct {
	Success    bool                   `json:"success"`
	Text       string                 `json:"text"`
	Docstrings map[string]string      `json:"docstrings,omitempty"`
	Metadata   map[string]interface{} `json:"metadata"`
}

type DocumentationGeneratorService struct {
	Orchestrator *GoOrchestrator
}

func NewDocumentationGeneratorService(orch *GoOrchestrator) *DocumentationGeneratorService {
	return &DocumentationGeneratorService{Orchestrator: orch}
}

func (s *DocumentationGeneratorService) GenerateDocstring(code string, style string) (*DocumentationResult, error) {
	startTime := time.Now()
	log.Printf("[DocGen] Generating docstrings (style: %s)", style)

	// Use Orchestrator to get analysis from sidecars
	analysis, err := s.Orchestrator.Execute("python_semantic_understanding.analyze_code", map[string]interface{}{"code": code}, 30*time.Second)
	if err != nil {
		return nil, fmt.Errorf("semantic analysis failed: %w", err)
	}

	// Synthesize docstring using the generation service
	prompt := fmt.Sprintf("Generate a comprehensive Python docstring in %s style for the following code analysis: %v", style, analysis)
	genRes, err := s.Orchestrator.Execute("cognitive_generator.generate_response", map[string]interface{}{
		"input": prompt,
		"context": "Focus on clarity, parameters, return types, and exceptions.",
	}, 60*time.Second)

	if err != nil {
		return nil, fmt.Errorf("generation stage failed: %w", err)
	}

	resMap := genRes.(map[string]interface{})
	return &DocumentationResult{
		Success: true,
		Text:    resMap["text"].(string),
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
			"style":          style,
		},
	}, nil
}

func (s *DocumentationGeneratorService) GenerateReadme(projectPath string) (*DocumentationResult, error) {
	startTime := time.Now()
	log.Printf("[DocGen] Generating README for project: %s", projectPath)

	// 1. Get project understanding
	projectRes, err := s.Orchestrator.Execute("python_project_understanding.understand_project", map[string]interface{}{"project": projectPath}, 60*time.Second)
	if err != nil {
		return nil, fmt.Errorf("project understanding failed: %w", err)
	}

	// 2. Synthesize README
	prompt := fmt.Sprintf("Generate a professional Markdown README for this project structure: %v", projectRes)
	genRes, err := s.Orchestrator.Execute("cognitive_generator.generate_response", map[string]interface{}{
		"input": prompt,
		"context": "Include sections for Overview, Installation, Usage, and Architecture.",
	}, 90*time.Second)

	if err != nil {
		return nil, fmt.Errorf("readme generation failed: %w", err)
	}

	resMap := genRes.(map[string]interface{})
	return &DocumentationResult{
		Success: true,
		Text:    resMap["text"].(string),
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
			"project_path":   projectPath,
		},
	}, nil
}

func (s *DocumentationGeneratorService) ExplainCode(code string, audience string) (*DocumentationResult, error) {
	startTime := time.Now()
	log.Printf("[DocGen] Explaining code for audience: %s", audience)

	prompt := fmt.Sprintf("Explain the following Python code to a %s: \n%s", audience, code)
	genRes, err := s.Orchestrator.Execute("cognitive_generator.generate_response", map[string]interface{}{
		"input": prompt,
	}, 60*time.Second)

	if err != nil {
		return nil, fmt.Errorf("explanation failed: %w", err)
	}

	resMap := genRes.(map[string]interface{})
	return &DocumentationResult{
		Success: true,
		Text:    resMap["text"].(string),
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
			"audience":       audience,
		},
	}, nil
}
