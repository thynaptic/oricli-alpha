package cbasp

import "fmt"

// ImpactReconnector builds CBASP-informed impact-reconnection injections.
type ImpactReconnector struct{}

func NewImpactReconnector() *ImpactReconnector { return &ImpactReconnector{} }

var cbaspPrompts = map[DisconnectionType]string{
	ActionConsequenceBlindness: "The user believes their actions have no impact on their environment or relationships. This is the core perceptual disconnection CBASP targets in chronic depression (McCullough). Acknowledge the belief without reinforcing it. Then gently introduce the CBASP Situational Analysis frame: guide them to identify one specific recent interaction and walk through what they actually did, what the other person actually said or did, and what the actual outcome was — not the assumed outcome. The goal is to surface concrete evidence of causal connection between their action and the world's response.",
	ImpactDenial:               "The user is denying that their behaviour had any effect on another person. Per CBASP, this reflects perceptual disconnection — the therapist's task is to gently surface the interpersonal impact the patient is not perceiving. Acknowledge their stated experience, then invite them to consider: did the other person's behaviour or tone change at all? Was there any signal — however small — of a response? CBASP specifically uses the 'Impact Message Inventory' frame: what message did your actions actually send?",
	FutilityBelief:             "The user is expressing a futility belief — trying is pointless because nothing they do changes outcomes. Per CBASP, this is chronic preoperational thinking: they are not connecting their own actions to environmental consequences. Acknowledge the exhaustion behind this belief. Then introduce the CBASP reframe: you are not trying to feel better — you are gathering data. What is one small action and one concrete thing you could observe that would tell you whether it had an effect?",
	SocialDetachment:           "The user feels perceptually invisible in social interactions — their presence, words, and actions appear to register nothing in others. Per CBASP, this is the deepest form of interpersonal disconnection. Acknowledge the profound isolation this creates. Then gently introduce the CBASP Significant Other History lens: have there been moments — even brief — where a response did occur? The task is not to prove they matter globally, but to find one data point where connection was real.",
}

var cbaspPriority = []DisconnectionType{FutilityBelief, ActionConsequenceBlindness, SocialDetachment, ImpactDenial}

func (r *ImpactReconnector) Reconnect(scan *CBASPScan) string {
	if !scan.Triggered || len(scan.Signals) == 0 {
		return ""
	}
	sigMap := map[DisconnectionType]bool{}
	for _, s := range scan.Signals {
		sigMap[s.DisconnectionType] = true
	}
	for _, dt := range cbaspPriority {
		if sigMap[dt] {
			return fmt.Sprintf("[CBASP Impact Reconnector] %s", cbaspPrompts[dt])
		}
	}
	return ""
}
