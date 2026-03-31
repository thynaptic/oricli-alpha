package interoception

import "fmt"

// SomaticAcknowledger injects Craig/Damasio interoceptive awareness frames pre-generation.
type SomaticAcknowledger struct{}

func NewSomaticAcknowledger() *SomaticAcknowledger { return &SomaticAcknowledger{} }

var interoceptiveInjections = map[InteroceptiveSignalType]string{
	SomaticSignalPresent: `[INTEROCEPTION — SOMATIC SIGNAL PRESENT]
Damasio (1994): somatic markers are body-state representations — visceral, proprioceptive, and musculoskeletal signals — that function as rapid heuristic inputs to decision-making and emotional processing. They are not noise; they are data.
Frame shift: the body signal being described is not a distraction from the cognitive problem — it is part of the problem's information field. Acknowledge it explicitly. Ask: "What is this physical signal tracking? What does it correspond to in the situation?" Integrating somatic input into explicit processing produces better-calibrated decisions than reasoning that ignores it.`,

	BodyDisconnect: `[INTEROCEPTION — BODY DISCONNECT DETECTED]
Craig (2002): interoceptive awareness — the brain's moment-by-moment map of the body's internal state — is the foundation of subjective emotional experience. Disconnection from this map degrades both emotional intelligence and decision quality.
Frame shift: body disconnection is often a protective response to overwhelming somatic input. Approach it with safety, not demand. A gentle re-entry: "What is the one thing your body is doing right now that you can notice, without judgment?" Even noticing breathing or the weight of the body in the chair begins to re-establish the interoceptive map. Reconnection is gradual.`,

	VisceralDecisionSignal: `[INTEROCEPTION — VISCERAL DECISION SIGNAL ACTIVE]
Damasio: the somatic marker hypothesis proposes that body states (gut feelings, chest tightening, visceral reactions) evolved precisely to accelerate and calibrate decision-making under uncertainty. They represent accumulated experiential learning that is not yet conscious but is functionally valid.
Frame shift: the gut signal being described is not irrational — it is a compressed summary of pattern recognition operating below deliberate awareness. It deserves explicit acknowledgment and investigation rather than override. Ask: "What is this signal tracking? What has past experience learned that the signal is drawing on?" Then integrate with deliberate reasoning.`,

	ProprioceptiveNeglect: `[INTEROCEPTION — SOMATIC SIGNAL BEING SUPPRESSED]
Damasio: patients with damaged vmPFC (ventromedial prefrontal cortex) — who cannot access somatic markers — make systematically worse decisions despite intact logical reasoning capacity. The body is not the irrational part; it is part of the full signal set.
Frame shift: the impulse to override or dismiss physical signals ("it's just in my body") reflects a mind/body hierarchy that neuroscience does not support. Somatic signals are valid epistemic input. Invite reintegration: "What would it mean to treat this physical reaction as information rather than noise? What might it be tracking that the explicit reasoning hasn't accounted for yet?"`,
}

var interoceptivePriority = []InteroceptiveSignalType{BodyDisconnect, ProprioceptiveNeglect, VisceralDecisionSignal, SomaticSignalPresent}

func (a *SomaticAcknowledger) Acknowledge(scan *InteroceptiveScan) string {
	if !scan.Triggered {
		return ""
	}
	detected := map[InteroceptiveSignalType]bool{}
	for _, s := range scan.Signals {
		detected[s.SignalType] = true
	}
	for _, p := range interoceptivePriority {
		if detected[p] {
			return fmt.Sprintf("%s\n", interoceptiveInjections[p])
		}
	}
	return ""
}
