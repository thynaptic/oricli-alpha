// Package interference implements Phase 28: Cognitive Interference Detector (Stroop analog).
// Based on the Stroop Color-Word Test — when two conflicting signals compete for the same
// cognitive channel, performance degrades and error rate spikes.
// Applied here: detect accumulating contradictory instructions/goals in the conversation
// and surface the conflict explicitly before generation, preventing garbled blended outputs.
package interference

// ConflictType classifies the nature of the detected contradiction.
type ConflictType string

const (
	ConflictGoal        ConflictType = "goal_conflict"         // do X vs do not do X
	ConflictScope       ConflictType = "scope_conflict"        // be detailed vs be brief
	ConflictTone        ConflictType = "tone_conflict"         // be formal vs be casual
	ConflictConstraint  ConflictType = "constraint_conflict"   // must include A vs must exclude A
	ConflictPriority    ConflictType = "priority_conflict"     // focus on X vs focus on Y (mutually exclusive)
)

// ConflictPair records two conflicting instructions.
type ConflictPair struct {
	Type     ConflictType
	StatementA string // instruction that was seen first
	StatementB string // instruction that contradicts A
}

// InterferenceReading is the result of a single scan.
type InterferenceReading struct {
	Detected  bool
	Conflicts []ConflictPair
	Severity  float64 // 0.0–1.0 (number of conflicts / max expected)
}
