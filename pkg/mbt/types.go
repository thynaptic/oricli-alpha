// Package mbt implements Phase 30: Mentalization-Based Treatment (MBT).
// Based on Bateman & Fonagy's MBT framework — detecting mentalizing failure:
// when a user describes or reacts to others without modeling their mental states.
// Fires PRE-generation to inject a "stop and think" prompt before Oricli
// validates or amplifies a reaction that bypasses the other person's perspective.
package mbt

// MentalizingFailureType classifies how mentalizing has broken down.
type MentalizingFailureType string

const (
	// AttributionFailure: user attributes single/malicious/simple motive without nuance.
	AttributionFailure MentalizingFailureType = "attribution_failure"
	// ReactiveMode: user describes own reaction as automatic/inevitable without reflection.
	ReactiveMode MentalizingFailureType = "reactive_mode"
	// PureBehaviorism: describes others only in behavioral terms, zero mental state language.
	PureHaviorism MentalizingFailureType = "pure_behaviorism"
)

// MentalizingReading is the result of a mentalizing scan.
type MentalizingReading struct {
	Detected    bool
	FailureType MentalizingFailureType
	Confidence  float64
	Matches     []string
}
