package service

import (
	"fmt"
	"regexp"
	"strings"
)

type CodeIssue struct {
	Type        string `json:"type"`
	Severity    string `json:"severity"`
	Description string `json:"description"`
}

type CodeSafetyService struct {
	DangerousPatterns map[string]*regexp.Regexp
}

func NewCodeSafetyService() *CodeSafetyService {
	return &CodeSafetyService{
		DangerousPatterns: map[string]*regexp.Regexp{
			"unsafe_execution": regexp.MustCompile(`(?i)\b(eval|exec)\s*\(`),
			"os_traversal":    regexp.MustCompile(`(?i)\b(os\.system|subprocess\.run|shutil\.rmtree)\s*\(`),
			"bare_except":     regexp.MustCompile(`(?m)^(\s*)except:\s*$`),
			"potential_leak":  regexp.MustCompile(`(?i)open\s*\(`),
		},
	}
}

func (s *CodeSafetyService) Analyze(code string) []CodeIssue {
	var issues []CodeIssue

	for name, re := range s.DangerousPatterns {
		if match := re.FindString(code); match != "" {
			severity := "medium"
			if name == "unsafe_execution" || name == "os_traversal" {
				severity = "high"
			}
			issues = append(issues, CodeIssue{
				Type:        name,
				Severity:    severity,
				Description: fmt.Sprintf("Potential %s detected: %s", name, match),
			})
		}
	}

	// Check for 'with' statement if 'open' is found
	if strings.Contains(code, "open(") && !strings.Contains(code, "with open") {
		issues = append(issues, CodeIssue{
			Type:        "resource_leak",
			Severity:    "medium",
			Description: "File opened without 'with' context manager.",
		})
	}

	return issues
}
