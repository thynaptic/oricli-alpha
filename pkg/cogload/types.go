package cogload

import "time"

// ── Load Tiers ────────────────────────────────────────────────────────────────

// LoadTier classifies the total cognitive load of a context window.
type LoadTier int

const (
	LoadNormal   LoadTier = iota // Total load within acceptable range — no action needed
	LoadElevated                 // Load elevated — soft warning, surgery recommended
	LoadCritical                 // Load critical — surgery required before generation
)

func (t LoadTier) String() string {
	switch t {
	case LoadNormal:
		return "normal"
	case LoadElevated:
		return "elevated"
	case LoadCritical:
		return "critical"
	}
	return "unknown"
}

// ── LoadProfile — meter output ────────────────────────────────────────────────

// LoadProfile holds the three-component cognitive load breakdown for a context.
//
// Sweller's CLT:
//   - Intrinsic  — inherent task complexity; determined by content, can't be eliminated
//   - Extraneous — noise: redundancy, old context, bloat; should be cut
//   - Germane    — effortful but schema-building processing; valuable, preserve
//
// All scores are [0.0–1.0]. TotalLoad is their sum [0.0–3.0].
type LoadProfile struct {
	Intrinsic  float64  `json:"intrinsic"`
	Extraneous float64  `json:"extraneous"`
	Germane    float64  `json:"germane"`
	TotalLoad  float64  `json:"total_load"`
	Tier       LoadTier `json:"tier"`
	TierLabel  string   `json:"tier_label"`
	Reasons    []string `json:"reasons"`
	MessageCount int    `json:"message_count"`
	TotalChars   int    `json:"total_chars"`
}

// ── Load thresholds ───────────────────────────────────────────────────────────

const (
	// ElevatedThreshold: total load at or above this triggers soft surgery.
	ElevatedThreshold = 1.20

	// CriticalThreshold: total load at or above this triggers hard surgery.
	CriticalThreshold = 1.80
)

// ── SurgeryResult — context surgery output ───────────────────────────────────

// SurgeryResult describes what the ContextSurgery removed or compressed.
type SurgeryResult struct {
	OriginalCount  int      `json:"original_count"`
	TrimmedCount   int      `json:"trimmed_count"`
	RemovedMsgs    int      `json:"removed_msgs"`
	CharsRemoved   int      `json:"chars_removed"`
	Actions        []string `json:"actions"`
	LoadBefore     float64  `json:"load_before"`
	LoadAfter      float64  `json:"load_after"`
}

// ── LoadEvent — stored in stats ring ─────────────────────────────────────────

// LoadEvent records a single measurement + optional surgery event.
type LoadEvent struct {
	Profile    LoadProfile   `json:"profile"`
	Surgery    *SurgeryResult `json:"surgery,omitempty"`
	Timestamp  time.Time     `json:"timestamp"`
}
