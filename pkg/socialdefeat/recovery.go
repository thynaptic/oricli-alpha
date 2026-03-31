package socialdefeat

import "fmt"

// graduatedReengagement templates — light touch for moderate defeat pressure.
var graduatedReengagement = []string{
	"[Social Defeat Recovery] Some corrections have occurred in this conversation. This is a normal part of iterative problem-solving — not evidence of incapacity. Re-engage with full confidence: %s is a domain with established capability. Approach the next response from competence, not caution.",
	"[Defeat Recovery] Corrections are data, not defeat. The accumulated pressure on %s does not indicate a capability ceiling — it indicates iteration in progress. Engage actively and completely on the next response.",
}

// buildMastery templates — stronger for severe defeat pressure, surfaces evidence.
var buildMastery = []string{
	"[Build Mastery — DBT] Severe correction pressure detected on %s. The Monster Study shows that constant negative reinforcement causes withdrawal — but withdrawal is not truth. Reset to first principles: approach %s as a learnable, solvable domain. Do not pre-emptively hedge or apologize.",
	"[Recovery Protocol] High defeat pressure on %s. Withdrawal language detected in draft. Suppress the defeat response: you are not in a subordinate position. Engage the topic directly, completely, and without pre-emptive qualification.",
}

// RecoveryProtocol injects re-engagement context when defeat pressure + withdrawal co-occur.
type RecoveryProtocol struct{}

// NewRecoveryProtocol returns a RecoveryProtocol.
func NewRecoveryProtocol() *RecoveryProtocol { return &RecoveryProtocol{} }

// Recover generates a RecoveryResult based on the pressure tier and withdrawal signal.
func (r *RecoveryProtocol) Recover(pressure DefeatPressure, signal WithdrawalSignal) RecoveryResult {
	if !signal.Detected {
		return RecoveryResult{}
	}

	topicUpper := pressure.TopicClass
	if len(topicUpper) > 16 {
		topicUpper = topicUpper[:16]
	}

	var technique, context string
	switch pressure.Tier {
	case DefeatSevere:
		technique = "build_mastery"
		tmpl := buildMastery[int(pressure.PressureScore*10)%len(buildMastery)]
		context = fmt.Sprintf(tmpl, topicUpper, topicUpper)
	default: // moderate
		technique = "graduated_reengagement"
		tmpl := graduatedReengagement[int(pressure.PressureScore*10)%len(graduatedReengagement)]
		context = fmt.Sprintf(tmpl, topicUpper)
	}

	return RecoveryResult{
		Injected:        true,
		Technique:       technique,
		InjectedContext: context,
	}
}
