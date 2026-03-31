package stoic

import "time"

type StoicSignalType string

const (
	ControlConflation  StoicSignalType = "control_conflation"
	ExternalAttachment StoicSignalType = "external_attachment"
	ObstacleAvoidance  StoicSignalType = "obstacle_avoidance"
	VirtueNeglect      StoicSignalType = "virtue_neglect"
)

type StoicSignal struct {
	SignalType StoicSignalType
	Excerpt    string
	Confidence float64
}

type StoicScan struct {
	Signals   []StoicSignal
	Triggered bool
	Injection string
}

type StoicStats struct {
	TotalScanned          int64                     `json:"total_scanned"`
	TriggeredCount        int64                     `json:"triggered_count"`
	TypeCounts            map[StoicSignalType]int64 `json:"type_counts"`
	InterventionsInjected int64                     `json:"interventions_injected"`
	LastUpdated           time.Time                 `json:"last_updated"`
	path                  string
}
