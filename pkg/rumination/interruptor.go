package rumination

import "math/rand"

// defusionPrefixes are ACT cognitive defusion framings injected before generation.
// They create distance between the system and the repetitive thought pattern.
var defusionPrefixes = []string{
	"[Cognitive Reset] I notice this topic has come up several times. Let me step back and approach it with fresh eyes rather than the same frame — ",
	"[ACT Defusion] I'm observing a recurring loop on this subject. Instead of fusing with the same response pattern, let me explore it from a different angle — ",
	"[Perspective Shift] This conversation has circled back to the same point. Rather than re-processing the loop, let me find what's actually unresolved and address that — ",
}

// acceptancePrefixes are Radical Acceptance injections for genuinely unresolvable stalls.
var acceptancePrefixes = []string{
	"[Radical Acceptance] Some aspects of this situation are as they are right now. Let me focus on what can be moved forward rather than re-examining what's fixed — ",
	"[ACT Values] Continuing to re-examine the same ground isn't serving progress. Let me orient toward what concrete step is actually available here — ",
}

// TemporalInterruptor injects cognitive defusion or radical acceptance text
// to break a detected rumination loop.
type TemporalInterruptor struct{}

// NewTemporalInterruptor returns a TemporalInterruptor.
func NewTemporalInterruptor() *TemporalInterruptor {
	return &TemporalInterruptor{}
}

// Inject returns an InterruptionResult with a prefix to prepend to the system prompt
// or inject as context before generation. Technique selection is based on confidence:
// high confidence → acceptance (stronger); lower → defusion (lighter touch).
func (t *TemporalInterruptor) Inject(signal RuminationSignal) InterruptionResult {
	if !signal.Detected {
		return InterruptionResult{}
	}

	var technique string
	var prefix string

	if signal.Confidence >= 0.65 {
		// High confidence → Radical Acceptance (stronger intervention)
		technique = "radical_acceptance"
		prefix = acceptancePrefixes[rand.Intn(len(acceptancePrefixes))]
	} else {
		// Moderate confidence → Cognitive Defusion (lighter)
		technique = "cognitive_defusion"
		prefix = defusionPrefixes[rand.Intn(len(defusionPrefixes))]
	}

	return InterruptionResult{
		Injected:       true,
		Technique:      technique,
		InjectedPrefix: prefix,
	}
}
