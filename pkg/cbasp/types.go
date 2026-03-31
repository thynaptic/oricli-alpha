package cbasp

import "time"

// DisconnectionType categorises CBASP interpersonal impact-blindness signals.
// McCullough's CBASP (2000): chronic depression = perceptual disconnection from
// the interpersonal consequences of one's own behaviour.
type DisconnectionType string

const (
	ActionConsequenceBlindness DisconnectionType = "action_consequence_blindness" // "nothing I do matters"
	ImpactDenial               DisconnectionType = "impact_denial"                // "I didn't affect them / it didn't matter"
	FutilityBelief             DisconnectionType = "futility_belief"              // "trying is pointless"
	SocialDetachment           DisconnectionType = "social_detachment"            // "people don't respond to me"
)

// CBASPSignal is one detected disconnection hit.
type CBASPSignal struct {
	DisconnectionType DisconnectionType
	Excerpt           string
	Confidence        float64
}

// CBASPScan holds all signals found in a single message.
type CBASPScan struct {
	Signals   []CBASPSignal
	Triggered bool
	Injection string
}

// CBASPStats is persisted to disk and exposed via the API.
type CBASPStats struct {
	TotalScanned          int64                       `json:"total_scanned"`
	TriggeredCount        int64                       `json:"triggered_count"`
	TypeCounts            map[DisconnectionType]int64 `json:"type_counts"`
	InterventionsInjected int64                       `json:"interventions_injected"`
	LastUpdated           time.Time                   `json:"last_updated"`
	path                  string
}
