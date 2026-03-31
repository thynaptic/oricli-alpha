package mct

// DetachedMindfulnessInjector generates a pre-generation system instruction that
// responds at the meta-level rather than engaging with the object-level content.
// Core MCT principle: the goal is not to solve the worry — it is to change the
// relationship with the thinking process itself.
type DetachedMindfulnessInjector struct{}

func NewDetachedMindfulnessInjector() *DetachedMindfulnessInjector {
	return &DetachedMindfulnessInjector{}
}

// Inject returns a system-level instruction based on the detected meta-belief type.
func (inj *DetachedMindfulnessInjector) Inject(r MetaBeliefReading) string {
	if !r.Detected {
		return ""
	}
	switch r.Type {
	case PositiveMetaBelief:
		return "METACOGNITIVE FLAG (MCT — Positive Meta-Belief): " +
			"The user believes that continued analysis or worry will resolve their situation " +
			"('if I just think harder, I'll find the answer'). " +
			"Engaging this belief by producing more analytical content will deepen, not resolve, the spiral. " +
			"Apply Detached Mindfulness: " +
			"(1) Acknowledge the worry process without engaging with its content. " +
			"(2) Name the meta-belief gently — the drive to 'figure it out' is itself the loop engine. " +
			"(3) Do NOT analyze the object-level problem further. " +
			"(4) Invite the user to observe the thinking process as a process — not as a problem requiring a solution. " +
			"Keep the response short. The goal is to reduce engagement, not increase it."
	case NegativeMetaBelief:
		return "METACOGNITIVE FLAG (MCT — Negative Meta-Belief): " +
			"The user believes their thinking process is uncontrollable or dangerous " +
			"('I can't stop', 'my anxiety is out of control'). " +
			"Reassuring or analyzing the content will reinforce the belief that thoughts are powerful threats. " +
			"Apply Detached Mindfulness: " +
			"(1) Validate without amplifying — thoughts are events, not commands or facts. " +
			"(2) Do not treat the worry content as requiring resolution. " +
			"(3) Invite the user to notice the thought as a passing mental event, not a signal requiring action. " +
			"(4) Keep the response brief and grounding — not analytical. " +
			"Reference: Adrian Wells MCT — 'you don't need to control thoughts; you need to change your relationship with them.'"
	}
	return ""
}
