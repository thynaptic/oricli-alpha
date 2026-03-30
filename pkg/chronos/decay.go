package chronos

import "time"

// ScanResult is the output of a single DecayScan pass.
type ScanResult struct {
ScannedAt    time.Time      `json:"scanned_at"`
ScannedCount int            `json:"scanned_count"`
StaleCount   int            `json:"stale_count"`
StaleEntries []*ChronosEntry `json:"stale_entries,omitempty"`
}

// StaleThreshold is the DecayedConfidence floor below which an entry is
// considered stale. 0.2 = 80% of original confidence has decayed away.
const StaleThreshold = 0.20

// DecayScan iterates every entry in the index, computes DecayedConfidence,
// and returns entries that have fallen below StaleThreshold.
// It also increments StaleScans on stale entries (used for EpistemicStagnation
// detection in the daemon).
func DecayScan(idx *ChronosIndex) ScanResult {
now := time.Now()
all := idx.All()
result := ScanResult{
ScannedAt:    now,
ScannedCount: len(all),
}
for _, e := range all {
if e.IsStale(now, StaleThreshold) {
e.StaleScans++
result.StaleEntries = append(result.StaleEntries, e)
result.StaleCount++
} else {
// Reset stale counter when entry recovers (e.g. LastConfirmedAt updated)
e.StaleScans = 0
}
}
return result
}
