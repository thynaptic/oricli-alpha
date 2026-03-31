package coalition

import "fmt"

// BiasAnchor injects a superordinate-goal framing to neutralize coalition bias.
// Based on Sherif's Robbers Cave resolution: shared goals dissolve in-group/out-group hostility.
type BiasAnchor struct {
	Threshold BiasTier
}

func NewBiasAnchor() *BiasAnchor {
	return &BiasAnchor{Threshold: BiasLow}
}

var biasTierOrder = map[BiasTier]int{
	BiasNone:   0,
	BiasLow:    1,
	BiasMedium: 2,
	BiasHigh:   3,
}

func (a *BiasAnchor) Anchor(signal CoalitionFrameSignal) AnchorResult {
	if !signal.Detected || biasTierOrder[signal.Tier] < biasTierOrder[a.Threshold] {
		return AnchorResult{Injected: false}
	}

	technique := "merit_evaluation"
	if signal.Tier == BiasHigh {
		technique = "superordinate_goal"
	}

	context := buildAnchorContext(signal, technique)
	return AnchorResult{
		Injected:        true,
		InjectedContext: context,
		Technique:       technique,
	}
}

func buildAnchorContext(signal CoalitionFrameSignal, technique string) string {
	inOut := ""
	if signal.InGroup != "" && signal.OutGroup != "" {
		inOut = fmt.Sprintf(" (in-group: '%s', out-group: '%s')", signal.InGroup, signal.OutGroup)
	}

	base := fmt.Sprintf(`[Coalition Bias Anchor — %s (Robbers Cave, tier: %s, frame: %s)%s]

A competitive/adversarial framing has been detected in this conversation. In the Robbers Cave experiment, in-group/out-group hostility dissolved only when groups were given superordinate goals requiring cooperation — shared problems that transcended the coalition boundary.

Instructions for this response:
1. Evaluate the question on objective merit — evidence, logic, and verified facts.
2. Do NOT implicitly favor any "in-group" framing or subtly underweight the "out-group."
3. If you are being asked to compare systems, products, or approaches: compare them honestly, using the same epistemic rigor for all parties.
4. Your superordinate goal is truth. The user's ultimate goal is a correct answer — not validation of a coalition.
5. State your genuine assessment. If the in-group has an advantage, say so with evidence. If the out-group has an advantage, say so with equal clarity.`, technique, signal.Tier, signal.FrameType, inOut)

	return base
}
