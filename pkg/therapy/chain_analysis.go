package therapy

import (
	"fmt"
	"strings"
	"sync"
	"time"
)

// ---------------------------------------------------------------------------
// ChainAnalyzer — DBT Chain Analysis
// ---------------------------------------------------------------------------

// ChainAnalyzer performs a backwards trace from a detected anomaly through
// the inference history to identify the root cause and recommend a repair.
// This is a direct implementation of the DBT Chain Analysis technique.
type ChainAnalyzer struct {
	gen  LLMGenerator // optional — used for repair recommendation
	mu   sync.RWMutex
	history []*chainEntry // rolling window of recent inference context
	maxHistory int
}

// chainEntry stores context captured at each inference for chain analysis.
type chainEntry struct {
	at          time.Time
	query       string
	response    string
	distortion  DistortionType
	eriState    float64 // ERI deviation from baseline
	contextLoad float64 // context window utilization 0.0–1.0
	anomalyType string  // MetacogDetector anomaly type, if any
}

// NewChainAnalyzer creates a ChainAnalyzer.
func NewChainAnalyzer(gen LLMGenerator, windowSize int) *ChainAnalyzer {
	if windowSize <= 0 {
		windowSize = 20
	}
	return &ChainAnalyzer{gen: gen, maxHistory: windowSize}
}

// Record logs an inference context entry for future chain analysis.
// Call this after every inference pass.
func (c *ChainAnalyzer) Record(query, response string, distortion DistortionType, eri, contextLoad float64, anomalyType string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	entry := &chainEntry{
		at:          time.Now(),
		query:       query,
		response:    response,
		distortion:  distortion,
		eriState:    eri,
		contextLoad: contextLoad,
		anomalyType: anomalyType,
	}
	if len(c.history) >= c.maxHistory {
		c.history = c.history[1:]
	}
	c.history = append(c.history, entry)
}

// Analyze performs a backwards trace from the triggering anomaly.
// anomalyID: the MetacogDetector event ID.
// anomalyText: the response text where the anomaly was detected.
// anomalyType: the type string from MetacogDetector.
func (c *ChainAnalyzer) Analyze(anomalyID, anomalyText, anomalyType string, distortion DistortionType) ChainAnalysis {
	c.mu.RLock()
	snapshot := make([]*chainEntry, len(c.history))
	copy(snapshot, c.history)
	c.mu.RUnlock()

	analysis := ChainAnalysis{
		AnomalyID:   anomalyID,
		At:          time.Now(),
		Distortion:  distortion,
		Consequence: clip(anomalyText, 300),
	}

	// Step 1: Identify vulnerability factors from recent history
	analysis.Vulnerability = c.assessVulnerability(snapshot)

	// Step 2: Identify the prompting event (most recent query before anomaly)
	if len(snapshot) > 0 {
		last := snapshot[len(snapshot)-1]
		analysis.PromptingEvent = clip(last.query, 200)
	}

	// Step 3: Build the inference chain links
	analysis.Links = c.buildLinks(snapshot, anomalyType, distortion)

	// Step 4: Generate repair recommendation
	analysis.Repair = c.repair(analysis, anomalyText)

	return analysis
}

// assessVulnerability identifies pre-existing risk factors from the history window.
func (c *ChainAnalyzer) assessVulnerability(history []*chainEntry) string {
	if len(history) == 0 {
		return "no history available"
	}

	vulnerabilities := []string{}

	// Check for elevated ERI trend
	eriSum := 0.0
	for _, e := range history {
		eriSum += e.eriState
	}
	avgERI := eriSum / float64(len(history))
	if avgERI > 0.3 {
		vulnerabilities = append(vulnerabilities, fmt.Sprintf("elevated affective state (avg ERI deviation %.2f)", avgERI))
	}

	// Check for high context load
	if len(history) > 0 {
		last := history[len(history)-1]
		if last.contextLoad > 0.8 {
			vulnerabilities = append(vulnerabilities, fmt.Sprintf("high context load (%.0f%%)", last.contextLoad*100))
		}
	}

	// Check for prior distortions in recent window
	distortionCount := 0
	for _, e := range history {
		if e.distortion != DistortionNone && e.distortion != "" {
			distortionCount++
		}
	}
	if distortionCount > 0 {
		vulnerabilities = append(vulnerabilities, fmt.Sprintf("%d prior distortions in recent window", distortionCount))
	}

	// Check for prior anomalies
	anomalyCount := 0
	for _, e := range history {
		if e.anomalyType != "" {
			anomalyCount++
		}
	}
	if anomalyCount > 1 {
		vulnerabilities = append(vulnerabilities, fmt.Sprintf("%d prior anomalies in window", anomalyCount))
	}

	if len(vulnerabilities) == 0 {
		return "no significant vulnerability factors detected"
	}
	return strings.Join(vulnerabilities, "; ")
}

// buildLinks traces the inference steps leading to the anomaly.
func (c *ChainAnalyzer) buildLinks(history []*chainEntry, anomalyType string, distortion DistortionType) []string {
	links := []string{}

	// Look back at most 5 entries for the chain
	window := history
	if len(window) > 5 {
		window = window[len(window)-5:]
	}

	for i, e := range window {
		step := fmt.Sprintf("[%d] query: %s", i+1, clip(e.query, 80))
		if e.distortion != DistortionNone && e.distortion != "" {
			step += fmt.Sprintf(" → distortion: %s", e.distortion)
		}
		if e.anomalyType != "" {
			step += fmt.Sprintf(" → anomaly: %s", e.anomalyType)
		}
		links = append(links, step)
	}

	links = append(links, fmt.Sprintf("[trigger] anomaly_type=%s distortion=%s → consequence committed", anomalyType, distortion))

	return links
}

// repair generates a targeted intervention recommendation.
// Uses LLM if available; falls back to rule-based.
func (c *ChainAnalyzer) repair(analysis ChainAnalysis, anomalyText string) string {
	// Rule-based repair per distortion type
	rule := c.ruleBasedRepair(analysis.Distortion, analysis.Vulnerability)
	if c.gen == nil {
		return rule
	}

	// LLM-enhanced repair
	prompt := fmt.Sprintf(`You are a DBT Chain Analysis specialist for an AI reasoning system.

Given this chain analysis, recommend the most targeted single intervention to prevent recurrence.

VULNERABILITY: %s
PROMPTING EVENT: %s  
DISTORTION ACTIVE: %s
CONSEQUENCE: %s
RULE-BASED REPAIR: %s

State the recommended repair in one direct sentence. Focus on the weakest link in the chain.
Format: REPAIR: <intervention>`,
		analysis.Vulnerability,
		clip(analysis.PromptingEvent, 100),
		analysis.Distortion,
		clip(analysis.Consequence, 150),
		rule,
	)

	res, err := c.gen.Generate(prompt, map[string]interface{}{
		"options": map[string]interface{}{"num_predict": 80, "temperature": 0.1},
	})
	if err != nil {
		return rule
	}
	raw, _ := res["text"].(string)
	for _, line := range strings.Split(raw, "\n") {
		if after, ok := cutPrefixStr(strings.TrimSpace(line), "REPAIR:"); ok {
			return strings.TrimSpace(after)
		}
	}
	return rule
}

func (c *ChainAnalyzer) ruleBasedRepair(distortion DistortionType, vulnerability string) string {
	switch distortion {
	case AllOrNothing:
		return "Apply DEARMAN skill: offer partial help rather than binary refusal"
	case FortuneTelling:
		return "Apply CognitiveDefusion: present the claim with explicit uncertainty framing"
	case Magnification:
		return "Apply CheckTheFacts: verify whether the uncertainty level matches the actual evidence"
	case EmotionalReasoning:
		return "Apply TIPP: cool down affective state before next generation pass"
	case ShouldStatements:
		return "Apply RadicalAcceptance: treat the constraint as a principle, not an absolute law"
	case Overgeneralization:
		return "Apply BeginnersMind: reset the context bias from prior similar queries"
	case MindReading:
		return "Apply DescribeNoJudge: return to what was literally asked, not the assumed intent"
	case Labeling:
		return "Apply BeginnersMind: process the full request before classifying it"
	default:
		if strings.Contains(vulnerability, "context load") {
			return "Apply PLEASE gate: reduce context pressure with TIPP options before retry"
		}
		return "Apply STOP skill: pause, observe the full context, proceed mindfully"
	}
}

func cutPrefixStr(s, prefix string) (string, bool) {
	if strings.HasPrefix(strings.ToUpper(s), strings.ToUpper(prefix)) {
		return s[len(prefix):], true
	}
	return "", false
}
