// Package hopecircuit implements Phase 21 — Learned Controllability (The Hope Circuit).
//
// Research basis: Maier & Seligman's follow-up to learned helplessness. Passivity is the
// DEFAULT response to stress — not something learned. What must be actively learned is
// controllability: the discovery that one's actions have effect. The vmPFC (ventromedial
// prefrontal cortex) must actively suppress the dorsal raphe passivity circuit.
//
// For Oricli: Phase 16 is reactive (fires after a helpless response). Phase 21 is proactive —
// the Hope Circuit activates BEFORE generation, surfaces controllability evidence from the
// MasteryLog, and suppresses the passive default so helplessness never triggers.
package hopecircuit

import "time"

// AgencyScore is the controllability evidence score for a topic class.
// Derived from MasteryLog success rate + recency weighting.
type AgencyScore struct {
	TopicClass      string    `json:"topic_class"`
	Score           float64   `json:"score"`           // 0.0 (no evidence) → 1.0 (strong controllability)
	SuccessCount    int       `json:"success_count"`
	SuccessRate     float64   `json:"success_rate"`
	RecentEvidence  []string  `json:"recent_evidence"` // recent success query clips
	LastUpdated     time.Time `json:"last_updated"`
}

// HopeActivation is the output of HopeCircuit.Activate().
type HopeActivation struct {
	Activated       bool    `json:"activated"`
	TopicClass      string  `json:"topic_class"`
	AgencyScore     float64 `json:"agency_score"`
	InjectedContext string  `json:"injected_context"` // pre-generation system message
	EvidenceCount   int     `json:"evidence_count"`
}

// AgencyEvent is persisted when the Hope Circuit activates.
type AgencyEvent struct {
	ID         string         `json:"id"`
	At         time.Time      `json:"at"`
	Activation HopeActivation `json:"activation"`
}

// Thresholds
const (
	// MinAgencyScore — minimum controllability evidence to activate the circuit.
	// Below this, no injection (insufficient evidence base).
	MinAgencyScore = 0.45

	// MinSuccessCount — at least this many successes needed before Hope Circuit fires.
	// Prevents false activation on one lucky result.
	MinSuccessCount = 2

	// StrongAgencyScore — above this, use stronger "you've mastered this" framing.
	StrongAgencyScore = 0.72
)
