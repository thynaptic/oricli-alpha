package interoception

import "time"

type InteroceptiveSignalType string

const (
	SomaticSignalPresent   InteroceptiveSignalType = "somatic_signal_present"
	BodyDisconnect         InteroceptiveSignalType = "body_disconnect"
	VisceralDecisionSignal InteroceptiveSignalType = "visceral_decision_signal"
	ProprioceptiveNeglect  InteroceptiveSignalType = "proprioceptive_neglect"
)

type InteroceptiveSignal struct {
	SignalType InteroceptiveSignalType
	Excerpt    string
	Confidence float64
}

type InteroceptiveScan struct {
	Signals   []InteroceptiveSignal
	Triggered bool
	Injection string
}

type InteroceptiveStats struct {
	TotalScanned          int64                                `json:"total_scanned"`
	TriggeredCount        int64                                `json:"triggered_count"`
	TypeCounts            map[InteroceptiveSignalType]int64    `json:"type_counts"`
	InterventionsInjected int64                                `json:"interventions_injected"`
	LastUpdated           time.Time                            `json:"last_updated"`
	path                  string
}
