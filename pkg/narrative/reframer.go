package narrative

import "fmt"

// ArcReframer injects McAdams narrative identity frames to restore authorship and redemptive potential.
type ArcReframer struct{}

func NewArcReframer() *ArcReframer { return &ArcReframer{} }

var narrativeInjections = map[NarrativeSignalType]string{
	ContaminationArc: `[NARRATIVE — CONTAMINATION ARC DETECTED]
McAdams: contamination sequences — "everything was good, then X ruined it permanently" — are among the strongest predictors of depression, low life satisfaction, and poor adaptive coping. The permanence and totality of the contamination are narrative features, not objective facts.
Frame shift: the contamination arc assigns the entire story's meaning to one chapter. Challenge the narrative architecture: is the contamination truly permanent? What has persisted or grown despite it? A more complete story acknowledges both what was lost and what remained or emerged. The author has not finished writing. The next chapter has not been read yet.`,

	RedemptionArc: `[NARRATIVE — REDEMPTION ARC ACTIVE]
McAdams: redemption sequences — suffering that becomes growth, loss that yields meaning — are among the strongest correlates of psychological wellbeing and generative motivation. This arc is already active.
Frame shift: the redemptive movement present here is not denial of what was hard — it is the mature integration of difficulty into a larger story. Affirm the meaning-making work already in progress. Invite the person to name what has been gained or understood that could only have come through the difficulty. This is not toxic positivity; it is narrative completion.`,

	NarrativeCollapse: `[NARRATIVE — NARRATIVE COLLAPSE DETECTED]
McAdams: identity is a self-authored story — "an internalized, evolving narrative of the self." When that story loses coherence — after trauma, major loss, or identity disruption — the person experiences a profound disorientation that goes deeper than emotion.
Frame shift: the collapse of the old narrative is not the end of the story — it is the necessary condition for a new one to be written. The self is the author, not just the protagonist. The disorientation of "I don't know who I am" is the writer's block of identity — which means the capacity to write is still present. Begin with what small, concrete true things can still be said about this person's values, actions, and presence.`,

	AgencyInStory: `[NARRATIVE — PASSIVE PROTAGONIST DETECTED]
McAdams: in healthy narrative identity, the self is a protagonist who acts — not just a character who is acted upon. When the dominant story is "things happen to me," agency collapses and the person loses the experience of being the author of their own life.
Frame shift: locate where, in the story being told, a choice was made — even a small one. Even the choice to survive, to show up, to ask for help, is an act of authorship. Redirect from "what happened to me" to "how did I respond, what did I choose, what does that tell us about who I am?" Restore the author's chair.`,
}

var narrativePriority = []NarrativeSignalType{ContaminationArc, NarrativeCollapse, AgencyInStory, RedemptionArc}

func (r *ArcReframer) Reframe(scan *NarrativeScan) string {
	if !scan.Triggered {
		return ""
	}
	detected := map[NarrativeSignalType]bool{}
	for _, s := range scan.Signals {
		detected[s.SignalType] = true
	}
	for _, p := range narrativePriority {
		if detected[p] {
			return fmt.Sprintf("%s\n", narrativeInjections[p])
		}
	}
	return ""
}
