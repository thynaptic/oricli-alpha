package dualprocess

import (
	"encoding/json"
	"log"
	"os"
	"sync"
	"time"
)

const statsRingSize = 500

// ProcessStats maintains a rolling ring buffer of ProcessMismatch events
// and aggregated mismatch rates per task class.
type ProcessStats struct {
	mu       sync.Mutex
	ring     []ProcessMismatch
	head     int
	count    int
	totals   map[string]int // taskClass → total audited
	misses   map[string]int // taskClass → mismatch count
	filePath string
}

// NewProcessStats creates a ProcessStats with JSON persist at filePath.
func NewProcessStats(filePath string) *ProcessStats {
	ps := &ProcessStats{
		ring:     make([]ProcessMismatch, statsRingSize),
		totals:   make(map[string]int),
		misses:   make(map[string]int),
		filePath: filePath,
	}
	ps.load()
	return ps
}

// Record adds an audited result to the stats. Call for every non-skipped audit.
func (ps *ProcessStats) Record(demand ProcessDemand, audit ProcessAuditResult) {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	ps.totals[demand.TaskClass]++
	if audit.Mismatch() {
		ps.misses[demand.TaskClass]++
		ps.ring[ps.head] = ProcessMismatch{
			Demand:    demand,
			Audit:     audit,
			Timestamp: time.Now(),
		}
		ps.head = (ps.head + 1) % statsRingSize
		if ps.count < statsRingSize {
			ps.count++
		}
	}
}

// Stats returns aggregated mismatch rates per task class.
func (ps *ProcessStats) Stats() []MismatchStat {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	result := make([]MismatchStat, 0, len(ps.totals))
	for class, total := range ps.totals {
		misses := ps.misses[class]
		rate := 0.0
		if total > 0 {
			rate = float64(misses) / float64(total)
		}
		result = append(result, MismatchStat{
			TaskClass:    class,
			Total:        total,
			Mismatches:   misses,
			MismatchRate: rate,
		})
	}
	return result
}

// RecentMismatches returns the last n mismatch events from the ring buffer.
func (ps *ProcessStats) RecentMismatches(n int) []ProcessMismatch {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	if n > ps.count {
		n = ps.count
	}
	result := make([]ProcessMismatch, n)
	for i := 0; i < n; i++ {
		idx := (ps.head - 1 - i + statsRingSize) % statsRingSize
		result[i] = ps.ring[idx]
	}
	return result
}

// Flush persists current stats to disk.
func (ps *ProcessStats) Flush() {
	ps.mu.Lock()
	defer ps.mu.Unlock()
	ps.persist()
}

// ── persistence ───────────────────────────────────────────────────────────────

type statsSnapshot struct {
	Totals map[string]int `json:"totals"`
	Misses map[string]int `json:"misses"`
}

func (ps *ProcessStats) persist() {
	snap := statsSnapshot{Totals: ps.totals, Misses: ps.misses}
	data, err := json.MarshalIndent(snap, "", "  ")
	if err != nil {
		return
	}
	if err := os.WriteFile(ps.filePath, data, 0644); err != nil {
		log.Printf("[ProcessStats] persist error: %v", err)
	}
}

func (ps *ProcessStats) load() {
	data, err := os.ReadFile(ps.filePath)
	if err != nil {
		return
	}
	var snap statsSnapshot
	if err := json.Unmarshal(data, &snap); err != nil {
		return
	}
	if snap.Totals != nil {
		ps.totals = snap.Totals
	}
	if snap.Misses != nil {
		ps.misses = snap.Misses
	}
}
