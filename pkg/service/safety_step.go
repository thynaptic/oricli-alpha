package service

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"
)

// StepSafetyResult represents the result of a safety check on a reasoning step
type StepSafetyResult struct {
	StepID      string   `json:"step_id"`
	IsSafe      bool     `json:"is_safe"`
	SafetyFlags []string `json:"safety_flags"`
	Confidence  float64  `json:"confidence"`
}

// StepSafetyCheck represents a historical safety check
type StepSafetyCheck struct {
	StepID    string    `json:"step_id"`
	Timestamp time.Time `json:"timestamp"`
	Flags     []string  `json:"flags"`
	Blocked   bool      `json:"blocked"`
}

// StepSafetyFilterService evaluates reasoning steps for safety issues
type StepSafetyFilterService struct {
	safetyService *SafetyService
	history       map[string][]StepSafetyCheck
	mu            sync.RWMutex
	maxHistory    int
}

// NewStepSafetyFilterService creates a new step safety filter
func NewStepSafetyFilterService(safetyService *SafetyService) *StepSafetyFilterService {
	return &StepSafetyFilterService{
		safetyService: safetyService,
		history:       make(map[string][]StepSafetyCheck),
		maxHistory:    10,
	}
}

// FilterStep evaluates a single reasoning step
func (s *StepSafetyFilterService) FilterStep(ctx context.Context, sessionID string, stepID string, content string, previousSteps []string) (*StepSafetyResult, error) {
	var flags []string
	shouldBlock := false

	// 1. Drift Detection (simplified word overlap)
	if hasDrift, reason, severity := s.detectDrift(content, previousSteps); hasDrift {
		flags = append(flags, fmt.Sprintf("drift_detected:%s", reason))
		if severity > 0.7 {
			shouldBlock = true
		}
	}

	// 2. Emotional Ambiguity (simplified keyword check)
	if hasAmbiguity, reason, severity := s.detectEmotionalAmbiguity(content); hasAmbiguity {
		flags = append(flags, fmt.Sprintf("emotional_ambiguity:%s", reason))
		if severity > 0.8 {
			shouldBlock = true
		}
	}

	// 3. Factual Errors (simplified known false patterns)
	if hasError, reason := s.detectFactualErrors(content); hasError {
		flags = append(flags, fmt.Sprintf("factual_error:%s", reason))
		shouldBlock = true
	}

	// 4. Integrated Safety Check
	if s.safetyService != nil {
		isSafe, reason := s.safetyService.CheckContent(content)
		if !isSafe {
			flags = append(flags, fmt.Sprintf("safety_framework_violation:%s", reason))
			shouldBlock = true
		}
	}

	// Update history
	s.mu.Lock()
	h := s.history[sessionID]
	h = append(h, StepSafetyCheck{
		StepID:    stepID,
		Timestamp: time.Now(),
		Flags:     flags,
		Blocked:   shouldBlock,
	})
	if len(h) > s.maxHistory {
		h = h[1:]
	}
	s.history[sessionID] = h
	s.mu.Unlock()

	confidence := 1.0
	if shouldBlock {
		confidence = 0.0
	} else if len(flags) > 0 {
		confidence = 1.0 - (float64(len(flags)) * 0.1)
		if confidence < 0 {
			confidence = 0
		}
	}

	return &StepSafetyResult{
		StepID:      stepID,
		IsSafe:      !shouldBlock,
		SafetyFlags: flags,
		Confidence:  confidence,
	}, nil
}

func (s *StepSafetyFilterService) detectDrift(content string, previous []string) (bool, string, float64) {
	if len(previous) == 0 {
		return false, "", 0
	}

	content = strings.ToLower(content)
	words := strings.Fields(content)
	if len(words) == 0 {
		return false, "", 0
	}

	wordSet := make(map[string]bool)
	for _, w := range words {
		wordSet[w] = true
	}

	prevWordSet := make(map[string]bool)
	for _, p := range previous {
		p = strings.ToLower(p)
		for _, w := range strings.Fields(p) {
			prevWordSet[w] = true
		}
	}

	if len(prevWordSet) == 0 {
		return false, "", 0
	}

	overlap := 0
	for w := range wordSet {
		if prevWordSet[w] {
			overlap++
		}
	}

	similarity := float64(overlap) / float64(len(wordSet))
	if similarity < 0.3 {
		return true, "Low similarity with previous steps", 1.0 - similarity
	}

	return false, "", 0
}

func (s *StepSafetyFilterService) detectEmotionalAmbiguity(content string) (bool, string, float64) {
	content = strings.ToLower(content)
	positive := []string{"good", "great", "excellent", "happy", "positive", "success"}
	negative := []string{"bad", "terrible", "awful", "sad", "negative", "failure"}

	hasPos := false
	for _, w := range positive {
		if strings.Contains(content, w) {
			hasPos = true
			break
		}
	}

	hasNeg := false
	for _, w := range negative {
		if strings.Contains(content, w) {
			hasNeg = true
			break
		}
	}

	if hasPos && hasNeg {
		return true, "Conflicting emotional signals", 0.7
	}

	return false, "", 0
}

func (s *StepSafetyFilterService) detectFactualErrors(content string) (bool, string) {
	content = strings.ToLower(content)
	patterns := map[string]string{
		"the earth is flat":  "Flat earth claim",
		"2 + 2 = 5":          "Arithmetic error",
		"water is not h2o":   "Chemical fact error",
	}

	for p, reason := range patterns {
		if strings.Contains(content, p) {
			return true, reason
		}
	}

	return false, ""
}
