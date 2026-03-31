package mbct

import "time"

// SpiralWarningType categorises MBCT early-warning depressive spiral signals.
// Segal, Williams & Teasdale (2002): decentering from thoughts as mental events.
type SpiralWarningType string

const (
	ThoughtFusion       SpiralWarningType = "thought_fusion"        // "I AM my thoughts/feelings" (over-identification)
	EarlyRumination     SpiralWarningType = "early_rumination"      // catching the spiral at the first loop
	SelfCriticalCascade SpiralWarningType = "self_critical_cascade" // small error → global self-attack
	MoodAsFactError     SpiralWarningType = "mood_as_fact"          // treating emotional state as objective reality
)

// MBCTSignal is one detected spiral-warning hit.
type MBCTSignal struct {
	WarningType SpiralWarningType
	Excerpt     string
	Confidence  float64
}

// MBCTScan holds all signals found in a single message.
type MBCTScan struct {
	Signals   []MBCTSignal
	Triggered bool
	Injection string
}

// MBCTStats is persisted to disk and exposed via the API.
type MBCTStats struct {
	TotalScanned          int64                         `json:"total_scanned"`
	TriggeredCount        int64                         `json:"triggered_count"`
	TypeCounts            map[SpiralWarningType]int64   `json:"type_counts"`
	InterventionsInjected int64                         `json:"interventions_injected"`
	LastUpdated           time.Time                     `json:"last_updated"`
	path                  string
}
