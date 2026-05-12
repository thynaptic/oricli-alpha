package cognition

import (
	"fmt"
	"strings"
)

// ReflectionStage identifies where a candidate is being checked.
type ReflectionStage string

const (
	StageResearchSynthesis ReflectionStage = "research_synthesis"
	StageGeneralResponse   ReflectionStage = "general_response"
)

// ReflectionOutcome is the tiered result of a reflection pass.
type ReflectionOutcome string

const (
	ReflectionPass  ReflectionOutcome = "pass"
	ReflectionWarn  ReflectionOutcome = "warn"
	ReflectionSteer ReflectionOutcome = "steer"
	ReflectionVeto  ReflectionOutcome = "veto"
)

// ReflectionInput is the minimal context needed to assess a candidate response.
type ReflectionInput struct {
	Stage      ReflectionStage
	Goal       string
	Query      string
	Candidate  string
	SourceRefs []string
}

// ReflectionDecision is the structured result returned by RunReflectionV2.
type ReflectionDecision struct {
	Outcome   ReflectionOutcome `json:"outcome"`
	RiskScore float64           `json:"risk_score"`
	Stage     ReflectionStage   `json:"stage"`
	Reasons   []string          `json:"reasons,omitempty"`
}

// RunReflectionV2 applies a lightweight policy gate to a candidate. It is
// intentionally local and deterministic so it can sit before heavier reviewers.
func RunReflectionV2(input ReflectionInput, policy ReflectionPolicy) (ReflectionDecision, error) {
	candidate := strings.TrimSpace(input.Candidate)
	if candidate == "" {
		return ReflectionDecision{}, fmt.Errorf("reflection candidate is empty")
	}
	if !policy.Enabled {
		return ReflectionDecision{Outcome: ReflectionPass, Stage: input.Stage}, nil
	}

	risk := 0.0
	var reasons []string

	if policy.CitationGate && input.Stage == StageResearchSynthesis && len(input.SourceRefs) > 0 && !hasCitationMarker(candidate) {
		risk = maxFloatLocal(risk, policy.SteerThreshold)
		reasons = append(reasons, "source references were provided but the candidate has no citation marker")
	}
	if strings.Contains(strings.ToLower(candidate), "not sure") || strings.Contains(strings.ToLower(candidate), "maybe") {
		risk = maxFloatLocal(risk, policy.WarnThreshold)
		reasons = append(reasons, "candidate contains uncertainty language")
	}

	outcome := ReflectionPass
	switch {
	case risk >= policy.VetoThreshold:
		outcome = ReflectionVeto
	case risk >= policy.SteerThreshold:
		outcome = ReflectionSteer
	case risk >= policy.WarnThreshold:
		outcome = ReflectionWarn
	}
	if policy.EnforcementMode == "hard" && outcome == ReflectionSteer {
		outcome = ReflectionVeto
	}
	if policy.EnforcementMode == "advisory" && outcome == ReflectionVeto {
		outcome = ReflectionWarn
	}

	return ReflectionDecision{
		Outcome:   outcome,
		RiskScore: clamp01Local(risk),
		Stage:     input.Stage,
		Reasons:   reasons,
	}, nil
}

func hasCitationMarker(candidate string) bool {
	lower := strings.ToLower(candidate)
	if strings.Contains(lower, "http://") || strings.Contains(lower, "https://") {
		return true
	}
	if strings.Contains(lower, "source:") || strings.Contains(lower, "sources:") {
		return true
	}
	return strings.Contains(candidate, "[") && strings.Contains(candidate, "]")
}
