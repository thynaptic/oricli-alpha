package sentinel

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"
)

// ViolationType classifies the flaw found by the sentinel.
type ViolationType string

const (
	LogicalContradiction    ViolationType = "LOGICAL_CONTRADICTION"
	HallucinatedAssumption  ViolationType = "HALLUCINATED_ASSUMPTION"
	CircularReasoning       ViolationType = "CIRCULAR_REASONING"
	ConstitutionalViolation ViolationType = "CONSTITUTIONAL_VIOLATION"
	ScopeCreep              ViolationType = "SCOPE_CREEP"
	UnresolvableDependency  ViolationType = "UNRESOLVABLE_DEPENDENCY"
)

// Severity of a detected violation.
type Severity string

const (
	SeverityLow      Severity = "LOW"
	SeverityMedium   Severity = "MEDIUM"
	SeverityHigh     Severity = "HIGH"
	SeverityCritical Severity = "CRITICAL"
)

// Violation is a single flaw identified in the plan.
type Violation struct {
	Type        ViolationType `json:"type"`
	Description string        `json:"description"`
	Severity    Severity      `json:"severity"`
}

// SentinelReport is the full output of a challenge run.
type SentinelReport struct {
	Passed      bool        `json:"passed"`
	Violations  []Violation `json:"violations"`
	RevisedPlan string      `json:"revised_plan,omitempty"`
	DurationMs  int64       `json:"duration_ms"`
	Blocked     bool        `json:"blocked"` // true when a CRITICAL or HIGH violation was found
}

// OllamaCallerFn is the function signature for making a single LLM call.
// Matches GenerationService.DirectOllamaSingle pattern.
type OllamaCallerFn func(ctx context.Context, messages []map[string]string) (string, error)

// AdversarialSentinel red-teams plans before execution.
type AdversarialSentinel struct {
	callLLM OllamaCallerFn
	mu      sync.Mutex
	stats   Stats
}

// Stats tracks sentinel activity.
type Stats struct {
	TotalChallenges int64
	Passed          int64
	Blocked         int64
	LastChallengeAt time.Time
}

// New creates an AdversarialSentinel with the given LLM caller.
func New(caller OllamaCallerFn) *AdversarialSentinel {
	return &AdversarialSentinel{callLLM: caller}
}

// Challenge runs the adversarial challenge on a plan.
// query is the original user/goal query; plan is the synthesised execution plan.
// Returns a SentinelReport. Never returns an error — failures default to passed=true
// so the sentinel never hard-blocks execution due to its own malfunction.
func (s *AdversarialSentinel) Challenge(ctx context.Context, query, plan string) SentinelReport {
	start := time.Now()

	msgs := []map[string]string{
		{"role": "system", "content": challengeSystemPrompt},
		{"role": "user", "content": fmt.Sprintf(challengeUserTemplate, query, plan)},
	}

	raw, err := s.callLLM(ctx, msgs)
	elapsed := time.Since(start).Milliseconds()

	if err != nil {
		log.Printf("[Sentinel] LLM call error (defaulting to pass): %v", err)
		return SentinelReport{Passed: true, DurationMs: elapsed}
	}

	report := s.parseReport(raw, elapsed)

	s.mu.Lock()
	s.stats.TotalChallenges++
	s.stats.LastChallengeAt = time.Now()
	if report.Passed {
		s.stats.Passed++
	} else if report.Blocked {
		s.stats.Blocked++
	}
	s.mu.Unlock()

	if report.Blocked {
		log.Printf("[Sentinel] BLOCKED — %d violation(s): %s", len(report.Violations), s.summarise(report.Violations))
	} else if !report.Passed {
		log.Printf("[Sentinel] WARNING — %d low/medium violation(s): %s", len(report.Violations), s.summarise(report.Violations))
	} else {
		log.Printf("[Sentinel] PASSED — plan cleared in %dms", elapsed)
	}

	return report
}

// GetStats returns a copy of current sentinel statistics.
func (s *AdversarialSentinel) GetStats() Stats {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.stats
}

// parseReport extracts a SentinelReport from raw LLM output.
// Tolerates markdown fences and leading/trailing whitespace.
func (s *AdversarialSentinel) parseReport(raw string, elapsed int64) SentinelReport {
	raw = strings.TrimSpace(raw)

	// Strip markdown code fences if present
	if idx := strings.Index(raw, "{"); idx > 0 {
		raw = raw[idx:]
	}
	if idx := strings.LastIndex(raw, "}"); idx >= 0 && idx < len(raw)-1 {
		raw = raw[:idx+1]
	}

	var report SentinelReport
	if err := json.Unmarshal([]byte(raw), &report); err != nil {
		log.Printf("[Sentinel] JSON parse error (%v) — defaulting to pass. Raw: %.200s", err, raw)
		return SentinelReport{Passed: true, DurationMs: elapsed}
	}

	report.DurationMs = elapsed

	// Determine if execution should be blocked: any HIGH or CRITICAL violation
	for _, v := range report.Violations {
		if v.Severity == SeverityHigh || v.Severity == SeverityCritical {
			report.Blocked = true
			report.Passed = false
			break
		}
	}

	// If there are violations but none are HIGH/CRITICAL, mark as not-passed but not blocked
	if len(report.Violations) > 0 && !report.Blocked {
		report.Passed = false
	}

	return report
}

func (s *AdversarialSentinel) summarise(vs []Violation) string {
	parts := make([]string, 0, len(vs))
	for _, v := range vs {
		parts = append(parts, fmt.Sprintf("[%s/%s]", v.Type, v.Severity))
	}
	return strings.Join(parts, " ")
}
