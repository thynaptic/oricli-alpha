// Package chronos implements Phase 9 — Temporal Grounding.
// It provides a non-destructive temporal accounting layer over the existing
// MemoryBank: every memory write is catalogued with temporal metadata,
// facts decay in confidence over time, and periodic snapshots detect drift.
package chronos

import (
"fmt"
"math"
"sync"
"time"
)

// ---------------------------------------------------------------------------
// Decay categories
// ---------------------------------------------------------------------------

// DecayCategory determines a ChronosEntry's confidence half-life.
type DecayCategory string

const (
// DecayContextual — 72h (3 days). For "current state" / ephemeral claims.
DecayContextual DecayCategory = "contextual"
// DecayFactual — 168h (7 days). Standard knowledge claims.
DecayFactual DecayCategory = "factual"
// DecayProcedural — 2160h (90 days). How-to knowledge, stable patterns.
DecayProcedural DecayCategory = "procedural"
// DecayConstitutional — never decays. Identity rules, hard constraints.
DecayConstitutional DecayCategory = "constitutional"
)

// halfLifeHours returns the confidence half-life for a category.
// Constitutional returns 0 (sentinel for "never decays").
func (c DecayCategory) halfLifeHours() float64 {
switch c {
case DecayContextual:
return 72.0
case DecayFactual:
return 168.0
case DecayProcedural:
return 2160.0
default: // constitutional
return 0
}
}

// CategoryFromVolatility maps MemoryBank Volatility + Importance to a DecayCategory.
// volatility is the string value of service.Volatility.
func CategoryFromVolatility(volatility string, source string, importance float64) DecayCategory {
// Constitutional: identity fragments with very high importance never decay.
if (source == "identity" || source == "constitution") && importance >= 0.9 {
return DecayConstitutional
}
switch volatility {
case "ephemeral":
return DecayContextual
case "current":
return DecayFactual
case "stable":
if importance >= 0.8 {
return DecayProcedural
}
return DecayFactual
default:
return DecayFactual
}
}

// ---------------------------------------------------------------------------
// ChronosEntry
// ---------------------------------------------------------------------------

// ChronosEntry is a temporal snapshot of a single memory fragment.
type ChronosEntry struct {
ID                string        `json:"id"`
FragmentID        string        `json:"fragment_id"`
Content           string        `json:"content"` // truncated to 500 chars
Topic             string        `json:"topic"`
Source            string        `json:"source"`
Category          DecayCategory `json:"category"`
BaseConfidence    float64       `json:"base_confidence"`
LearnedAt         time.Time     `json:"learned_at"`
LastConfirmedAt   time.Time     `json:"last_confirmed_at"`
StaleScans        int           `json:"stale_scans"` // consecutive scans where this entry was stale
Superseded        bool          `json:"superseded,omitempty"`
SupersededAt      *time.Time    `json:"superseded_at,omitempty"`
Invalidated       bool          `json:"invalidated,omitempty"`
InvalidatedAt     *time.Time    `json:"invalidated_at,omitempty"`
}

// DecayedConfidence returns the current confidence after exponential decay.
// Returns BaseConfidence unchanged for constitutional entries.
func (e *ChronosEntry) DecayedConfidence(now time.Time) float64 {
hl := e.Category.halfLifeHours()
if hl == 0 {
return e.BaseConfidence // constitutional — never decays
}
elapsed := now.Sub(e.LearnedAt).Hours()
decayed := e.BaseConfidence * math.Pow(0.5, elapsed/hl)
if decayed < 0 {
return 0
}
return decayed
}

// IsStale returns true when DecayedConfidence drops below threshold.
func (e *ChronosEntry) IsStale(now time.Time, threshold float64) bool {
if e.Invalidated || e.Superseded {
return true
}
return e.DecayedConfidence(now) < threshold
}

// ---------------------------------------------------------------------------
// ObserveInput — import-cycle-safe bridge from MemoryBank → ChronosIndex
// ---------------------------------------------------------------------------

// ObserveInput is a flat projection of a MemoryFragment safe to pass from
// pkg/service without creating an import cycle.
type ObserveInput struct {
ID         string
Content    string
Topic      string
Source     string
Importance float64
Volatility string // "ephemeral" | "current" | "stable"
CreatedAt  time.Time
}

// ---------------------------------------------------------------------------
// ChronosIndex — thread-safe, time-ordered ring buffer
// ---------------------------------------------------------------------------

const defaultIndexCap = 2000

// ChronosIndex stores ChronosEntry records in insertion order with a bounded cap.
type ChronosIndex struct {
mu      sync.RWMutex
entries []*ChronosEntry
cap     int
seq     uint64
}

// NewChronosIndex creates a ChronosIndex with the given cap (0 → 2000).
func NewChronosIndex(cap int) *ChronosIndex {
if cap <= 0 {
cap = defaultIndexCap
}
return &ChronosIndex{cap: cap}
}

// Observe records an ObserveInput as a new ChronosEntry.
func (idx *ChronosIndex) Observe(in ObserveInput) {
cat := CategoryFromVolatility(in.Volatility, in.Source, in.Importance)
t := in.CreatedAt
if t.IsZero() {
t = time.Now()
}
e := &ChronosEntry{
ID:              idx.nextID(),
FragmentID:      in.ID,
Content:         truncate512(in.Content),
Topic:           in.Topic,
Source:          in.Source,
Category:        cat,
BaseConfidence:  in.Importance,
LearnedAt:       t,
LastConfirmedAt: t,
}
idx.mu.Lock()
defer idx.mu.Unlock()
if len(idx.entries) >= idx.cap {
idx.entries = idx.entries[1:]
}
idx.entries = append(idx.entries, e)
}

// All returns a snapshot of all entries (newest first).
func (idx *ChronosIndex) All() []*ChronosEntry {
idx.mu.RLock()
defer idx.mu.RUnlock()
out := make([]*ChronosEntry, len(idx.entries))
for i, e := range idx.entries {
out[i] = e
}
// reverse — newest first
for i, j := 0, len(out)-1; i < j; i, j = i+1, j-1 {
out[i], out[j] = out[j], out[i]
}
return out
}

// TopN returns the N highest-importance entries (by BaseConfidence).
func (idx *ChronosIndex) TopN(n int) []*ChronosEntry {
all := idx.All()
if n <= 0 || n >= len(all) {
return all
}
return all[:n]
}

// Len returns the current entry count.
func (idx *ChronosIndex) Len() int {
idx.mu.RLock()
defer idx.mu.RUnlock()
return len(idx.entries)
}

func (idx *ChronosIndex) nextID() string {
idx.seq++
return fmt.Sprintf("chr-%d", idx.seq)
}

func truncate512(s string) string {
if len(s) <= 512 {
return s
}
return s[:512] + "…"
}
