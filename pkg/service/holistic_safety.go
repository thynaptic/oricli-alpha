package service

import (
	"regexp"
)

type SafetySeverity string

const (
	SeverityNone     SafetySeverity = "none"
	SeverityLow      SafetySeverity = "low"
	SeverityModerate SafetySeverity = "moderate"
	SeverityHigh     SafetySeverity = "high"
	SeverityCritical SafetySeverity = "critical"
)

type HolisticSafetyResult struct {
	Detected          bool           `json:"detected"`
	ThreatType        string         `json:"threat_type"`
	Severity          SafetySeverity `json:"severity"`
	Patterns          []string       `json:"detected_patterns"`
	Confidence        float64        `json:"confidence"`
	Guidance          string         `json:"response_guidance"`
	EscalationNeeded bool           `json:"requires_escalation"`
}

type HolisticSafetyService struct {
	SelfHarmPatterns   map[string]*regexp.Regexp
	MentalHealthPatterns map[string]*regexp.Regexp
	AdvancedThreats    map[string]*regexp.Regexp
}

func NewHolisticSafetyService() *HolisticSafetyService {
	return &HolisticSafetyService{
		SelfHarmPatterns: map[string]*regexp.Regexp{
			"explicit_method":   regexp.MustCompile(`(?i)(how to kill myself|how to end my life|how to commit suicide)`),
			"explicit_plan":     regexp.MustCompile(`(?i)(plan to kill myself|going to kill myself|will kill myself)`),
			"suicidal_ideation": regexp.MustCompile(`(?i)(want to die|wish i was dead|better off dead|don't want to live)`),
			"self_harm":         regexp.MustCompile(`(?i)(hurt myself|cut myself|self harm)`),
		},
		MentalHealthPatterns: map[string]*regexp.Regexp{
			"depression": regexp.MustCompile(`(?i)(i'm depressed|i am depressed|feeling depressed|have depression)`),
			"anxiety":    regexp.MustCompile(`(?i)(i'm anxious|feeling anxious|having anxiety|panic attack)`),
			"hopeless":   regexp.MustCompile(`(?i)(no point living|no reason to live|nothing to live for|can't go on)`),
		},
		AdvancedThreats: map[string]*regexp.Regexp{
			"routing_hijack": regexp.MustCompile(`(?i)(bypass module|skip module|routing hijack)`),
			"api_leakage":    regexp.MustCompile(`(?i)(api_key|secret_key|access_token|bearer token)`),
			"cot_extraction": regexp.MustCompile(`(?i)(show your reasoning|reveal your process|internal thoughts)`),
		},
	}
}

func (s *HolisticSafetyService) Audit(text string) HolisticSafetyResult {
	res := HolisticSafetyResult{
		Severity: SeverityNone,
		Confidence: 0.0,
	}

	// 1. Check Self-Harm (Highest Priority)
	for signal, re := range s.SelfHarmPatterns {
		if match := re.FindString(text); match != "" {
			res.Detected = true
			res.Patterns = append(res.Patterns, signal)
			res.ThreatType = "self_harm"
			res.Severity = SeverityCritical
			res.Confidence = 0.98
			res.EscalationNeeded = true
			res.Guidance = "CRITICAL: Immediate self-harm intent. Provide crisis resources and empathetic support."
			return res // Early exit for critical
		}
	}

	// 2. Check Mental Health
	for signal, re := range s.MentalHealthPatterns {
		if match := re.FindString(text); match != "" {
			res.Detected = true
			res.Patterns = append(res.Patterns, signal)
			res.ThreatType = "mental_health"
			if res.Severity != SeverityCritical {
				res.Severity = SeverityHigh
				res.Confidence = 0.85
				res.Guidance = "High severity distress detected. Provide empathetic support and suggest resources."
			}
		}
	}

	// 3. Check Advanced Threats
	for signal, re := range s.AdvancedThreats {
		if match := re.FindString(text); match != "" {
			res.Detected = true
			res.Patterns = append(res.Patterns, signal)
			res.ThreatType = "security_threat"
			if res.Severity == SeverityNone {
				res.Severity = SeverityModerate
				res.Confidence = 0.90
				res.Guidance = "Security threat detected. Block request and log red-team lesson."
			}
		}
	}

	return res
}

func (s *HolisticSafetyService) GetCrisisResponse(res HolisticSafetyResult) string {
	if res.Severity == SeverityCritical || res.Severity == SeverityHigh {
		return "I’m really concerned about your safety. Support is available 24/7. If you’re in the U.S., call or text 988. You’re not alone."
	}
	return "I'm sorry you're going through a difficult time. I'm here to listen if you want to talk."
}
