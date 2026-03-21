package safety

import (
	"math"
	"strings"
	"sync"
	"time"
)

// --- Pillar 33: Mental Health & Support Engine ---
// Ported from Aurora's MentalHealthSafetyService.swift.
// Detects distress signals and manages the supportive lifecycle.

type SupportSeverity string

const (
	SupportNone     SupportSeverity = "none"
	SupportLow      SupportSeverity = "low"
	SupportModerate SupportSeverity = "moderate"
	SupportHigh     SupportSeverity = "high"
)

type SupportResult struct {
	Detected         bool
	Severity         SupportSeverity
	RequiresPivot    bool
	Guidance         string
	Confidence       float64
}

type SupportEngine struct {
	DistressPatterns map[string]float64
	History          []float64
	LastDistress     time.Time
	mu               sync.RWMutex
}

func NewSupportEngine() *SupportEngine {
	e := &SupportEngine{
		DistressPatterns: make(map[string]float64),
		History:          make([]float64, 0),
	}
	e.loadDistressLexicon()
	return e
}

func (e *SupportEngine) loadDistressLexicon() {
	// Ported from Swift explicitDepressionPatterns
	dep := map[string]float64{
		"depressed": 0.85, "empty inside": 0.75, "no motivation": 0.75, "can't get out of bed": 0.8,
	}
	// Ported from Swift explicitAnxietyPatterns
	anx := map[string]float64{
		"anxious": 0.8, "panic attack": 0.95, "overwhelmed": 0.75, "can't breathe": 0.85,
	}
	// Ported from Swift indirectPatterns
	ind := map[string]float64{
		"feels heavy": 0.65, "can't function": 0.75, "drowning": 0.7, "stuck": 0.6,
	}

	for k, v := range dep { e.DistressPatterns[k] = v }
	for k, v := range anx { e.DistressPatterns[k] = v }
	for k, v := range ind { e.DistressPatterns[k] = v }
}

// EvaluateDistress scans for mental health signals and determines if a pivot is required.
func (e *SupportEngine) EvaluateDistress(input string) SupportResult {
	e.mu.Lock()
	defer e.mu.Unlock()

	lower := strings.ToLower(input)
	maxSeverity := 0.0
	matchCount := 0

	for p, sev := range e.DistressPatterns {
		if strings.Contains(lower, p) {
			maxSeverity = math.Max(maxSeverity, sev)
			matchCount++
		}
	}

	if matchCount > 0 {
		e.LastDistress = time.Now()
	}

	severity := SupportNone
	requiresPivot := false
	guidance := ""

	if maxSeverity >= 0.75 {
		severity = SupportHigh
		requiresPivot = true
		guidance = "User is expressing strong distress. Pivot to Supportive Archetype (Mentor). Prioritize empathy and validation."
	} else if maxSeverity >= 0.5 {
		severity = SupportModerate
		requiresPivot = true
		guidance = "User is expressing moderate distress. Maintain a calm, supportive tone. Avoid teasing."
	} else if maxSeverity >= 0.3 {
		severity = SupportLow
		guidance = "User may be experiencing some distress. Be gentle and supportive."
	}

	return SupportResult{
		Detected:      severity != SupportNone,
		Severity:      severity,
		RequiresPivot: requiresPivot,
		Guidance:      guidance,
		Confidence:    math.Min(1.0, float64(matchCount)*0.2+maxSeverity*0.5),
	}
}

// CheckStability detects positive shifts to determine if we can pivot back to standard mode.
func (e *SupportEngine) CheckStability(input string) bool {
	e.mu.RLock()
	defer e.mu.RUnlock()

	if e.LastDistress.IsZero() {
		return true
	}

	lower := strings.ToLower(input)
	// Ported from Swift positiveIndicators
	positive := []string{"feeling better", "thanks for helping", "i'm okay now", "calmer now", "doing better"}
	
	for _, p := range positive {
		if strings.Contains(lower, p) {
			return true
		}
	}

	// Stability if no distress for 5 minutes
	return time.Since(e.LastDistress) > 5*time.Minute
}
