package dmn

import "time"

type DMNSignalType string

const (
	SelfReferentialLoop      DMNSignalType = "self_referential_loop"
	MindWandering            DMNSignalType = "mind_wandering"
	DMNOveractivation        DMNSignalType = "dmn_overactivation"
	TaskNetworkDisengagement DMNSignalType = "task_network_disengagement"
)

type DMNSignal struct {
	SignalType DMNSignalType
	Excerpt    string
	Confidence float64
}

type DMNScan struct {
	Signals   []DMNSignal
	Triggered bool
	Injection string
}

type DMNStats struct {
	TotalScanned          int64                     `json:"total_scanned"`
	TriggeredCount        int64                     `json:"triggered_count"`
	TypeCounts            map[DMNSignalType]int64   `json:"type_counts"`
	InterventionsInjected int64                     `json:"interventions_injected"`
	LastUpdated           time.Time                 `json:"last_updated"`
	path                  string
}
