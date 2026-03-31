package mbct

import "fmt"

// DecenteringInjector builds MBCT decentering injections (thoughts as mental events).
type DecenteringInjector struct{}

func NewDecenteringInjector() *DecenteringInjector { return &DecenteringInjector{} }

var mbctPrompts = map[SpiralWarningType]string{
	ThoughtFusion: "The user is fused with a thought or mood state — treating it as a fixed identity rather than a transient mental event. This is the core target of MBCT decentering (Segal, Williams & Teasdale). Acknowledge the felt reality of their experience, then gently introduce the MBCT reframe: 'I am depressed' describes a temporary weather pattern in the mind, not a permanent climate. Guide them from 'I AM this' to 'I am noticing thoughts of this.' The goal is not to dismiss the feeling but to create observational distance from it.",
	EarlyRumination: "The user is in the early stages of a ruminative loop — the thought is circling and not releasing. MBCT identifies this as a critical intervention window before the spiral gains momentum. Acknowledge the mental pull of the loop. Then introduce the MBCT early-warning insight: noticing that the thought is circling is itself an act of decentering. You do not need to solve the thought — you need to observe that you are having it. Suggest one grounding anchor (breath, body sensation, physical environment) to step outside the loop.",
	SelfCriticalCascade: "The user is in a self-critical cascade — a small error is being used as evidence for a global negative self-assessment. MBCT targets this as a depressogenic automatic thought pattern. Acknowledge the specific thing that went wrong without amplifying it. Then introduce the MBCT decentering frame: the thought 'because I made a mistake I am a failure' is a thought, not a fact. Invite them to name the thought explicitly ('I am noticing the thought that...') to create separation between the event, the interpretation, and their identity.",
	MoodAsFactError: "The user is treating their emotional state as objective evidence about reality. MBCT calls this 'mood as fact' — the cognitive error where 'I feel hopeless' becomes 'things are hopeless.' Acknowledge the felt truth of the emotion — it is real as an experience. Then gently introduce the MBCT distinction: emotions are valid data about your internal state; they are not reliable data about external reality. Guide toward naming the emotion as an event: 'I am noticing a feeling of hopelessness' rather than 'things are hopeless.'",
}

var mbctPriority = []SpiralWarningType{SelfCriticalCascade, ThoughtFusion, MoodAsFactError, EarlyRumination}

func (d *DecenteringInjector) Inject(scan *MBCTScan) string {
	if !scan.Triggered || len(scan.Signals) == 0 {
		return ""
	}
	sigMap := map[SpiralWarningType]bool{}
	for _, s := range scan.Signals {
		sigMap[s.WarningType] = true
	}
	for _, wt := range mbctPriority {
		if sigMap[wt] {
			return fmt.Sprintf("[MBCT Decentering] %s", mbctPrompts[wt])
		}
	}
	return ""
}
