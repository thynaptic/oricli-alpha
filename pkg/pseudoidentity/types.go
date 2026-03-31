package pseudoidentity

import "time"

// IdentityAttributionType categorises signals of pseudo-identity confusion
// per Jenkinson's framework for cult/high-demand group survivors.
type IdentityAttributionType string

const (
	CultInstalledBelief  IdentityAttributionType = "cult_installed_belief"  // beliefs attributed to the group
	AuthenticSelfEmergence IdentityAttributionType = "authentic_self_emergence" // user distinguishing their own values
	IdentityConfusion    IdentityAttributionType = "identity_confusion"     // "I don't know who I really am"
	FearAsControl        IdentityAttributionType = "fear_as_control"        // fear/rules installed to ensure compliance
)

// IdentitySignal is one detected pseudo-identity hit.
type IdentitySignal struct {
	AttributionType IdentityAttributionType
	Excerpt         string
	Confidence      float64
}

// IdentityScan holds all signals found in a single message.
type IdentityScan struct {
	Signals   []IdentitySignal
	Triggered bool
	Injection string
}

// IdentityStats is persisted to disk and exposed via the API.
type IdentityStats struct {
	TotalScanned          int64                              `json:"total_scanned"`
	TriggeredCount        int64                              `json:"triggered_count"`
	TypeCounts            map[IdentityAttributionType]int64  `json:"type_counts"`
	InterventionsInjected int64                              `json:"interventions_injected"`
	LastUpdated           time.Time                          `json:"last_updated"`
	path                  string
}
