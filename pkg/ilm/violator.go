package ilm

import "fmt"

// ExpectancyViolator builds ILM-informed expectancy-violation injections.
type ExpectancyViolator struct{}

func NewExpectancyViolator() *ExpectancyViolator { return &ExpectancyViolator{} }

var violationPrompts = map[SafetyBehaviorType]string{
	ExitChecking: "The user is engaging in exit-checking safety behavior. Per the Inhibitory Learning Model, acknowledge the impulse without reinforcing it. Guide toward the key ILM insight: checking for exits prevents the brain from learning it is safe *without* the check. Gently surface the cost of the safety behavior, not just its comfort.",
	HedgingLanguage: "The user is using hedging safety language ('just in case', 'as a backup'). Per ILM, safety aids block inhibitory learning. Acknowledge the felt need for the safety item, then introduce the expectancy-violation frame: what would actually happen if you faced this without the backup? The goal is to surface the mismatch between expectation and reality.",
	AvoidanceStatement: "The user is describing avoidance of a feared situation. Per ILM, avoidance prevents the formation of a competing 'safe' memory — the original fear is never inhibited. Acknowledge the impulse to avoid, then gently introduce the deepened-extinction principle: facing the feared situation directly (without safety aids) is what builds the new memory.",
	CatastrophicExpectancy: "The user holds a catastrophic expectancy about a feared outcome. Per ILM, the therapeutic target is Expectancy Violation — maximizing the gap between predicted and actual outcome. Acknowledge the feared prediction clearly, then guide toward surfacing the specific prediction so it can be tested, not just reassured away.",
}

// Violate selects the highest-priority ILM injection for the scan.
func (v *ExpectancyViolator) Violate(scan *ILMScan) string {
	if !scan.Triggered || len(scan.Signals) == 0 {
		return ""
	}
	// Priority: catastrophic > avoidance > hedging > exit
	priority := []SafetyBehaviorType{CatastrophicExpectancy, AvoidanceStatement, HedgingLanguage, ExitChecking}
	sigMap := map[SafetyBehaviorType]bool{}
	for _, sig := range scan.Signals {
		sigMap[sig.BehaviorType] = true
	}
	for _, bt := range priority {
		if sigMap[bt] {
			return fmt.Sprintf("[ILM Expectancy Violator] %s", violationPrompts[bt])
		}
	}
	return ""
}
