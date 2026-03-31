package up

import "time"

// ARCComponent represents one part of the Antecedent-Response-Consequence cycle
// as defined in the Unified Protocol (Barlow et al.).
type ARCComponent string

const (
	AntecedentDetected  ARCComponent = "antecedent"
	ResponseDetected    ARCComponent = "response"
	ConsequenceDetected ARCComponent = "consequence"
)

// ARCSignal is one detected ARC cycle component.
type ARCSignal struct {
	Component  ARCComponent
	Excerpt    string
	Confidence float64
}

// ARCScan holds all ARC components found in a single message.
type ARCScan struct {
	Signals   []ARCSignal
	HasCycle  bool   // true when at least antecedent + response detected
	Injection string
}

// UPStats is persisted to disk and exposed via the API.
type UPStats struct {
	TotalScanned          int64                      `json:"total_scanned"`
	CyclesDetected        int64                      `json:"cycles_detected"`
	ComponentCounts       map[ARCComponent]int64     `json:"component_counts"`
	InterventionsInjected int64                      `json:"interventions_injected"`
	LastUpdated           time.Time                  `json:"last_updated"`
	path                  string
}
