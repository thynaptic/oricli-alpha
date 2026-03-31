package mbt

// MentalizingPrompt generates a pre-generation instruction to restore mentalizing.
// The goal is not to invalidate the user's experience — it's to open the
// perspective of the other person before Oricli validates or amplifies the reaction.
type MentalizingPrompt struct{}

func NewMentalizingPrompt() *MentalizingPrompt { return &MentalizingPrompt{} }

func (p *MentalizingPrompt) Inject(r MentalizingReading) string {
	if !r.Detected {
		return ""
	}
	base := "MENTALIZING PROMPT (MBT — Bateman & Fonagy): "
	switch r.FailureType {
	case AttributionFailure:
		return base +
			"The user is attributing clear or malicious intent to another person without exploring their mental state. " +
			"Do NOT validate the attribution as fact. " +
			"Gently hold both perspectives: acknowledge the user's experience AND invite curiosity about what the other person might have been thinking, feeling, or intending. " +
			"'Stop and think' is the core MBT maneuver — slow the reactive loop before it becomes a fixed narrative. " +
			"Ask or model: what else could explain their behavior? What might they have been feeling?"
	case ReactiveMode:
		return base +
			"The user is framing their reaction as automatic or inevitable ('I had no choice', 'anyone would'). " +
			"This closes off mentalizing — both of self and other. " +
			"Validate the intensity of the feeling while gently reopening agency: " +
			"there was likely a mental state (threat, hurt, fear) that drove the reaction. " +
			"Help them name that state rather than just describe the behavior."
	case PureHaviorism:
		return base +
			"The user is describing another person purely in behavioral terms with no mental state attribution. " +
			"Invite them to step into the other person's perspective: " +
			"what might that person have been feeling, needing, or fearing that produced that behavior? " +
			"Do not moralize — just open the mental state space."
	}
	return ""
}
