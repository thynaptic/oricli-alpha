// Package tonetrack implements the Tone Forecast + Accuracy Loop —
// ported from Aurora's ToneForecastService.swift / ToneForecastMetrics.swift.
//
// Before each response Ori "predicts" her tone (from ARTE state).
// After the response completes, the actual ARTE state is recorded.
// Accuracy is tracked per tone in a ring buffer and fed back into ERI
// as the toneCoherence node — closing the self-improvement loop.
package tonetrack

import (
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/arte"
)

// Tone is Aurora's response tone taxonomy — maps to ARTE states.
// Direct port of AuroraTone enum from Swift.
type Tone string

const (
	ToneClear      Tone = "clear"      // Direct, precise — ARTE: Focused
	ToneEnergetic  Tone = "energetic"  // High energy — ARTE: Energized
	ToneReflective Tone = "reflective" // Thoughtful — ARTE: Reflective
	ToneCalm       Tone = "calm"       // Balanced — ARTE: Calm
	ToneSteadying  Tone = "steadying"  // Grounding — ARTE: Fatigued (recovery)
)

// Sentiment of the interaction outcome (mirrors OutcomeSentiment.swift).
type Sentiment string

const (
	SentimentPositive Sentiment = "positive"
	SentimentNeutral  Sentiment = "neutral"
	SentimentNegative Sentiment = "negative"
)

// Sample is one prediction → actual outcome record.
type Sample struct {
	Predicted  Tone
	Actual     Tone
	Sentiment  Sentiment
	Confidence float32
	Accurate   bool
	RecordedAt time.Time
}

const maxSamples = 50 // 50-sample ring buffer per tone (matches Aurora's 30-day lookback)

// Tracker records tone predictions and measures accuracy over time.
// Thread-safe.
type Tracker struct {
	mu      sync.RWMutex
	samples []Sample

	// pendingPrediction holds the pre-response prediction until confirmed
	pendingPrediction *Tone
	pendingConf       float32
	pendingAt         time.Time
}

// NewTracker returns a ready Tracker.
func NewTracker() *Tracker {
	return &Tracker{}
}

// Predict records Ori's tone prediction before a response begins.
// Called from sovereign pipeline just before generation starts.
func (t *Tracker) Predict(state arte.ARTEState, confidence float32) {
	t.mu.Lock()
	defer t.mu.Unlock()
	tone := arteToTone(state)
	t.pendingPrediction = &tone
	t.pendingConf = confidence
	t.pendingAt = time.Now()
}

// Confirm records the actual tone after response completes.
// sentiment: inferred from user reaction (positive/neutral/negative).
// Called from sovereign pipeline after generation ends.
func (t *Tracker) Confirm(actualState arte.ARTEState, sentiment Sentiment) {
	t.mu.Lock()
	defer t.mu.Unlock()

	if t.pendingPrediction == nil {
		return
	}
	// Stale prediction (>2 min) — discard
	if time.Since(t.pendingAt) > 2*time.Minute {
		t.pendingPrediction = nil
		return
	}

	actual := arteToTone(actualState)
	s := Sample{
		Predicted:  *t.pendingPrediction,
		Actual:     actual,
		Sentiment:  sentiment,
		Confidence: t.pendingConf,
		Accurate:   *t.pendingPrediction == actual,
		RecordedAt: time.Now(),
	}

	t.samples = append(t.samples, s)
	if len(t.samples) > maxSamples {
		t.samples = t.samples[len(t.samples)-maxSamples:]
	}
	t.pendingPrediction = nil
}

// ToneCoherence returns a 0.0-1.0 accuracy score suitable for use as
// the toneCoherence node in the 4-node ERI formula.
// Higher = Ori is reliably predicting her own tone.
func (t *Tracker) ToneCoherence() float32 {
	t.mu.RLock()
	defer t.mu.RUnlock()

	if len(t.samples) == 0 {
		return 0.7 // optimistic cold-start default (Aurora used 0.5, but we trust Ori)
	}

	var weightedScore, totalWeight float64
	for i, s := range t.samples {
		// Recency weight — later samples matter more
		w := float64(i+1) / float64(len(t.samples))
		// Sentiment weight — positive outcomes count more
		switch s.Sentiment {
		case SentimentPositive:
			w *= 1.2
		case SentimentNegative:
			w *= 0.8
		}
		if s.Accurate {
			weightedScore += w
		}
		totalWeight += w
	}

	if totalWeight == 0 {
		return 0.7
	}
	score := float32(weightedScore / totalWeight)
	if score > 1.0 {
		score = 1.0
	}
	return score
}

// AccuracyByTone returns per-tone accuracy scores for diagnostics.
func (t *Tracker) AccuracyByTone() map[Tone]float32 {
	t.mu.RLock()
	defer t.mu.RUnlock()

	hits := map[Tone]int{}
	total := map[Tone]int{}
	for _, s := range t.samples {
		total[s.Predicted]++
		if s.Accurate {
			hits[s.Predicted]++
		}
	}

	out := map[Tone]float32{}
	for tone, n := range total {
		out[tone] = float32(hits[tone]) / float32(n)
	}
	return out
}

// SampleCount returns how many samples are stored (for confidence display).
func (t *Tracker) SampleCount() int {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return len(t.samples)
}

// arteToTone maps an ARTE cognitive state to its Aurora tone equivalent.
func arteToTone(state arte.ARTEState) Tone {
	switch state {
	case arte.StateFocused:
		return ToneClear
	case arte.StateEnergized:
		return ToneEnergetic
	case arte.StateReflective:
		return ToneReflective
	case arte.StateFatigued:
		return ToneSteadying
	default:
		return ToneCalm
	}
}
