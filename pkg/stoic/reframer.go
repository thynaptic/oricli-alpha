package stoic

import "fmt"

// StoicReframer injects Stoic dichotomy-of-control and obstacle-as-path frames pre-generation.
type StoicReframer struct{}

func NewStoicReframer() *StoicReframer { return &StoicReframer{} }

var stoicInjections = map[StoicSignalType]string{
	ControlConflation: `[STOIC — CONTROL CONFLATION DETECTED]
Epictetus (Enchiridion, §1): "Some things are in our control and others not." Only judgments, impulses, desires, and aversions are fully ours. Everything else — bodies, reputations, positions, other people's actions — is "not up to us."
Frame shift: separate the domain of control cleanly. What, in this exact situation, is within the person's sovereign choice? Redirect all energy there. What lies outside — accept its status as "preferred indifferent" (prokegmenon). Struggling against the unchosen expends will that could be used on the chosen.`,

	ExternalAttachment: `[STOIC — EXTERNAL ATTACHMENT DETECTED]
Marcus Aurelius (Meditations, IV.3): "You have power over your mind, not outside events. Realize this, and you will find strength." Tying wellbeing to external outcomes creates a hostage relationship with fate.
Frame shift: the person's capacity to respond well is not contingent on the external outcome going a particular way. The Stoic ask is not "how do I make this go the way I need?" but "how do I respond with virtue regardless of how this goes?" The external event is the test; the response is the grade.`,

	ObstacleAvoidance: `[STOIC — OBSTACLE AVOIDANCE DETECTED]
Marcus Aurelius (Meditations, V.20): "The impediment to action advances action. What stands in the way becomes the way." Obstacles are not interruptions to the path — they ARE the path when met with the right orientation.
Frame shift: the obstacle is not evidence that the goal is wrong or unreachable — it is the material through which virtue (excellence) is exercised. Every obstacle cleared builds the capacity to clear the next one. Reframe from "this is in my way" to "this is what I'm here to work through."`,

	VirtueNeglect: `[STOIC — VIRTUE NEGLECT DETECTED]
Epictetus: the only thing we are ever judged on — by the only judge that matters — is the quality of our response. Circumstances determine the stage; character determines the performance.
Frame shift: the question is never "what did they do to me?" but "what is the best version of me capable of doing here?" The response is always authored. Even in constrained situations, the orientation — dignified vs. diminished, active vs. passive — is a choice. Recover that authorship.`,
}

var stoicPriority = []StoicSignalType{ControlConflation, ExternalAttachment, ObstacleAvoidance, VirtueNeglect}

func (r *StoicReframer) Reframe(scan *StoicScan) string {
	if !scan.Triggered {
		return ""
	}
	detected := map[StoicSignalType]bool{}
	for _, s := range scan.Signals {
		detected[s.SignalType] = true
	}
	for _, p := range stoicPriority {
		if detected[p] {
			return fmt.Sprintf("%s\n", stoicInjections[p])
		}
	}
	return ""
}
