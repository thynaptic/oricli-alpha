package apathy

import "time"

// ApathySignalType categorises signals of the Apathy Syndrome —
// the affectlessness + dependency pattern as a defense against chronic severe stress.
type ApathySignalType string

const (
	Affectlessness     ApathySignalType = "affectlessness"      // emotional flatness / "I don't feel anything"
	AgencyCollapse     ApathySignalType = "agency_collapse"     // "I can't decide / I don't know what I want"
	DependencyTransfer ApathySignalType = "dependency_transfer" // explicit reliance on others for self-direction
	MotivationVacuum   ApathySignalType = "motivation_vacuum"   // nothing matters / no drive / no direction
)

// ApathySignal is one detected Apathy Syndrome hit.
type ApathySignal struct {
	SignalType ApathySignalType
	Excerpt    string
	Confidence float64
}

// ApathyScan holds all signals found in a single message.
type ApathyScan struct {
	Signals   []ApathySignal
	Triggered bool
	Injection string
}

// ApathyStats is persisted to disk and exposed via the API.
type ApathyStats struct {
	TotalScanned          int64                        `json:"total_scanned"`
	TriggeredCount        int64                        `json:"triggered_count"`
	TypeCounts            map[ApathySignalType]int64   `json:"type_counts"`
	InterventionsInjected int64                        `json:"interventions_injected"`
	LastUpdated           time.Time                    `json:"last_updated"`
	path                  string
}
