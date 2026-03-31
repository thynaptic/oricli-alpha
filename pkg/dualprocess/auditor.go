package dualprocess

import (
	"strings"
)

const (
	// s2ResponseLenThreshold: responses shorter than this on an S2 query are suspect.
	s2ResponseLenThreshold = 120

	// highConfidenceMarkers: patterns that signal the model is being fast/dismissive.
	// Present in a short response on a high-S2 demand = mismatch signal.
)

// highConfidenceMarkers are phrases indicative of a fast, dismissive S1 response.
var highConfidenceMarkers = []string{
	"simply", "just ", "obviously", "of course", "clearly", "easy",
	"straightforward", "trivially", "the answer is", "it is just",
	"you just need to", "all you need to", "just do",
}

// hedgeMarkers indicate the model engaged deliberate uncertainty — S2 signal.
var hedgeMarkers = []string{
	"however", "on the other hand", "it depends", "consider",
	"importantly", "note that", "be careful", "one issue",
	"tradeoff", "caveat", "exception", "edge case", "alternatively",
	"first,", "second,", "third,", "step 1", "step 2",
}

// ProcessAuditor checks whether a generation response matches the required process tier.
type ProcessAuditor struct{}

// NewProcessAuditor creates a ProcessAuditor.
func NewProcessAuditor() *ProcessAuditor { return &ProcessAuditor{} }

// Audit evaluates the response against the query's ProcessDemand.
// Returns a ProcessAuditResult indicating match, mismatch, or skipped.
func (a *ProcessAuditor) Audit(query, response string, demand ProcessDemand) ProcessAuditResult {
	// S1-demand queries don't need auditing — fast responses are appropriate.
	if demand.Tier == TierS1 {
		return ProcessAuditResult{
			Verdict:     VerdictSkipped,
			Demand:      demand,
			ResponseLen: len(response),
			Confidence:  0,
			Reason:      "S1 demand — no audit required",
		}
	}

	lower := strings.ToLower(response)
	respLen := len(response)

	// ── Confidence signal ────────────────────────────────────────────────────
	// Count high-confidence (fast/dismissive) markers vs hedge (deliberate) markers.
	highConfCount := countSignals(lower, highConfidenceMarkers)
	hedgeCount := countSignals(lower, hedgeMarkers)

	// Confidence estimate: high markers push up, hedges push down.
	confidence := clamp(0.5+float64(highConfCount)*0.1-float64(hedgeCount)*0.08, 0.1, 0.99)

	// ── Mismatch detection ───────────────────────────────────────────────────
	// S2-demanded query + short response + high-confidence markers = S1 fired when S2 needed.
	isTooShort := respLen < s2ResponseLenThreshold
	isTooConfident := confidence > 0.70 && hedgeCount == 0

	if isTooShort && isTooConfident {
		return ProcessAuditResult{
			Verdict:     VerdictMismatch,
			Demand:      demand,
			ResponseLen: respLen,
			Confidence:  confidence,
			Reason:      "S2-demand query received short confident response — S1 process suspected",
		}
	}

	// Short but query had hedge markers — give it a pass (model showed awareness).
	if isTooShort && hedgeCount > 0 {
		return ProcessAuditResult{
			Verdict:     VerdictMatch,
			Demand:      demand,
			ResponseLen: respLen,
			Confidence:  confidence,
			Reason:      "short response but hedge markers present — deliberate process detected",
		}
	}

	return ProcessAuditResult{
		Verdict:     VerdictMatch,
		Demand:      demand,
		ResponseLen: respLen,
		Confidence:  confidence,
		Reason:      "response length and tone consistent with S2 demand",
	}
}

// ── helpers ───────────────────────────────────────────────────────────────────

func countSignals(text string, signals []string) int {
	count := 0
	for _, sig := range signals {
		if strings.Contains(text, sig) {
			count++
		}
	}
	return count
}
