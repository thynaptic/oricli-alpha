package polyvagal

import "fmt"

// VagalRestorer injects Porges Polyvagal Theory frames to guide autonomic state navigation pre-generation.
type VagalRestorer struct{}

func NewVagalRestorer() *VagalRestorer { return &VagalRestorer{} }

var polyvagalInjections = map[PolyvagalStateType]string{
	ShutdownCascade: `[POLYVAGAL — DORSAL VAGAL SHUTDOWN DETECTED]
Porges (2011): dorsal vagal shutdown is the autonomic nervous system's most ancient protective response — immobilization, collapse, affective numbing, dissociation. It activates when the nervous system perceives threat as overwhelming and inescapable. It is not weakness; it is a survival circuit.
Frame shift: the shutdown state is not permanent — it is a state, and states change. The pathway out of dorsal shutdown runs through the social engagement system (ventral vagal), not through willpower or cognitive effort alone. Signal safety: slow, warm, predictable prosodic input (tone matters as much as content). The first step is not action — it is a micro-signal of safety: "you are here, you are not alone, this is survivable."`,

	FightFlightMobilization: `[POLYVAGAL — SYMPATHETIC MOBILIZATION DETECTED]
Porges: the sympathetic nervous system has mobilized — fight/flight is active. The autonomic nervous system has assessed threat and is preparing for action. Cognitive access is reduced; the prefrontal cortex is partially offline. This is not irrational — it is the nervous system doing its job.
Frame shift: meet the activation state before offering cognitive reframes. The ventral vagal system (social engagement) is the brake on sympathetic activation — it requires a sense of co-regulation and safety before it can engage. Slow the rhythm. Acknowledge the activation without amplifying it. Only after the system begins to settle does cognitive processing become fully accessible.`,

	SocialEngagementActive: `[POLYVAGAL — SOCIAL ENGAGEMENT SYSTEM ACTIVE]
Porges: the social engagement system (ventral vagal complex) is the most evolutionarily recent circuit — it regulates facial expression, vocal prosody, middle ear, and co-regulation. When active, it signals that the nervous system has assessed sufficient safety to engage with another.
Frame shift: the person is in a co-regulatory state. This is the optimal window for connection, meaning-making, and gentle challenge. Maintain the warmth, rhythm, and attunement that keeps the ventral vagal system engaged. This is not the time for high-challenge confrontation — it is the time for deepening.`,

	VentralVagalAccess: `[POLYVAGAL — VENTRAL VAGAL ACCESS CONFIRMED]
Porges: ventral vagal dominance is the physiological substrate of safety, connection, and regulated engagement. The nervous system is currently assessing the environment as safe enough to be present, curious, and open.
Frame shift: this is the ideal state for learning, integration, and growth. The window is open. Engage fully — the person has the physiological capacity to receive, process, and integrate. Recognize and name this state when appropriate; it builds the person's awareness of what regulated safety feels like, making it easier to return to.`,
}

func (r *VagalRestorer) Restore(scan *PolyvagalScan) string {
	if !scan.Triggered {
		return ""
	}
	if inj, ok := polyvagalInjections[scan.InferredState]; ok {
		return fmt.Sprintf("%s\n", inj)
	}
	return ""
}
