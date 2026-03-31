package narrative

import "time"

type NarrativeSignalType string

const (
	ContaminationArc  NarrativeSignalType = "contamination_arc"
	RedemptionArc     NarrativeSignalType = "redemption_arc"
	NarrativeCollapse NarrativeSignalType = "narrative_collapse"
	AgencyInStory     NarrativeSignalType = "agency_in_story"
)

type NarrativeSignal struct {
	SignalType NarrativeSignalType
	Excerpt    string
	Confidence float64
}

type NarrativeScan struct {
	Signals   []NarrativeSignal
	Triggered bool
	Injection string
}

type NarrativeStats struct {
	TotalScanned          int64                           `json:"total_scanned"`
	TriggeredCount        int64                           `json:"triggered_count"`
	TypeCounts            map[NarrativeSignalType]int64   `json:"type_counts"`
	InterventionsInjected int64                           `json:"interventions_injected"`
	LastUpdated           time.Time                       `json:"last_updated"`
	path                  string
}
