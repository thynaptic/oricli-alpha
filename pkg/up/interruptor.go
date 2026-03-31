package up

import "fmt"

// ARCInterruptor builds Unified Protocol ARC-cycle injections.
type ARCInterruptor struct{}

func NewARCInterruptor() *ARCInterruptor { return &ARCInterruptor{} }

const arcFullCyclePrompt = `The user is describing a full ARC (Antecedent → Response → Consequence) emotional cycle. Per the Unified Protocol (Barlow), the therapeutic target is the *response* — not the trigger (antecedent) or the outcome (consequence). Acknowledge the cycle they are describing, then guide toward the UP insight: the emotional response itself is not the problem; the avoidance or escape behavior that follows is what maintains the disorder. Help them identify the specific response and surface what a different response might look like — one that does not reinforce avoidance.`

const arcPartialCyclePrompt = `The user is describing part of an emotional trigger-response cycle. Per the Unified Protocol (Barlow), awareness of the ARC cycle (Antecedent → Response → Consequence) is itself therapeutic. Acknowledge what they have identified, then gently help them map the full cycle: what triggered it, how they responded (physically and mentally), and what happened after. Naming the cycle is the first step toward changing the response.`

func (a *ARCInterruptor) Interrupt(scan *ARCScan) string {
	if len(scan.Signals) == 0 {
		return ""
	}
	hasC := false
	for _, s := range scan.Signals {
		if s.Component == ConsequenceDetected { hasC = true }
	}
	if scan.HasCycle && hasC {
		return fmt.Sprintf("[Unified Protocol ARC] %s", arcFullCyclePrompt)
	}
	if scan.HasCycle || len(scan.Signals) > 0 {
		return fmt.Sprintf("[Unified Protocol ARC] %s", arcPartialCyclePrompt)
	}
	return ""
}
