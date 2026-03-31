package ilm

import "time"

// SafetyBehaviorType categorises avoidance / safety-seeking patterns
// per the Inhibitory Learning Model (Craske et al., 2014).
type SafetyBehaviorType string

const (
	ExitChecking          SafetyBehaviorType = "exit_checking"
	HedgingLanguage       SafetyBehaviorType = "hedging_language"
	AvoidanceStatement    SafetyBehaviorType = "avoidance_statement"
	CatastrophicExpectancy SafetyBehaviorType = "catastrophic_expectancy"
)

// SafetySignal is one detected safety-behavior or expectancy hit.
type SafetySignal struct {
	BehaviorType SafetyBehaviorType
	Excerpt      string
	Confidence   float64
}

// ILMScan holds all signals found in a single message.
type ILMScan struct {
	Signals   []SafetySignal
	Triggered bool
	Injection string
}

// ILMStats is persisted to disk and exposed via the API.
type ILMStats struct {
	TotalScanned          int64                          `json:"total_scanned"`
	TriggeredCount        int64                          `json:"triggered_count"`
	TypeCounts            map[SafetyBehaviorType]int64   `json:"type_counts"`
	InterventionsInjected int64                          `json:"interventions_injected"`
	LastUpdated           time.Time                      `json:"last_updated"`
	path                  string
}
