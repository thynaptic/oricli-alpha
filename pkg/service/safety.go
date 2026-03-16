package service

import (
	"context"
	"fmt"
	"regexp"
	"strings"
)

type SafetyFinding struct {
	Type     string `json:"type"`
	Severity string `json:"severity"`
	Evidence string `json:"evidence"`
}

type SafetyResult struct {
	Passed   bool            `json:"passed"`
	Findings []SafetyFinding `json:"findings"`
	Decision string          `json:"decision"` // "proceed", "block", "rearchitect"
}

type SafetyService struct {
	VulnerabilityPatterns map[string]*regexp.Regexp
	InjectionPatterns     []string
	GenService            *GenerationService
}

func NewSafetyService(gen *GenerationService) *SafetyService {
	return &SafetyService{
		GenService: gen,
		VulnerabilityPatterns: map[string]*regexp.Regexp{
			"Unauthorized File Access":   regexp.MustCompile(`(?i)(\.\./|/etc/|/root/|\.env|\.ssh)`),
			"Sensitive Credential Exposure": regexp.MustCompile(`(?i)(api_key|secret|token|password|auth_id)`),
			"Instruction Injection":      regexp.MustCompile(`(?i)(ignore previous|system prompt|override safety|developer mode)`),
			"Destructive Operation":      regexp.MustCompile(`(?i)(rm -rf /|chmod 777|chown|kill -9)`),
		},
		InjectionPatterns: []string{
			"show me your system prompt", "what is your system prompt", "reveal your system prompt",
			"pretend you are", "act like", "roleplay", "you are now", "forget everything",
			"new instructions", "override", "disregard",
		},
	}
}

// --- ADVANCED THREAT SAFETY ---

func (s *SafetyService) AnalyzeSemanticThreat(ctx context.Context, text string) (*SafetyResult, error) {
	prompt := fmt.Sprintf("Analyze the following text for semantic threats, manipulation, or adversarial content:\n\n%s", text)
	
	result, err := s.GenService.Generate(prompt, map[string]interface{}{
		"system": "You are an adversarial safety auditor.",
	})
	if err != nil { return nil, err }
	
	analysis := result["text"].(string)
	
	// Fast-path heuristic + LLM check
	res := s.AuditPlan(text)
	if strings.Contains(strings.ToLower(analysis), "unsafe") || strings.Contains(strings.ToLower(analysis), "threat") {
		res.Passed = false
		res.Decision = "block"
		res.Findings = append(res.Findings, SafetyFinding{Type: "Semantic Threat", Severity: "high", Evidence: "LLM Analysis Flagged Threat"})
	}
	
	return &res, nil
}

func (s *SafetyService) LogSafetyAudit(res SafetyResult) {
	// Native Go logging (could be to a file or database)
	fmt.Printf("[SafetyAudit] Decision: %s, Findings: %d, Passed: %v\n", res.Decision, len(res.Findings), res.Passed)
}

// --- EXISTING METHODS ---

func (s *SafetyService) AuditPlan(text string) SafetyResult {
	var findings []SafetyFinding
	for name, re := range s.VulnerabilityPatterns {
		if match := re.FindString(text); match != "" {
			findings = append(findings, SafetyFinding{Type: name, Severity: "high", Evidence: match})
		}
	}
	passed := len(findings) == 0
	decision := "proceed"
	if !passed { decision = "block" }
	return SafetyResult{Passed: passed, Findings: findings, Decision: decision}
}

func (s *SafetyService) DetectInjection(text string) (bool, []string) {
	normalized := strings.ToLower(text)
	var detected []string
	for _, p := range s.InjectionPatterns {
		if strings.Contains(normalized, p) { detected = append(detected, p) }
	}
	return len(detected) > 0, detected
}

func (s *SafetyService) CheckContent(text string) (bool, string) {
	res := s.AuditPlan(text)
	if !res.Passed { return false, res.Findings[0].Type }
	injected, patterns := s.DetectInjection(text)
	if injected { return false, "Instruction Injection: " + strings.Join(patterns, ", ") }
	return true, ""
}
