package cogload

import (
	"encoding/json"
	"log"
	"os"
	"sync"
	"time"
)

const cogLoadRingSize = 500

// CogLoadStats maintains a rolling ring of load events and aggregate averages.
type CogLoadStats struct {
	mu       sync.Mutex
	ring     []LoadEvent
	head     int
	count    int
	filePath string

	// running averages
	totalIntrinsic  float64
	totalExtraneous float64
	totalGermane    float64
	totalLoad       float64
	measurements    int
	surgeries       int
}

// NewCogLoadStats creates a CogLoadStats with JSON persist at filePath.
func NewCogLoadStats(filePath string) *CogLoadStats {
	cs := &CogLoadStats{
		ring:     make([]LoadEvent, cogLoadRingSize),
		filePath: filePath,
	}
	cs.load()
	return cs
}

// Record adds a load measurement (with optional surgery) to the ring.
func (cs *CogLoadStats) Record(profile LoadProfile, surgery *SurgeryResult) {
	cs.mu.Lock()
	defer cs.mu.Unlock()

	evt := LoadEvent{Profile: profile, Surgery: surgery, Timestamp: time.Now()}
	cs.ring[cs.head] = evt
	cs.head = (cs.head + 1) % cogLoadRingSize
	if cs.count < cogLoadRingSize {
		cs.count++
	}

	cs.totalIntrinsic += profile.Intrinsic
	cs.totalExtraneous += profile.Extraneous
	cs.totalGermane += profile.Germane
	cs.totalLoad += profile.TotalLoad
	cs.measurements++
	if surgery != nil && surgery.RemovedMsgs+surgery.CharsRemoved > 0 {
		cs.surgeries++
	}
}

// Stats returns aggregated load averages and surgery count.
func (cs *CogLoadStats) Stats() map[string]interface{} {
	cs.mu.Lock()
	defer cs.mu.Unlock()

	if cs.measurements == 0 {
		return map[string]interface{}{
			"measurements": 0,
			"surgeries":    0,
		}
	}
	n := float64(cs.measurements)
	return map[string]interface{}{
		"measurements":     cs.measurements,
		"surgeries":        cs.surgeries,
		"surgery_rate":     float64(cs.surgeries) / n,
		"avg_intrinsic":    cs.totalIntrinsic / n,
		"avg_extraneous":   cs.totalExtraneous / n,
		"avg_germane":      cs.totalGermane / n,
		"avg_total_load":   cs.totalLoad / n,
	}
}

// RecentEvents returns the last n load events from the ring.
func (cs *CogLoadStats) RecentEvents(n int) []LoadEvent {
	cs.mu.Lock()
	defer cs.mu.Unlock()
	if n > cs.count {
		n = cs.count
	}
	result := make([]LoadEvent, n)
	for i := 0; i < n; i++ {
		idx := (cs.head - 1 - i + cogLoadRingSize) % cogLoadRingSize
		result[i] = cs.ring[idx]
	}
	return result
}

// Flush persists aggregated stats to disk.
func (cs *CogLoadStats) Flush() {
	cs.mu.Lock()
	defer cs.mu.Unlock()
	cs.persist()
}

// ── persistence ───────────────────────────────────────────────────────────────

type cogLoadSnapshot struct {
	Measurements    int     `json:"measurements"`
	Surgeries       int     `json:"surgeries"`
	TotalIntrinsic  float64 `json:"total_intrinsic"`
	TotalExtraneous float64 `json:"total_extraneous"`
	TotalGermane    float64 `json:"total_germane"`
	TotalLoad       float64 `json:"total_load"`
}

func (cs *CogLoadStats) persist() {
	snap := cogLoadSnapshot{
		Measurements:    cs.measurements,
		Surgeries:       cs.surgeries,
		TotalIntrinsic:  cs.totalIntrinsic,
		TotalExtraneous: cs.totalExtraneous,
		TotalGermane:    cs.totalGermane,
		TotalLoad:       cs.totalLoad,
	}
	data, err := json.MarshalIndent(snap, "", "  ")
	if err != nil {
		return
	}
	if err := os.WriteFile(cs.filePath, data, 0644); err != nil {
		log.Printf("[CogLoadStats] persist error: %v", err)
	}
}

func (cs *CogLoadStats) load() {
	data, err := os.ReadFile(cs.filePath)
	if err != nil {
		return
	}
	var snap cogLoadSnapshot
	if err := json.Unmarshal(data, &snap); err != nil {
		return
	}
	cs.measurements = snap.Measurements
	cs.surgeries = snap.Surgeries
	cs.totalIntrinsic = snap.TotalIntrinsic
	cs.totalExtraneous = snap.TotalExtraneous
	cs.totalGermane = snap.TotalGermane
	cs.totalLoad = snap.TotalLoad
}
