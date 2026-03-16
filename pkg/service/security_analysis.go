package service

import (
	"fmt"
	"log"
	"regexp"
	"strings"
	"sync"
	"time"
)

type SecurityFinding struct {
	Type        string `json:"type"`
	Description string `json:"description"`
	Severity    string `json:"severity"`
	Line        int    `json:"line"`
}

type SecurityAnalysisResult struct {
	Success         bool              `json:"success"`
	SecurityScore   int               `json:"security_score"`
	Vulnerabilities []SecurityFinding `json:"vulnerabilities"`
	InjectionRisks  []SecurityFinding `json:"injection_risks"`
	AuthIssues      []SecurityFinding `json:"auth_issues"`
	SecretsFound    []SecurityFinding `json:"secrets_found"`
	Summary         string            `json:"summary"`
	Metadata        map[string]interface{} `json:"metadata"`
}

type SecurityAnalysisService struct {
	Orchestrator *GoOrchestrator
}

func NewSecurityAnalysisService(orch *GoOrchestrator) *SecurityAnalysisService {
	return &SecurityAnalysisService{Orchestrator: orch}
}

func (s *SecurityAnalysisService) AnalyzeSecurity(code string) (*SecurityAnalysisResult, error) {
	startTime := time.Now()
	log.Printf("[SecurityAnalysis] Analyzing code security")

	var wg sync.WaitGroup
	wg.Add(4)

	var vulnerabilities, injectionRisks, authIssues, secrets []SecurityFinding
	var mu sync.Mutex

	lines := strings.Split(code, "\n")

	// 1. Secret Detection (High performance in Go)
	go func() {
		defer wg.Done()
		found := s.detectSecrets(lines)
		mu.Lock()
		secrets = found
		mu.Unlock()
	}()

	// 2. Injection Risks
	go func() {
		defer wg.Done()
		found := s.detectInjectionRisks(lines)
		mu.Lock()
		injectionRisks = found
		mu.Unlock()
	}()

	// 3. Vulnerability Detection (e.g., unsafe functions)
	go func() {
		defer wg.Done()
		found := s.detectVulnerabilities(lines)
		mu.Lock()
		vulnerabilities = found
		mu.Unlock()
	}()

	// 4. Auth Patterns
	go func() {
		defer wg.Done()
		found := s.detectAuthIssues(lines)
		mu.Lock()
		authIssues = found
		mu.Unlock()
	}()

	wg.Wait()

	score := 100 - (len(vulnerabilities)*10 + len(injectionRisks)*5 + len(secrets)*15 + len(authIssues)*5)
	if score < 0 { score = 0 }

	return &SecurityAnalysisResult{
		Success:         true,
		SecurityScore:   score,
		Vulnerabilities: vulnerabilities,
		InjectionRisks:  injectionRisks,
		AuthIssues:      authIssues,
		SecretsFound:    secrets,
		Summary:         fmt.Sprintf("Security analysis complete. Score: %d. Found %d issues.", score, len(vulnerabilities)+len(injectionRisks)+len(secrets)+len(authIssues)),
		Metadata: map[string]interface{}{
			"execution_time": time.Since(startTime).Seconds(),
		},
	}, nil
}

func (s *SecurityAnalysisService) detectSecrets(lines []string) []SecurityFinding {
	findings := []SecurityFinding{}
	// Common secret patterns
	patterns := map[string]*regexp.Regexp{
		"Generic Secret": regexp.MustCompile(`(?i)(key|secret|password|token|auth|pwd)\s*[:=]\s*['\"][a-zA-Z0-9\-_]{8,}['\"]`),
		"AWS Key":        regexp.MustCompile(`AKIA[0-9A-Z]{16}`),
	}

	for i, line := range lines {
		for name, re := range patterns {
			if re.MatchString(line) {
				findings = append(findings, SecurityFinding{
					Type:        "secret",
					Description: fmt.Sprintf("Potential %s found", name),
					Severity:    "high",
					Line:        i + 1,
				})
			}
		}
	}
	return findings
}

func (s *SecurityAnalysisService) detectInjectionRisks(lines []string) []SecurityFinding {
	findings := []SecurityFinding{}
	// Simple patterns for demonstration
	patterns := map[string]*regexp.Regexp{
		"SQL Injection": regexp.MustCompile(`(?i)execute\(.*%\s*\(.*\)\)` ),
		"OS Injection":  regexp.MustCompile(`(?i)os\.system\(.*\+.*\)` ),
	}

	for i, line := range lines {
		for name, re := range patterns {
			if re.MatchString(line) {
				findings = append(findings, SecurityFinding{
					Type:        "injection",
					Description: fmt.Sprintf("Potential %s risk", name),
					Severity:    "critical",
					Line:        i + 1,
				})
			}
		}
	}
	return findings
}

func (s *SecurityAnalysisService) detectVulnerabilities(lines []string) []SecurityFinding {
	findings := []SecurityFinding{}
	unsafeFunctions := map[string]string{
		"eval(":  "Use of unsafe eval() function",
		"exec(":  "Use of unsafe exec() function",
		"pickle.load(": "Unsafe deserialization using pickle",
	}

	for i, line := range lines {
		for fn, desc := range unsafeFunctions {
			if strings.Contains(line, fn) {
				findings = append(findings, SecurityFinding{
					Type:        "vulnerability",
					Description: desc,
					Severity:    "high",
					Line:        i + 1,
				})
			}
		}
	}
	return findings
}

func (s *SecurityAnalysisService) detectAuthIssues(lines []string) []SecurityFinding {
	findings := []SecurityFinding{}
	if strings.Contains(strings.Join(lines, "\n"), "verify=False") {
		findings = append(findings, SecurityFinding{
			Type:        "auth",
			Description: "Insecure SSL verification disabled (verify=False)",
			Severity:    "medium",
		})
	}
	return findings
}
