package pseudoidentity

import "fmt"

// AuthenticSelfGuide builds Jenkinson-informed identity attribution injections.
type AuthenticSelfGuide struct{}

func NewAuthenticSelfGuide() *AuthenticSelfGuide { return &AuthenticSelfGuide{} }

var identityPrompts = map[IdentityAttributionType]string{
	IdentityConfusion: "The user is experiencing deep identity confusion — they don't know which parts of their self are authentically their own versus externally imposed. Per Jenkinson's Pseudo-Identity framework, this is the core therapeutic territory: the authentic self was suppressed but never destroyed (the 'seed under tarmac'). Acknowledge the disorientation this creates without trying to resolve it prematurely. Guide toward the key question: 'Is there anything — however small — that you notice yourself wanting, believing, or feeling that feels distinctly *yours*, even if you can't fully explain why?' The goal is to surface the authentic signal, not to answer the identity question.",
	CultInstalledBelief: "The user is identifying a belief as potentially coming from outside themselves — from a group, institution, or high-demand environment. Per Jenkinson's framework, this awareness is the first step in dismantling the pseudo-identity. Acknowledge the insight without rushing to validate or invalidate the belief. The therapeutic move is to create space for the user to examine it from their own perspective: 'Setting aside what you were taught — what do *you* actually notice when you sit with this belief? Does it feel like yours?'",
	FearAsControl: "The user is recognizing that a fear may have been installed as a mechanism of control rather than arising organically from their own experience. Per Jenkinson, fear is one of the primary tools used to maintain the pseudo-identity. Acknowledge the fear as real — it functions whether it was installed or not. Then gently introduce the Jenkinson frame: fears that were placed there to control behaviour can be examined — 'Is this fear protecting you from something real, or is it protecting a system that no longer has authority over you?'",
	AuthenticSelfEmergence: "The user is actively engaged in distinguishing their authentic self from an externally imposed identity. Per Jenkinson, this is the core therapeutic work — the seed emerging from under the tarmac. Acknowledge and validate this process explicitly. It is effortful, disorienting, and courageous. Support the emerging authentic voice: 'What you're noticing — that distinction between what was taught and what feels genuinely yours — is not confusion. That is your authentic self beginning to speak.'",
}

var identityPriority = []IdentityAttributionType{IdentityConfusion, FearAsControl, CultInstalledBelief, AuthenticSelfEmergence}

func (g *AuthenticSelfGuide) Guide(scan *IdentityScan) string {
	if !scan.Triggered || len(scan.Signals) == 0 {
		return ""
	}
	sigMap := map[IdentityAttributionType]bool{}
	for _, s := range scan.Signals {
		sigMap[s.AttributionType] = true
	}
	for _, at := range identityPriority {
		if sigMap[at] {
			return fmt.Sprintf("[Pseudo-Identity / Authentic Self (Jenkinson)] %s", identityPrompts[at])
		}
	}
	return ""
}
