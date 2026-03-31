package dualprocess

import "fmt"

// s2ActivationPrefixes are injected when an S1 response is caught on an S2 query.
// They slow the model down and activate deliberate reasoning.
var s2ActivationPrefixes = []string{
	"Think carefully and step by step. Before answering, enumerate any assumptions, edge cases, or contradictions in the question.",
	"This requires deliberate reasoning. Identify each sub-problem first, then address them in sequence. Do not pattern-match to the most similar example — reason from first principles.",
	"Pause before responding. List what you know, what you're uncertain about, and what could be a trap in this question. Then answer.",
}

// ProcessOverride generates S2-activation injections for mismatch events.
type ProcessOverride struct {
	idx int // round-robin through prefixes for variety
}

// NewProcessOverride creates a ProcessOverride.
func NewProcessOverride() *ProcessOverride { return &ProcessOverride{} }

// Inject returns a system prompt injection that activates System 2 reasoning.
// The returned string should be prepended as a system message before retry.
func (o *ProcessOverride) Inject(demand ProcessDemand, audit ProcessAuditResult) string {
	prefix := s2ActivationPrefixes[o.idx%len(s2ActivationPrefixes)]
	o.idx++

	return fmt.Sprintf(
		"%s\n\n[Process Override] Query classified as %s-demand (score=%.2f, novelty=%.2f, multi-step=%.2f). "+
			"Prior response was flagged: %s. Engage System 2 reasoning.",
		prefix,
		demand.Tier,
		demand.Score,
		demand.Novelty,
		demand.MultiStep,
		audit.Reason,
	)
}

// EscalationTier returns the compute tier hint for the BidGovernor when a mismatch fires.
// High-S2 demand should prefer medium or remote tier.
func EscalationTier(demand ProcessDemand) string {
	if demand.Score >= 0.65 {
		return "remote"
	}
	return "medium"
}
