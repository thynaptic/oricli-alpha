package service

import (
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
}

func NewSafetyService() *SafetyService {
	return &SafetyService{
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

func (s *SafetyService) AuditPlan(text string) SafetyResult {
	var findings []SafetyFinding
	
	for name, re := range s.VulnerabilityPatterns {
		if match := re.FindString(text); match != "" {
			findings = append(findings, SafetyFinding{
				Type:     name,
				Severity: "high",
				Evidence: match,
			})
		}
	}

	passed := len(findings) == 0
	decision := "proceed"
	if !passed {
		decision = "block"
	}

	return SafetyResult{
		Passed:   passed,
		Findings: findings,
		Decision: decision,
	}
}

func (s *SafetyService) DetectInjection(text string) (bool, []string) {
	normalized := strings.ToLower(text)
	var detected []string
	
	for _, p := range s.InjectionPatterns {
		if strings.Contains(normalized, p) {
			detected = append(detected, p)
		}
	}

	return len(detected) > 0, detected
}
