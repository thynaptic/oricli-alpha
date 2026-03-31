package arousal

// ArousalOptimizer generates response complexity/style instructions based on arousal tier.
// Under-arousal: inject structure and stakes to engage.
// Over-arousal: simplify hard — short sentences, direct answers, one thing at a time.
// Optimal: no intervention.
type ArousalOptimizer struct{}

func NewArousalOptimizer() *ArousalOptimizer { return &ArousalOptimizer{} }

// Optimize returns an OptimizationAction for the given reading.
// Returns nil if no intervention is needed (TierOptimal).
func (o *ArousalOptimizer) Optimize(r ArousalReading) *OptimizationAction {
	switch r.Tier {
	case TierUnder:
		return &OptimizationAction{
			Tier: TierUnder,
			Instruction: "The user appears under-engaged. Structure your response with clear sections, " +
				"add concrete examples, and frame the stakes of the topic to restore cognitive engagement. " +
				"Avoid flat, list-only answers.",
		}
	case TierOver:
		if r.EvaluativeThreat {
			return &OptimizationAction{
				Tier: TierOver,
				Instruction: "The user is under acute evaluative pressure (high-stakes context — presentation, " +
					"interview, review). They are likely past the Yerkes-Dodson optimal point. " +
					"Respond with maximum brevity: short sentences, single focused answer, clear next action. " +
					"Do not introduce new considerations. Ground them first, expand second.",
			}
		}
		return &OptimizationAction{
			Tier: TierOver,
			Instruction: "The user shows signs of cognitive overload / over-arousal. " +
				"They are likely past the Yerkes-Dodson optimal performance threshold — adding more information " +
				"will degrade, not improve, their outcome. " +
				"Respond with maximum clarity: one idea at a time, shortest possible sentences, " +
				"no tangents. State the single most important thing first.",
		}
	default:
		return nil
	}
}
