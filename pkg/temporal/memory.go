// Package temporal implements the Temporal Emotional Memory system —
// ported from Aurora's TemporalEmotionalMemory.swift.
//
// Maintains a rolling ring buffer of ERI snapshots and computes weighted
// baselines that let Ori know if her current state is "normal" or drifting
// from her own historical pattern.
package temporal

import (
	"math"
	"sync"
	"time"
)

// Trend is the direction of Ori's emotional momentum over time.
type Trend string

const (
	TrendRising   Trend = "rising"
	TrendStable   Trend = "stable"
	TrendDeclining Trend = "declining"
)

// Snapshot is a single ERI sample recorded at a point in time.
type Snapshot struct {
	ERI       float32
	ARTEScore float32
	RecordedAt time.Time
}

// Baseline is the computed temporal context from the ring buffer.
type Baseline struct {
	SevenDay   float32 // Weighted avg ERI over last 7 days
	ThirtyDay  float32 // Weighted avg ERI over last 30 days
	Volatility float32 // Rolling variance (0.0-1.0)
	Momentum   Trend   // Rising / stable / declining
	Confidence float32 // 0.0-1.0 — how many samples back this
}

const (
	maxSnapshots = 500         // ~1 snapshot/min × 8h/day × 7 days comfortably
	sevenDays    = 7 * 24 * time.Hour
	thirtyDays   = 30 * 24 * time.Hour
)

// Memory is the thread-safe temporal ERI store.
type Memory struct {
	mu        sync.RWMutex
	snapshots []Snapshot
}

// NewMemory returns an initialized Memory.
func NewMemory() *Memory {
	return &Memory{}
}

// Record adds an ERI snapshot to the ring buffer.
func (m *Memory) Record(eri, arteScore float32) {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.snapshots = append(m.snapshots, Snapshot{
		ERI:        eri,
		ARTEScore:  arteScore,
		RecordedAt: time.Now(),
	})
	if len(m.snapshots) > maxSnapshots {
		m.snapshots = m.snapshots[len(m.snapshots)-maxSnapshots:]
	}
}

// Compute returns the current Baseline from all stored snapshots.
func (m *Memory) Compute() Baseline {
	m.mu.RLock()
	defer m.mu.RUnlock()

	now := time.Now()
	sevenCutoff := now.Add(-sevenDays)
	thirtyCutoff := now.Add(-thirtyDays)

	var (
		sevenSum, sevenWeight   float64
		thirtySum, thirtyWeight float64
		values7                 []float64
	)

	for i, s := range m.snapshots {
		age := now.Sub(s.RecordedAt)
		if age > thirtyDays {
			continue
		}

		// Recency weight: newer = heavier (linear from 0 to 1 over window)
		recency := 1.0 - age.Seconds()/thirtyDays.Seconds()
		// Position weight: later in buffer = slightly more trusted (more settled)
		position := float64(i+1) / float64(len(m.snapshots))
		w := recency * position

		val := float64(s.ERI)
		thirtySum += val * w
		thirtyWeight += w

		if s.RecordedAt.After(sevenCutoff) {
			sevenSum += val * w
			sevenWeight += w
			values7 = append(values7, val)
		}
	}

	seven := float32(0.5)
	if sevenWeight > 0 {
		seven = float32(sevenSum / sevenWeight)
	}

	thirty := float32(0.5)
	if thirtyWeight > 0 {
		thirty = float32(thirtySum / thirtyWeight)
	}

	volatility := rollingVariance(values7)
	momentum := computeTrend(m.snapshots, sevenCutoff, thirtyCutoff)
	confidence := math.Min(1.0, float64(len(values7))/50.0) // full confidence at 50+ samples

	return Baseline{
		SevenDay:   seven,
		ThirtyDay:  thirty,
		Volatility: volatility,
		Momentum:   momentum,
		Confidence: float32(confidence),
	}
}

// rollingVariance returns normalized variance (0.0-1.0) of a slice.
func rollingVariance(vals []float64) float32 {
	if len(vals) < 2 {
		return 0
	}
	var sum float64
	for _, v := range vals {
		sum += v
	}
	mean := sum / float64(len(vals))
	var variance float64
	for _, v := range vals {
		d := v - mean
		variance += d * d
	}
	variance /= float64(len(vals))
	// Normalize: max realistic ERI variance is ~0.25 (±0.5 swing)
	return float32(math.Min(1.0, variance/0.25))
}

// computeTrend compares the 7-day window mean to the 30-day mean.
// Rising: recent avg is meaningfully above historical.
func computeTrend(snaps []Snapshot, sevenCutoff, thirtyCutoff time.Time) Trend {
	var recentVals, olderVals []float64
	for _, s := range snaps {
		if s.RecordedAt.After(sevenCutoff) {
			recentVals = append(recentVals, float64(s.ERI))
		} else if s.RecordedAt.After(thirtyCutoff) {
			olderVals = append(olderVals, float64(s.ERI))
		}
	}
	if len(recentVals) < 3 || len(olderVals) < 3 {
		return TrendStable
	}
	recentMean := mean(recentVals)
	olderMean := mean(olderVals)
	delta := recentMean - olderMean
	if delta > 0.08 {
		return TrendRising
	}
	if delta < -0.08 {
		return TrendDeclining
	}
	return TrendStable
}

func mean(vals []float64) float64 {
	if len(vals) == 0 {
		return 0
	}
	var s float64
	for _, v := range vals {
		s += v
	}
	return s / float64(len(vals))
}
