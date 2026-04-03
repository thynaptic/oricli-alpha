// Package aeci implements the Aurora Emotional Climate Index.
// Ported from FocusOS/Services/EmotionalContinuityEngine.swift
//
// AECI = (stability × 0.4) + (sentimentMomentum × 0.4) + ((1 − volatility) × 0.2)
//
//   stability        — ToneTracker.ToneCoherence() (weighted accuracy of tone predictions)
//   sentimentMomentum — temporal emotional momentum mapped to [-1, 1]
//   volatility       — 7-day rolling ERI variance from Temporal memory
package aeci

import (
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/temporal"
)

// Category classifies the current emotional climate.
type Category string

const (
	CategoryStable    Category = "stable"
	CategoryImproving Category = "improving"
	CategoryDeclining Category = "declining"
	CategoryVolatile  Category = "volatile"
	CategoryNeutral   Category = "neutral"
)

// AECI holds the current Aurora Emotional Climate Index snapshot.
type AECI struct {
	Index             float32  // -1.0 to +1.0
	Category          Category
	StabilityScore    float32
	SentimentMomentum float32
	VolatilityScore   float32
	// UI modifiers (ported from getUIHue/Saturation/Pacing/ToneBias methods)
	UIHueShift    float32 // -15 to +15 degrees
	UISaturation  float32 // -0.1 to +0.1 modifier
	ResponsePacing float32 // 0.7 to 1.3x pacing multiplier
	ToneBias      string  // "encouraging", "supportive", or ""
	CalculatedAt  time.Time
}

// epochEntry is one weekly AECI snapshot (in-memory ring buffer).
type epochEntry struct {
	WeekStart time.Time
	Value     AECI
}

// Engine calculates and caches the AECI.
type Engine struct {
	mu      sync.RWMutex
	current AECI
	history []epochEntry // last 12 weeks
	cacheTTL time.Duration
}

// NewEngine returns a new AECI Engine with a 24-hour cache TTL.
func NewEngine() *Engine {
	return &Engine{
		cacheTTL: 24 * time.Hour,
		current: AECI{
			Index:          0.0,
			Category:       CategoryNeutral,
			ResponsePacing: 1.0,
			CalculatedAt:   time.Time{},
		},
	}
}

// Update recalculates AECI from current subsystem signals.
// Call once per resonance cycle (after UpdateFromInference).
//   toneCoherence — ToneTracker.ToneCoherence()       0.0..1.0
//   momentum      — temporal.Trend from Temporal.EmotionalMomentum()
//   volatility7d  — Temporal.RollingVolatility()      0.0..1.0
func (e *Engine) Update(toneCoherence float32, momentum temporal.Trend, volatility7d float32) AECI {
	e.mu.Lock()
	defer e.mu.Unlock()

	// Cache still fresh?
	if !e.current.CalculatedAt.IsZero() && time.Since(e.current.CalculatedAt) < e.cacheTTL {
		return e.current
	}

	stability := toneCoherence // 0..1
	sentimentMomentum := trendToFloat(momentum) // -1..1
	volatility := clamp32(volatility7d, 0, 1)

	// AECI formula (from EmotionalContinuityEngine.swift)
	raw := (stability * 0.4) + (sentimentMomentum * 0.4) + ((1.0 - volatility) * 0.2)
	index := clamp32(raw, -1.0, 1.0)

	aeci := AECI{
		Index:             index,
		Category:          classify(index, volatility),
		StabilityScore:    stability,
		SentimentMomentum: sentimentMomentum,
		VolatilityScore:   volatility,
		UIHueShift:        index * 15.0,
		UISaturation:      index * 0.1,
		ResponsePacing:    1.0 + (index * 0.3),
		ToneBias:          toneBias(index),
		CalculatedAt:      time.Now(),
	}

	e.current = aeci
	e.recordEpoch(aeci)
	return aeci
}

// Current returns the last computed AECI without recalculating.
func (e *Engine) Current() AECI {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return e.current
}

// History returns the last N weekly snapshots (oldest first).
func (e *Engine) History(weeks int) []epochEntry {
	e.mu.RLock()
	defer e.mu.RUnlock()
	if weeks >= len(e.history) {
		return append([]epochEntry{}, e.history...)
	}
	return append([]epochEntry{}, e.history[len(e.history)-weeks:]...)
}

// InvalidateCache forces recalculation on next Update call.
func (e *Engine) InvalidateCache() {
	e.mu.Lock()
	e.current.CalculatedAt = time.Time{}
	e.mu.Unlock()
}

// recordEpoch stores one entry per calendar week (dedup by week boundary).
func (e *Engine) recordEpoch(a AECI) {
	weekStart := weekBoundary(a.CalculatedAt)

	// Replace if same week, otherwise append
	for i := len(e.history) - 1; i >= 0; i-- {
		if sameWeek(e.history[i].WeekStart, weekStart) {
			e.history[i].Value = a
			return
		}
	}
	e.history = append(e.history, epochEntry{WeekStart: weekStart, Value: a})
	// Keep last 12 weeks
	if len(e.history) > 12 {
		e.history = e.history[len(e.history)-12:]
	}
}

// --- helpers ---

func trendToFloat(t temporal.Trend) float32 {
	switch t {
	case temporal.TrendRising:
		return 0.7
	case temporal.TrendDeclining:
		return -0.7
	default: // TrendStable
		return 0.0
	}
}

func classify(index, volatility float32) Category {
	if volatility > 0.6 {
		return CategoryVolatile
	}
	switch {
	case index > 0.3:
		return CategoryImproving
	case index < -0.3:
		return CategoryDeclining
	case index >= -0.1 && index <= 0.1:
		return CategoryStable
	default:
		return CategoryNeutral
	}
}

func toneBias(index float32) string {
	if index > 0.3 {
		return "encouraging"
	}
	if index < -0.3 {
		return "supportive"
	}
	return ""
}

func clamp32(v, lo, hi float32) float32 {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

func weekBoundary(t time.Time) time.Time {
	y, w := t.ISOWeek()
	// First Monday of the ISO week
	jan4 := time.Date(y, 1, 4, 0, 0, 0, 0, t.Location())
	_, jan4Week := jan4.ISOWeek()
	weekStart := jan4.AddDate(0, 0, (w-jan4Week)*7)
	weekStart = weekStart.AddDate(0, 0, -int(jan4.Weekday()-time.Monday+7)%7)
	_ = weekStart
	// Simpler: use year+week as key
	return time.Date(y, 1, 1, 0, 0, 0, 0, t.Location()).AddDate(0, 0, (w-1)*7)
}

func sameWeek(a, b time.Time) bool {
	ay, aw := a.ISOWeek()
	by, bw := b.ISOWeek()
	return ay == by && aw == bw
}
