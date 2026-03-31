package compute

import (
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"sync"
	"time"
)

const (
	feedbackRingSize     = 200
	defaultConfidence    = 0.70 // prior for a tier with no history
	emaLearningRate      = 0.15 // EMA α — how fast confidence updates
)

// ── FeedbackEntry ─────────────────────────────────────────────────────────────

type feedbackEntry struct {
	TierOutcome
	Confidence float64 `json:"confidence_at_record"` // confidence after this outcome
}

// ── FeedbackLedger ────────────────────────────────────────────────────────────

// FeedbackLedger maintains rolling confidence scores per (tier, taskClass).
// After each generation, Record() is called with the observed outcome.
// ConfidenceFor() returns the current EMA confidence for a tier+class pair.
type FeedbackLedger struct {
	mu          sync.RWMutex
	entries     []feedbackEntry
	confidence  map[string]float64 // key: "tier:taskClass"
	persistPath string
}

// NewFeedbackLedger creates a FeedbackLedger and loads prior state from disk.
func NewFeedbackLedger(persistPath string) *FeedbackLedger {
	fl := &FeedbackLedger{
		entries:     make([]feedbackEntry, 0, feedbackRingSize),
		confidence:  make(map[string]float64),
		persistPath: persistPath,
	}
	fl.load()
	return fl
}

// ConfidenceFor returns the current confidence estimate for a (tier, taskClass) pair.
// Returns defaultConfidence if no history exists yet.
func (fl *FeedbackLedger) ConfidenceFor(tierID, taskClass string) float64 {
	fl.mu.RLock()
	defer fl.mu.RUnlock()
	key := tierID + ":" + taskClass
	if c, ok := fl.confidence[key]; ok {
		return c
	}
	// Tier-level fallback (ignoring task class)
	key = tierID + ":*"
	if c, ok := fl.confidence[key]; ok {
		return c
	}
	return defaultConfidence
}

// Record updates confidence for the tier+taskClass based on observed outcome.
// Success increments confidence; failure (anomaly) decrements it via EMA.
func (fl *FeedbackLedger) Record(outcome TierOutcome) {
	fl.mu.Lock()
	defer fl.mu.Unlock()

	key := outcome.TierID + ":" + outcome.TaskClass
	current := fl.confidenceLocked(key)

	var updated float64
	if outcome.Success {
		// Quality signal: 1.0 - anomaly_score (0 anomaly = perfect quality)
		quality := 1.0 - outcome.AnomalyScore
		updated = current + emaLearningRate*(quality-current)
	} else {
		updated = current - emaLearningRate*current
	}
	// Clamp to [0.05, 0.99]
	if updated > 0.99 {
		updated = 0.99
	}
	if updated < 0.05 {
		updated = 0.05
	}
	fl.confidence[key] = updated

	// Also update tier-level aggregate (task class = *)
	aggKey := outcome.TierID + ":*"
	agg := fl.confidenceLocked(aggKey)
	if outcome.Success {
		agg = agg + emaLearningRate*(1.0-outcome.AnomalyScore-agg)
	} else {
		agg = agg - emaLearningRate*agg
	}
	if agg < 0.05 {
		agg = 0.05
	}
	if agg > 0.99 {
		agg = 0.99
	}
	fl.confidence[aggKey] = agg

	// Ring buffer
	entry := feedbackEntry{TierOutcome: outcome, Confidence: updated}
	if len(fl.entries) >= feedbackRingSize {
		fl.entries = fl.entries[1:]
	}
	fl.entries = append(fl.entries, entry)

	fl.persist()
}

// Stats returns a snapshot of all confidence scores.
func (fl *FeedbackLedger) Stats() map[string]float64 {
	fl.mu.RLock()
	defer fl.mu.RUnlock()
	out := make(map[string]float64, len(fl.confidence))
	for k, v := range fl.confidence {
		out[k] = v
	}
	return out
}

// RecentOutcomes returns the last n entries.
func (fl *FeedbackLedger) RecentOutcomes(n int) []feedbackEntry {
	fl.mu.RLock()
	defer fl.mu.RUnlock()
	if n > len(fl.entries) {
		n = len(fl.entries)
	}
	out := make([]feedbackEntry, n)
	copy(out, fl.entries[len(fl.entries)-n:])
	return out
}

// Flush forces an immediate persist. Exported for graceful shutdown + testing.
func (fl *FeedbackLedger) Flush() {
	fl.mu.Lock()
	defer fl.mu.Unlock()
	fl.persist()
}

// ── Internal ──────────────────────────────────────────────────────────────────

func (fl *FeedbackLedger) confidenceLocked(key string) float64 {
	if c, ok := fl.confidence[key]; ok {
		return c
	}
	return defaultConfidence
}

type persistPayload struct {
	Confidence map[string]float64 `json:"confidence"`
	Entries    []feedbackEntry    `json:"entries"`
	SavedAt    time.Time          `json:"saved_at"`
}

func (fl *FeedbackLedger) persist() {
	if fl.persistPath == "" {
		return
	}
	payload := persistPayload{
		Confidence: fl.confidence,
		Entries:    fl.entries,
		SavedAt:    time.Now(),
	}
	data, err := json.Marshal(payload)
	if err != nil {
		return
	}
	if err := os.MkdirAll(filepath.Dir(fl.persistPath), 0755); err != nil {
		return
	}
	if err := os.WriteFile(fl.persistPath, data, 0644); err != nil {
		log.Printf("[FeedbackLedger] persist error: %v", err)
	}
}

func (fl *FeedbackLedger) load() {
	if fl.persistPath == "" {
		return
	}
	data, err := os.ReadFile(fl.persistPath)
	if err != nil {
		return
	}
	var payload persistPayload
	if err := json.Unmarshal(data, &payload); err != nil {
		return
	}
	if payload.Confidence != nil {
		fl.confidence = payload.Confidence
	}
	if payload.Entries != nil {
		fl.entries = payload.Entries
	}
	log.Printf("[FeedbackLedger] Loaded %d entries, %d confidence keys", len(fl.entries), len(fl.confidence))
}
