package service

import (
	"fmt"
	"strings"
)

// RealtimeCodeService replaces reasoning_code_completion, program_behavior_reasoning, and test_generation_reasoning.
// It leverages native string parsing, rapid context window slicing, and delegates heavy semantics to the SLM.
type RealtimeCodeService struct {
	GenService *GenerationService
}

func NewRealtimeCodeService(gen *GenerationService) *RealtimeCodeService {
	return &RealtimeCodeService{
		GenService: gen,
	}
}

// --- REASONING CODE COMPLETION ---

func (s *RealtimeCodeService) CompleteCode(params map[string]interface{}) (map[string]interface{}, error) {
	prefix, _ := params["prefix"].(string)
	suffix, _ := params["suffix"].(string)

	prompt := fmt.Sprintf("Complete the following code.\n\nPrefix:\n```\n%s\n```\n\nSuffix:\n```\n%s\n```\n\nProvide only the missing code to connect the prefix and suffix.", prefix, suffix)

	result, err := s.GenService.Generate(prompt, map[string]interface{}{
		"system": "You are an expert real-time code completion engine. Output only the precise completion logic.",
		"options": map[string]interface{}{
			"num_predict": 512,
		},
	})
	if err != nil {
		return nil, err
	}

	resultText, _ := result["text"].(string)
	completion := extractCodeBlocks(resultText)
	if completion == "" {
		completion = strings.TrimSpace(resultText)
	}

	return map[string]interface{}{
		"success":    true,
		"completion": completion,
		"raw":        resultText,
	}, nil
}

func (s *RealtimeCodeService) CompleteWithExplanation(params map[string]interface{}) (map[string]interface{}, error) {
	prefix, _ := params["prefix"].(string)

	prompt := fmt.Sprintf("Complete the following code and briefly explain why.\n\nCode:\n```\n%s\n```", prefix)

	result, err := s.GenService.Generate(prompt, map[string]interface{}{
		"system": "You are a senior engineer explaining code completion.",
		"options": map[string]interface{}{
			"num_predict": 1024,
		},
	})
	if err != nil {
		return nil, err
	}
	resultText, _ := result["text"].(string)

	return map[string]interface{}{
		"success":     true,
		"completion":  extractCodeBlocks(resultText),
		"explanation": resultText,
	}, nil
}

func (s *RealtimeCodeService) VerifyCompletion(params map[string]interface{}) (map[string]interface{}, error) {
	code, _ := params["code"].(string)
	completion, _ := params["completion"].(string)

	// Ultra-fast heuristic check natively in Go
	if strings.Contains(completion, "TODO") || strings.Contains(completion, "pass") {
		return map[string]interface{}{
			"success": false,
			"verified": false,
			"reason": "Contains placeholder logic",
		}, nil
	}

	prompt := fmt.Sprintf("Does this completion logically fit into the code?\nCode:\n%s\nCompletion:\n%s\nAnswer Yes or No and explain.", code, completion)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{
		"system": "You are a code verifier.",
		"options": map[string]interface{}{"num_predict": 256},
	})
	if err != nil {
		return nil, err
	}

	resultText, _ := result["text"].(string)
	verified := strings.HasPrefix(strings.ToLower(strings.TrimSpace(resultText)), "yes")

	return map[string]interface{}{
		"success":  true,
		"verified": verified,
		"reason":   resultText,
	}, nil
}

// --- PROGRAM BEHAVIOR REASONING ---

func (s *RealtimeCodeService) PredictExecution(params map[string]interface{}) (map[string]interface{}, error) {
	code, _ := params["code"].(string)
	inputs, _ := params["inputs"].(string)

	prompt := fmt.Sprintf("Predict the execution output of this code given the inputs.\n\nCode:\n```\n%s\n```\n\nInputs:\n%s\n\nProvide the expected standard output or return value.", code, inputs)

	result, err := s.GenService.Generate(prompt, map[string]interface{}{
		"system": "You are a deterministic code execution simulator.",
		"options": map[string]interface{}{"num_predict": 512},
	})
	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"success":    true,
		"prediction": result["text"],
	}, nil
}

func (s *RealtimeCodeService) FindEdgeCases(params map[string]interface{}) (map[string]interface{}, error) {
	code, _ := params["code"].(string)

	prompt := fmt.Sprintf("Analyze this code and list 3-5 critical edge cases that could cause it to fail or behave unexpectedly.\n\nCode:\n```\n%s\n```", code)

	result, err := s.GenService.Generate(prompt, map[string]interface{}{
		"system": "You are a QA engineer identifying edge cases.",
		"options": map[string]interface{}{"num_predict": 1024},
	})
	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"success":    true,
		"edge_cases": result["text"],
	}, nil
}

func (s *RealtimeCodeService) AnalyzeSideEffects(params map[string]interface{}) (map[string]interface{}, error) {
	code, _ := params["code"].(string)

	// Quick native scan for global vars, I/O, or mutable state logic
	sideEffects := []string{}
	lowerCode := strings.ToLower(code)
	if strings.Contains(lowerCode, "global ") {
		sideEffects = append(sideEffects, "Modifies global state")
	}
	if strings.Contains(lowerCode, "open(") || strings.Contains(lowerCode, "write(") {
		sideEffects = append(sideEffects, "Performs File I/O")
	}

	// Slm deep analysis
	prompt := fmt.Sprintf("Identify hidden side effects in this code (e.g., state mutation, I/O, network calls).\n\nCode:\n```\n%s\n```", code)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{
		"system": "You are a strict functional programming auditor.",
		"options": map[string]interface{}{"num_predict": 512},
	})
	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"success":      true,
		"side_effects": result["text"],
		"native_hints": sideEffects,
	}, nil
}

func (s *RealtimeCodeService) AnalyzeComplexity(params map[string]interface{}) (map[string]interface{}, error) {
	code, _ := params["code"].(string)

	prompt := fmt.Sprintf("Provide the Time (Big-O) and Space complexity for this code.\n\nCode:\n```\n%s\n```", code)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{
		"system": "You are an algorithm analysis engine. Be concise and precise.",
		"options": map[string]interface{}{"num_predict": 512},
	})
	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"success":    true,
		"complexity": result["text"],
	}, nil
}

// --- TEST GENERATION REASONING ---

func (s *RealtimeCodeService) GenerateTests(params map[string]interface{}) (map[string]interface{}, error) {
	code, _ := params["code"].(string)
	framework, _ := params["framework"].(string)
	if framework == "" {
		framework = "pytest"
	}

	prompt := fmt.Sprintf("Generate a complete, robust %s test suite for the following code. Include edge cases.\n\nCode:\n```\n%s\n```", framework, code)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{
		"system": "You are a test-driven development (TDD) expert. Return ONLY the test code inside markdown blocks.",
		"options": map[string]interface{}{"num_predict": 2048},
	})
	if err != nil {
		return nil, err
	}

	resultText, _ := result["text"].(string)
	tests := extractCodeBlocks(resultText)

	return map[string]interface{}{
		"success": true,
		"tests":   tests,
		"raw":     resultText,
	}, nil
}

func (s *RealtimeCodeService) IdentifyTestCases(params map[string]interface{}) (map[string]interface{}, error) {
	code, _ := params["code"].(string)

	prompt := fmt.Sprintf("List the necessary test cases (happy path, edge cases, error cases) for this code.\n\nCode:\n```\n%s\n```", code)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{
		"system": "You are a QA automation architect planning a test suite.",
		"options": map[string]interface{}{"num_predict": 1024},
	})
	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"success":    true,
		"test_cases": result["text"],
	}, nil
}

func (s *RealtimeCodeService) AnalyzeCoverage(params map[string]interface{}) (map[string]interface{}, error) {
	code, _ := params["code"].(string)
	tests, _ := params["tests"].(string)

	prompt := fmt.Sprintf("Analyze the test coverage of these tests against the original code. What branches or edge cases are missing?\n\nCode:\n```\n%s\n```\n\nTests:\n```\n%s\n```", code, tests)
	result, err := s.GenService.Generate(prompt, map[string]interface{}{
		"system": "You are a code coverage analyzer evaluating the completeness of a test suite.",
		"options": map[string]interface{}{"num_predict": 1024},
	})
	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"success":  true,
		"coverage": result["text"],
	}, nil
}
