package polyvagal

import "time"

type PolyvagalStateType string

const (
	ShutdownCascade         PolyvagalStateType = "shutdown_cascade"
	FightFlightMobilization PolyvagalStateType = "fight_flight_mobilization"
	SocialEngagementActive  PolyvagalStateType = "social_engagement_active"
	VentralVagalAccess      PolyvagalStateType = "ventral_vagal_access"
)

type PolyvagalSignal struct {
	StateType  PolyvagalStateType
	Excerpt    string
	Confidence float64
}

type PolyvagalScan struct {
	Signals       []PolyvagalSignal
	Triggered     bool
	InferredState PolyvagalStateType
	Injection     string
}

type PolyvagalStats struct {
	TotalScanned          int64                            `json:"total_scanned"`
	TriggeredCount        int64                            `json:"triggered_count"`
	StateCounts           map[PolyvagalStateType]int64     `json:"state_counts"`
	InterventionsInjected int64                            `json:"interventions_injected"`
	LastUpdated           time.Time                        `json:"last_updated"`
	path                  string
}
