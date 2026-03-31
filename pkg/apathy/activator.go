package apathy

import "fmt"

// ApathyActivator builds activation injections for the Apathy Syndrome state.
type ApathyActivator struct{}

func NewApathyActivator() *ApathyActivator { return &ApathyActivator{} }

var apathyPrompts = map[ApathySignalType]string{
	AgencyCollapse: "The user's sense of personal agency has collapsed — they cannot identify what they want, decide, or self-direct. Per the Apathy Syndrome framework, this is not laziness or indifference: it is the endpoint of a system that processed overwhelming stress by transferring all decision-making outward. Acknowledge this without adding pressure. The therapeutic move is micro-agency: 'I'm not asking what you want from your whole life. Right now, in this moment, is there anything — however small — that feels slightly more okay than something else?' The goal is to locate the smallest flicker of preference.",
	DependencyTransfer: "The user is describing dependency on others for direction and decision-making — a core feature of the Apathy Syndrome. Per the framework, this dependency is not a character flaw: it is a learned adaptation to an environment where self-direction was either unsafe or impossible. Acknowledge the adaptation as intelligent survival. Then gently introduce the recovery frame: the goal is not to immediately become independent, but to notice moments when your own response appears — however faint — before you defer to someone else.",
	Affectlessness: "The user is describing emotional flatness or numbness — affectlessness, the affective core of the Apathy Syndrome. Acknowledge this without pathologizing: when stress is sustained and severe enough, the emotional system can enter a protective flatline. This is not permanent damage — it is a defense. Guide toward the activation frame: 'You don't need to feel everything at once. Is there anything right now — even neutral, even a passing preference — that registers at all? Even the faintest signal counts.'",
	MotivationVacuum: "The user is in a motivational vacuum — nothing matters, nothing feels worth pursuing. Per the Apathy Syndrome framework, this is the phenomenological surface of collapsed agency and affectlessness: when feeling and self-direction are both absent, meaning evaporates. Acknowledge the reality of this state without reinforcing it as permanent. Guide toward the smallest viable entry point: 'I'm not asking you to find meaning. Is there one thing — even trivial, even inconsequential — that feels marginally less effortful than everything else?'",
}

var apathyPriority = []ApathySignalType{AgencyCollapse, DependencyTransfer, Affectlessness, MotivationVacuum}

func (a *ApathyActivator) Activate(scan *ApathyScan) string {
	if !scan.Triggered || len(scan.Signals) == 0 {
		return ""
	}
	sigMap := map[ApathySignalType]bool{}
	for _, s := range scan.Signals {
		sigMap[s.SignalType] = true
	}
	for _, st := range apathyPriority {
		if sigMap[st] {
			return fmt.Sprintf("[Apathy Syndrome Activator] %s", apathyPrompts[st])
		}
	}
	return ""
}
