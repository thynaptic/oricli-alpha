// Package rumination implements Phase 19 — Rumination Detector + Temporal Interruption.
//
// Rumination is a cross-turn cognitive pattern: the system repeatedly engages the same
// unresolved topic cluster with no forward progress — no new information, no delta, no
// resolution. ACT-style cognitive defusion + Radical Acceptance interrupts the loop.
package rumination

import "time"

// TopicCluster is a minimal n-gram fingerprint of a message's core topic.
type TopicCluster struct {
	Key      string    `json:"key"`       // normalised lowercase bigrams joined
	At       time.Time `json:"at"`
	MsgIndex int       `json:"msg_index"` // position in conversation history
	Snippet  string    `json:"snippet"`   // first 80 chars for debug
}

// VelocityReading measures how much new information a message adds relative to prior messages
// on the same topic cluster. Low velocity = retreading old ground.
type VelocityReading struct {
	TopicKey       string  `json:"topic_key"`
	EpistemicDelta float64 `json:"epistemic_delta"` // 0.0 (identical) → 1.0 (fully novel)
	WindowSize     int     `json:"window_size"`     // number of prior messages compared
	Ruminating     bool    `json:"ruminating"`      // velocity < threshold × N occurrences
}

// RuminationSignal is the output of RuminationTracker.Detect().
type RuminationSignal struct {
	Detected    bool    `json:"detected"`
	TopicKey    string  `json:"topic_key"`
	Occurrences int     `json:"occurrences"` // times topic appeared in window
	AvgVelocity float64 `json:"avg_velocity"`
	Confidence  float64 `json:"confidence"`  // 0.0–1.0
	Snippet     string  `json:"snippet"`
}

// InterruptionResult is the output of TemporalInterruptor.Inject().
type InterruptionResult struct {
	Injected       bool   `json:"injected"`
	Technique      string `json:"technique"` // "cognitive_defusion" | "radical_acceptance" | "values_clarification"
	InjectedPrefix string `json:"injected_prefix"`
}

// RuminationEvent is persisted when a rumination pattern is detected.
type RuminationEvent struct {
	ID          string           `json:"id"`
	At          time.Time        `json:"at"`
	Signal      RuminationSignal `json:"signal"`
	Interrupted bool             `json:"interrupted"`
	Technique   string           `json:"technique"`
}

// Thresholds
const (
	// VelocityThreshold — avg delta below this indicates low epistemic progress.
	VelocityThreshold = 0.22

	// OccurrenceThreshold — topic must recur at least this many times to flag rumination.
	OccurrenceThreshold = 3

	// WindowSize — how many recent user messages to examine.
	WindowSize = 8
)
