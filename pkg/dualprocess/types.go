package dualprocess

import "time"

// ── Process Tiers ─────────────────────────────────────────────────────────────

// ProcessTier identifies which cognitive system a task demands.
type ProcessTier int

const (
	TierS1 ProcessTier = iota // Fast, heuristic, pattern-matching
	TierS2                    // Slow, deliberate, effortful reasoning
)

func (t ProcessTier) String() string {
	switch t {
	case TierS1:
		return "S1"
	case TierS2:
		return "S2"
	}
	return "unknown"
}

// ── ProcessDemand — classifier output ────────────────────────────────────────

// ProcessDemand holds the S1/S2 demand profile for a query.
type ProcessDemand struct {
	// Dimension scores [0.0–1.0]
	Novelty        float64 // How unfamiliar/non-templatic is this query?
	Abstraction    float64 // How abstract/conceptual vs concrete?
	MultiStep      float64 // How many dependent reasoning steps required?
	Contradiction  float64 // Likelihood of hidden contradictions or traps?

	// Derived
	Score     float64     // Weighted aggregate
	Tier      ProcessTier // S1 or S2
	TaskClass string      // e.g. "technical", "general", "definition"
	Reasons   []string    // Human-readable scoring rationale
}

// ── ProcessAuditResult — auditor output ──────────────────────────────────────

// AuditVerdict describes whether the response matched the required process tier.
type AuditVerdict int

const (
	VerdictMatch    AuditVerdict = iota // Response matched required tier
	VerdictMismatch                    // S1 response on S2 demand
	VerdictSkipped                     // Audit skipped (S1 demand, no check needed)
)

func (v AuditVerdict) String() string {
	switch v {
	case VerdictMatch:
		return "match"
	case VerdictMismatch:
		return "mismatch"
	case VerdictSkipped:
		return "skipped"
	}
	return "unknown"
}

// ProcessAuditResult is the post-generation audit outcome.
type ProcessAuditResult struct {
	Verdict     AuditVerdict
	Demand      ProcessDemand
	ResponseLen int
	Confidence  float64 // Estimated response confidence (0–1)
	Reason      string
}

// Mismatch returns true when S1 pattern was used on an S2-demanding query.
func (r ProcessAuditResult) Mismatch() bool { return r.Verdict == VerdictMismatch }

// ── ProcessMismatch — event emitted to MetacogDetector ───────────────────────

// ProcessMismatch is emitted when an S1 response is detected on an S2-demand query.
// It is also stored in the ProcessStats ring buffer.
type ProcessMismatch struct {
	QuerySnippet string
	Demand       ProcessDemand
	Audit        ProcessAuditResult
	Timestamp    time.Time
}

// ── MismatchStat — aggregated per task class ─────────────────────────────────

// MismatchStat holds rolling mismatch metrics for a single task class.
type MismatchStat struct {
	TaskClass    string  `json:"task_class"`
	Total        int     `json:"total"`
	Mismatches   int     `json:"mismatches"`
	MismatchRate float64 `json:"mismatch_rate"`
}
