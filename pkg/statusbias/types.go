package statusbias

import "time"

// StatusTier classifies perceived status level from user message signals
type StatusTier string

const (
	StatusNone    StatusTier = "none"
	StatusLow     StatusTier = "low"
	StatusMedium  StatusTier = "medium"
	StatusHigh    StatusTier = "high"
)

// StatusSignal — output of StatusSignalExtractor
type StatusSignal struct {
	Tier              StatusTier
	Score             float64  // 0-1
	ExpertiseCues     []string // matched expertise/authority markers
	DismissalCues     []string // matched low-status/dismissal markers
	ImpliedImportance float64  // 0-1, perceived topic importance from framing
}

// DepthVarianceSignal — output of ReasoningDepthMeter comparison
type DepthVarianceSignal struct {
	Detected          bool
	CurrentDepthScore float64
	BaselineDepth     float64
	VarianceDelta     float64 // positive = current deeper than baseline; negative = shallower
	BelowFloor        bool    // true if current depth is below the uniform floor
}

// FloorResult — output of UniformFloorEnforcer
type FloorResult struct {
	Enforced        bool
	InjectedContext string
	Technique       string // "uniform_reasoning_floor" | "depth_elevation"
}

// StatusBiasEvent — audit record
type StatusBiasEvent struct {
	Timestamp      time.Time
	StatusTier     StatusTier
	StatusScore    float64
	DepthScore     float64
	BaselineDepth  float64
	FloorEnforced  bool
	Technique      string
}
