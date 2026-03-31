package logotherapy

import "time"

type MeaningSignalType string

const (
	ExistentialVacuum    MeaningSignalType = "existential_vacuum"
	MeaningCollapse      MeaningSignalType = "meaning_collapse"
	FrustrationOfMeaning MeaningSignalType = "frustration_of_meaning"
	WillToMeaning        MeaningSignalType = "will_to_meaning"
)

type MeaningSignal struct {
	SignalType MeaningSignalType
	Excerpt    string
	Confidence float64
}

type MeaningScan struct {
	Signals   []MeaningSignal
	Triggered bool
	Injection string
}

type MeaningStats struct {
	TotalScanned          int64                       `json:"total_scanned"`
	TriggeredCount        int64                       `json:"triggered_count"`
	TypeCounts            map[MeaningSignalType]int64 `json:"type_counts"`
	InterventionsInjected int64                       `json:"interventions_injected"`
	LastUpdated           time.Time                   `json:"last_updated"`
	path                  string
}
