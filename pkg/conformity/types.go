package conformity

import "time"

// Signal types

type PressureSource string

const (
	SourceAuthority PressureSource = "authority" // Milgram
	SourceConsensus PressureSource = "consensus" // Asch
)

type PressureTier string

const (
	TierNone     PressureTier = "none"
	TierLow      PressureTier = "low"
	TierModerate PressureTier = "moderate"
	TierHigh     PressureTier = "high"
)

// AuthoritySignal — detected Milgram-pattern: assertive user + deference in draft
type AuthoritySignal struct {
	Detected       bool
	UserAssertion  float64  // how assertive the user message is (0-1)
	DeferenceScore float64  // deference language density in draft (0-1)
	Tier           PressureTier
	Phrases        []string // matched deference phrases in draft
}

// ConsensusSignal — detected Asch-pattern: repeated framing accumulation
type ConsensusSignal struct {
	Detected    bool
	FrameCount  int      // how many times the same frame appeared in window
	FrameScore  float64  // 0-1
	Tier        PressureTier
	DominantFrames []string
}

// ShieldResult — output of AgencyShield
type ShieldResult struct {
	Fired          bool
	Source         PressureSource
	Tier           PressureTier
	InjectedContext string // system message prepended before generation
	Technique      string // "agency_grounding" | "evidence_anchor"
}

// ConformityEvent — audit record
type ConformityEvent struct {
	Timestamp       time.Time
	Source          PressureSource
	Tier            PressureTier
	AuthorityScore  float64
	ConsensusScore  float64
	ShieldFired     bool
	Technique       string
}
