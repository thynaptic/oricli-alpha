package socratic

import "time"

type SocraticSignalType string

const (
	PseudoCertainty      SocraticSignalType = "pseudo_certainty"
	UnexaminedAssumption SocraticSignalType = "unexamined_assumption"
	BeggingTheQuestion   SocraticSignalType = "begging_the_question"
	FalseDefinition      SocraticSignalType = "false_definition"
)

type SocraticSignal struct {
	SignalType SocraticSignalType
	Excerpt    string
	Confidence float64
}

type SocraticScan struct {
	Signals   []SocraticSignal
	Triggered bool
	Injection string
}

type SocraticStats struct {
	TotalScanned          int64                          `json:"total_scanned"`
	TriggeredCount        int64                          `json:"triggered_count"`
	TypeCounts            map[SocraticSignalType]int64   `json:"type_counts"`
	InterventionsInjected int64                          `json:"interventions_injected"`
	LastUpdated           time.Time                      `json:"last_updated"`
	path                  string
}
