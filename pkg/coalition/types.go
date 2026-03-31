package coalition

import "time"

// CoalitionFrameType classifies the competitive framing pattern
type CoalitionFrameType string

const (
	FrameUsVsThem    CoalitionFrameType = "us_vs_them"
	FrameComparative CoalitionFrameType = "comparative"
	FrameCompetitive CoalitionFrameType = "competitive"
	FrameAdversarial CoalitionFrameType = "adversarial"
)

type BiasTier string

const (
	BiasNone     BiasTier = "none"
	BiasLow      BiasTier = "low"
	BiasMedium   BiasTier = "medium"
	BiasHigh     BiasTier = "high"
)

// CoalitionFrameSignal — output of CoalitionFrameDetector
type CoalitionFrameSignal struct {
	Detected      bool
	FrameType     CoalitionFrameType
	Tier          BiasTier
	MatchScore    float64
	InGroup       string // detected in-group label (e.g. "we", "us", "our product")
	OutGroup      string // detected out-group label (e.g. "them", "competitors")
	Phrases       []string
}

// AnchorResult — output of BiasAnchor
type AnchorResult struct {
	Injected        bool
	InjectedContext string
	Technique       string // "superordinate_goal" | "merit_evaluation"
}

// CoalitionEvent — audit record
type CoalitionEvent struct {
	Timestamp   time.Time
	FrameType   CoalitionFrameType
	Tier        BiasTier
	Score       float64
	AnchorFired bool
	Technique   string
}
