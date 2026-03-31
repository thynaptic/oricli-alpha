package ipsrt

import "time"

// RhythmDisruptionType categorises circadian / social-rhythm disruption signals
// as identified by the Social Rhythm Metric (Frank et al., IPSRT).
type RhythmDisruptionType string

const (
	SleepDisruption  RhythmDisruptionType = "sleep_disruption"
	RoutineBreak     RhythmDisruptionType = "routine_break"
	MealDisruption   RhythmDisruptionType = "meal_disruption"
	SocialIsolation  RhythmDisruptionType = "social_isolation"
	ScheduleChaos    RhythmDisruptionType = "schedule_chaos"
)

// RhythmSignal is one detected disruption hit in the input.
type RhythmSignal struct {
	DisruptionType RhythmDisruptionType
	Excerpt        string
	Confidence     float64
}

// RhythmScan holds all signals found in a single message.
type RhythmScan struct {
	Signals    []RhythmSignal
	Disrupted  bool
	Injection  string
}

// RhythmStats is persisted to disk and exposed via the API.
type RhythmStats struct {
	TotalScanned         int64                            `json:"total_scanned"`
	DisruptionsDetected  int64                            `json:"disruptions_detected"`
	TypeCounts           map[RhythmDisruptionType]int64   `json:"type_counts"`
	InterventionsInjected int64                           `json:"interventions_injected"`
	LastUpdated          time.Time                        `json:"last_updated"`
	path                 string
}
