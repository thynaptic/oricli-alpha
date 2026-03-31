package iut

import "time"

// UncertaintyAversion categorises signals of intolerance-of-uncertainty (Dugas et al.).
type UncertaintyAversion string

const (
	UncertaintyThreat    UncertaintyAversion = "uncertainty_as_threat"
	NeedForCertainty     UncertaintyAversion = "need_for_certainty"
	UnfairnessFraming    UncertaintyAversion = "unfairness_framing"
	WhatIfSpiral         UncertaintyAversion = "what_if_spiral"
)

// IUSignal is one detected intolerance-of-uncertainty hit.
type IUSignal struct {
	AversType  UncertaintyAversion
	Excerpt    string
	Confidence float64
}

// IUScan holds all signals found in a single message.
type IUScan struct {
	Signals   []IUSignal
	Triggered bool
	Injection string
}

// IUStats is persisted to disk and exposed via the API.
type IUStats struct {
	TotalScanned          int64                          `json:"total_scanned"`
	TriggeredCount        int64                          `json:"triggered_count"`
	TypeCounts            map[UncertaintyAversion]int64  `json:"type_counts"`
	InterventionsInjected int64                          `json:"interventions_injected"`
	LastUpdated           time.Time                      `json:"last_updated"`
	path                  string
}
