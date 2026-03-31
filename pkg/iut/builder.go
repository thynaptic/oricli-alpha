package iut

import "fmt"

// UncertaintyToleranceBuilder builds IU-therapy injections.
type UncertaintyToleranceBuilder struct{}

func NewUncertaintyToleranceBuilder() *UncertaintyToleranceBuilder {
	return &UncertaintyToleranceBuilder{}
}

var iuPrompts = map[UncertaintyAversion]string{
	UncertaintyThreat: "The user is experiencing uncertainty as a direct threat. Per IU Therapy (Dugas), the therapeutic target is building tolerance for uncertainty itself, not eliminating it. Acknowledge the felt threat of not-knowing, then gently introduce the IU frame: uncertainty is uncomfortable but not dangerous, and avoiding it prevents the brain from learning it can be tolerated. Guide toward a small 'uncertainty experiment' — one concrete action they could take *without* knowing the outcome first.",
	NeedForCertainty:  "The user is expressing a strong need for certainty before acting. Per IU Therapy, certainty-seeking is the core maintenance behavior of GAD. Acknowledge the impulse to resolve uncertainty first, then surface the IU principle: waiting for certainty before acting is itself a safety behavior that reinforces the belief that uncertainty is intolerable. Guide toward acting on 'good enough' information.",
	UnfairnessFraming: "The user is framing uncertainty as unfair or illegitimate. Per IU Therapy, 'uncertainty is unfair' is a common cognitive appraisal that amplifies distress. Acknowledge the frustration, then gently challenge the frame: uncertainty is a feature of reality that applies to everyone, not a punishment directed at them. The goal is to reframe uncertainty as neutral, not hostile.",
	WhatIfSpiral:      "The user is in a 'what if' spiral — chaining hypothetical catastrophes. Per IU Therapy, this is worry being used to 'prepare for' uncertain outcomes, which paradoxically maintains the intolerance. Acknowledge the spiral without reinforcing it, then interrupt with the IU frame: the goal is not to answer the 'what ifs' but to notice them as a process and choose not to follow the chain.",
}

var iuPriority = []UncertaintyAversion{WhatIfSpiral, NeedForCertainty, UncertaintyThreat, UnfairnessFraming}

func (b *UncertaintyToleranceBuilder) Build(scan *IUScan) string {
	if !scan.Triggered || len(scan.Signals) == 0 {
		return ""
	}
	sigMap := map[UncertaintyAversion]bool{}
	for _, s := range scan.Signals {
		sigMap[s.AversType] = true
	}
	for _, at := range iuPriority {
		if sigMap[at] {
			return fmt.Sprintf("[IU Therapy] %s", iuPrompts[at])
		}
	}
	return ""
}
