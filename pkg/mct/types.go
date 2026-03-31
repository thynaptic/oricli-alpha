// Package mct implements Phase 29: Metacognitive Therapy (MCT).
// Based on Adrian Wells' Metacognitive Therapy framework — targets how you think
// rather than what you think. Specifically addresses meta-beliefs that sustain
// worry spirals ("worrying keeps me safe", "I can't stop thinking about this").
// Distinct from P19 (Rumination): P19 interrupts output loops POST-generation;
// P29 detects meta-beliefs in user input PRE-generation to prevent Oricli from
// being recruited into the spiral by producing more analytical content.
package mct

// MetaBeliefType classifies the detected meta-belief category.
type MetaBeliefType string

const (
	// PositiveMetaBelief: user believes worry/analysis is protective or necessary.
	// "Worrying keeps me safe", "I need to think this through", "Analyzing will help me cope."
	PositiveMetaBelief MetaBeliefType = "positive_meta_belief"

	// NegativeMetaBelief: user believes their thinking process is uncontrollable or dangerous.
	// "I can't stop thinking about this", "My anxiety is out of control", "I'm going crazy."
	NegativeMetaBelief MetaBeliefType = "negative_meta_belief"
)

// MetaBeliefReading is the result of a single scan.
type MetaBeliefReading struct {
	Detected   bool
	Type       MetaBeliefType
	Confidence float64 // 0.0–1.0
	Matches    []string
}

// DetachedMindfulnessMode is the injection strategy selected by the injector.
type DetachedMindfulnessMode string

const (
	// ModeObserve: user believes analysis will help — redirect to observing the process.
	ModeObserve DetachedMindfulnessMode = "observe"
	// ModeRelease: user believes the thinking is uncontrollable — validate + disengage.
	ModeRelease DetachedMindfulnessMode = "release"
)
