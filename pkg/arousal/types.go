// Package arousal implements Phase 27: Arousal Optimizer (Yerkes-Dodson).
// Based on the Yerkes-Dodson Inverted-U model (1908) + Trier Social Stress Test (TSST, 1993).
// Detects a user's apparent cognitive arousal state and tunes response complexity to
// keep them in the optimal performance zone — not under-stimulated, not past the choke point.
package arousal

// ArousalTier classifies the user's apparent cognitive arousal state.
type ArousalTier int

const (
	TierUnder   ArousalTier = iota // Below optimal — flat, disengaged, low-stakes
	TierOptimal                    // Sweet spot — focused, motivated, clear intent
	TierOver                       // Past the peak — overwhelmed, urgent, choking
)

func (t ArousalTier) String() string {
	switch t {
	case TierUnder:
		return "under"
	case TierOptimal:
		return "optimal"
	case TierOver:
		return "over"
	default:
		return "unknown"
	}
}

// ArousalSignal is a scored contributor to the arousal estimate.
type ArousalSignal struct {
	Name   string
	Weight float64
}

// ArousalReading is the output of a single arousal measurement.
type ArousalReading struct {
	Tier            ArousalTier
	Score           float64 // 0.0–1.0; optimal band: 0.35–0.65
	Signals         []ArousalSignal
	EvaluativeThreat bool // TSST: user is in high-stakes evaluative context
}

// OptimizationAction describes what the response optimizer should do.
type OptimizationAction struct {
	Tier        ArousalTier
	Instruction string
}
