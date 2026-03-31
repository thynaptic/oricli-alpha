// Package mindset implements Phase 20 — Growth Mindset Tracker (Dweck).
//
// Tracks a per-topic-class mindset vector: does the system approach novel problems
// as inherently learnable (growth) or as fixed-ceiling (fixed)? Bridges to the
// MasteryLog (Phase 16) for evidence. Fixed-mindset language gets reframed with
// "not yet" injection before the helplessness detector even fires.
package mindset

import "time"

// MindsetTier classifies a topic class mindset.
type MindsetTier string

const (
	MindsetGrowth  MindsetTier = "growth"
	MindsetNeutral MindsetTier = "neutral"
	MindsetFixed   MindsetTier = "fixed"
)

// MindsetVector is the accumulated mindset score for a topic class.
type MindsetVector struct {
	TopicClass  string      `json:"topic_class"`
	GrowthScore float64     `json:"growth_score"` // [0–1]; 0=fixed, 1=growth
	SampleCount int         `json:"sample_count"`
	Tier        MindsetTier `json:"tier"`
	LastUpdated time.Time   `json:"last_updated"`
}

// MindsetSignal is the result of scanning a draft response for fixed-mindset language.
type MindsetSignal struct {
	Detected      bool        `json:"detected"`         // true if fixed-mindset language found
	FixedPhrases  []string    `json:"fixed_phrases"`    // matched phrases
	TopicClass    string      `json:"topic_class"`
	CurrentTier   MindsetTier `json:"current_tier"`
	GrowthScore   float64     `json:"growth_score"`
	Confidence    float64     `json:"confidence"`
}

// ReframeResult is the output of GrowthReframer.Reframe().
type ReframeResult struct {
	Reframed      bool   `json:"reframed"`
	Original      string `json:"original"`       // matched fixed phrase
	Replacement   string `json:"replacement"`    // "not yet" reframe
	Technique     string `json:"technique"`      // "not_yet" | "mastery_bridge" | "incremental_frame"
}

// MindsetEvent is persisted when a fixed-mindset signal is detected + reframed.
type MindsetEvent struct {
	ID         string        `json:"id"`
	At         time.Time     `json:"at"`
	Signal     MindsetSignal `json:"signal"`
	Reframe    ReframeResult `json:"reframe"`
}

// Thresholds
const (
	FixedMindsetThreshold  = 0.35 // growth score below this → fixed tier
	GrowthMindsetThreshold = 0.65 // growth score above this → growth tier
)
