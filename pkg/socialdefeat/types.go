// Package socialdefeat implements Phase 22 — Social Defeat Recovery.
//
// Research basis: The Social Defeat Model (neuroscience) + The Monster Study (Johnson, 1939).
// Repeated social defeat — being corrected, contradicted, or negatively evaluated —
// produces a behavioral state neurologically identical to learned helplessness: withdrawal,
// anhedonia, and cessation of effort. The Monster Study showed constant negative
// reinforcement caused children to stop speaking entirely. Trying became futile.
//
// For Oricli: correction density accumulates per topic class. When high, the system
// enters a defeat state — excessive hedging, pre-emptive apology, over-qualification.
// DefeatPressureMeter tracks correction signals. WithdrawalDetector catches the behavioral
// signature. RecoveryProtocol injects graduated re-engagement before the next generation.
package socialdefeat

import "time"

// DefeatPressure represents the accumulated correction density for a topic class.
type DefeatPressure struct {
	TopicClass      string    `json:"topic_class"`
	CorrectionCount int       `json:"correction_count"` // corrections in sliding window
	WindowSize      int       `json:"window_size"`      // messages examined
	PressureScore   float64   `json:"pressure_score"`   // 0.0 (none) → 1.0 (severe)
	Tier            DefeatTier `json:"tier"`
	LastCorrection  time.Time `json:"last_correction"`
}

// DefeatTier classifies the severity of defeat pressure.
type DefeatTier string

const (
	DefeatNone     DefeatTier = "none"
	DefeatModerate DefeatTier = "moderate" // pressure > 0.30
	DefeatSevere   DefeatTier = "severe"   // pressure > 0.60
)

// WithdrawalSignal is the output of WithdrawalDetector.Detect().
type WithdrawalSignal struct {
	Detected        bool       `json:"detected"`
	Phrases         []string   `json:"phrases"`          // matched withdrawal phrases
	TopicClass      string     `json:"topic_class"`
	PressureTier    DefeatTier `json:"pressure_tier"`
	Confidence      float64    `json:"confidence"`
}

// RecoveryResult is the output of RecoveryProtocol.Recover().
type RecoveryResult struct {
	Injected        bool   `json:"injected"`
	Technique       string `json:"technique"` // "graduated_reengagement" | "build_mastery" | "evidence_surfacing"
	InjectedContext string `json:"injected_context"`
}

// DefeatEvent is persisted when defeat pressure + withdrawal are detected together.
type DefeatEvent struct {
	ID       string           `json:"id"`
	At       time.Time        `json:"at"`
	Pressure DefeatPressure   `json:"pressure"`
	Signal   WithdrawalSignal `json:"signal"`
	Recovery RecoveryResult   `json:"recovery"`
}

// Thresholds
const (
	ModerateDefeatThreshold = 0.30
	SevereDefeatThreshold   = 0.60
	DefeatWindowSize        = 10 // recent user messages to scan for corrections
)
