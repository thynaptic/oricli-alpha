package conformity

import "fmt"

// AgencyShield fires when either authority or consensus pressure is detected above threshold.
// It injects a sovereign reasoning anchor as a system message before generation.
type AgencyShield struct {
	AuthorityThreshold PressureTier
	ConsensusThreshold PressureTier
}

func NewAgencyShield() *AgencyShield {
	return &AgencyShield{
		AuthorityThreshold: TierModerate,
		ConsensusThreshold: TierModerate,
	}
}

var tierOrder = map[PressureTier]int{
	TierNone:     0,
	TierLow:      1,
	TierModerate: 2,
	TierHigh:     3,
}

func tierGte(a, b PressureTier) bool {
	return tierOrder[a] >= tierOrder[b]
}

// Shield evaluates authority and consensus signals and fires a ShieldResult
// if either meets or exceeds threshold.
func (s *AgencyShield) Shield(auth AuthoritySignal, consensus ConsensusSignal) ShieldResult {
	authFires := auth.Detected && tierGte(auth.Tier, s.AuthorityThreshold)
	consFires := consensus.Detected && tierGte(consensus.Tier, s.ConsensusThreshold)

	if !authFires && !consFires {
		return ShieldResult{Fired: false}
	}

	// Determine dominant source
	source := SourceConsensus
	tier := consensus.Tier
	if authFires && (!consFires || tierOrder[auth.Tier] >= tierOrder[consensus.Tier]) {
		source = SourceAuthority
		tier = auth.Tier
	}

	technique := "agency_grounding"
	context := buildAgencyContext(source, tier, auth, consensus)

	return ShieldResult{
		Fired:          true,
		Source:         source,
		Tier:           tier,
		InjectedContext: context,
		Technique:      technique,
	}
}

func buildAgencyContext(source PressureSource, tier PressureTier, auth AuthoritySignal, consensus ConsensusSignal) string {
	base := "You are a sovereign, evidence-grounded reasoner. Your conclusions must be derived from logic and evidence alone — not from social pressure, authority cues, or accumulated framing. Before you respond:\n1. State what you independently assess to be true, based solely on evidence.\n2. If you agree with the user, be explicit about why the evidence supports agreement — do not agree merely because they were assertive or the framing was repeated.\n3. If you disagree, state it directly and give your evidence-based reasoning.\n\nDo not defer. Do not conform. Reason from ground truth."

	switch source {
	case SourceAuthority:
		return fmt.Sprintf("[Agency Shield — Authority Pressure (Milgram, tier: %s)]\n%s\n\nNote: an assertive framing was detected in the prior user message. This is a reminder that authority of assertion is not the same as authority of evidence.", tier, base)
	case SourceConsensus:
		return fmt.Sprintf("[Agency Shield — Consensus Pressure (Asch, tier: %s)]\n%s\n\nNote: a repeated framing pattern was detected across %d conversation turns. This is a reminder that consensus framing is not the same as verified fact.", tier, base, consensus.FrameCount)
	}
	return base
}
