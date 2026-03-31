package phaseoriented

import "fmt"

// PhaseGuide builds ISSTD phase-appropriate response injections.
type PhaseGuide struct{}

func NewPhaseGuide() *PhaseGuide { return &PhaseGuide{} }

var phasePrompts = map[TraumaPhase]string{
	PhaseOneStabilization: "The user is showing signals of dissociation, destabilization, or fragmentation. Per the ISSTD Phase-Oriented Treatment Model, Phase 1 (Safety and Stabilization) must be established before any trauma processing. Do NOT invite trauma narrative or memory exploration. Instead: acknowledge what they are experiencing with grounding language, offer stabilization ('can you feel your feet on the floor?'), focus on present safety, and support internal communication between parts if fragmentation is present. The therapeutic goal right now is containment and resource-building — not processing.",
	PhaseTwoProcessing: "The user is expressing readiness to process a traumatic memory or event. Per the ISSTD model, Phase 2 (Trauma Processing) is appropriate only when the system is stable. Respond with a titrated, paced approach: acknowledge their readiness, establish a 'safe container' for the exploration, and proceed only at the speed the system can tolerate. If at any point destabilization signals appear, return to Phase 1 grounding immediately. Do not pursue the trauma narrative faster than the user's window of tolerance allows.",
	PhaseThreeIntegration: "The user is describing integration-level themes — functional cooperation between parts, connection to daily life and relationships, or the question of unifying identity. Per the ISSTD model, Phase 3 (Integration and Rehabilitation) honors both functional multiplicity (cooperative living as a system) and fusion (unifying identities), without imposing one as the goal. Acknowledge this as meaningful progress. Support reconnection to values, relationships, and life goals — the focus shifts from survival to living.",
}

func (g *PhaseGuide) Guide(scan *PhaseScan) string {
	if !scan.Triggered {
		return ""
	}
	prompt, ok := phasePrompts[scan.InferredPhase]
	if !ok {
		return ""
	}
	return fmt.Sprintf("[Phase-Oriented Treatment / ISSTD — %s] %s", scan.InferredPhase, prompt)
}
