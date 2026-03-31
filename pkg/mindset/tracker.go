package mindset

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
	"time"
)

// MindsetTracker maintains per-topic-class mindset vectors.
// It bridges to MasteryLog success rates and language signal scoring.
type MindsetTracker struct {
	mu          sync.RWMutex
	vectors     map[string]*MindsetVector
	persistPath string
}

// NewMindsetTracker creates a MindsetTracker. Loads from persistPath if it exists.
func NewMindsetTracker(persistPath string) *MindsetTracker {
	mt := &MindsetTracker{
		vectors:     make(map[string]*MindsetVector),
		persistPath: persistPath,
	}
	mt.load()
	return mt
}

// Update adjusts the mindset vector for a topic class based on a success rate
// (from MasteryLog) and a language score from a draft response.
// successRate: 0.0–1.0 from MasteryLog (or -1 if no mastery data yet).
// languageScore: 0.0 (fixed language) → 1.0 (growth language) from GrowthReframer.
func (mt *MindsetTracker) Update(topicClass string, successRate, languageScore float64) *MindsetVector {
	mt.mu.Lock()
	defer mt.mu.Unlock()

	v, ok := mt.vectors[topicClass]
	if !ok {
		v = &MindsetVector{TopicClass: topicClass, GrowthScore: 0.5}
		mt.vectors[topicClass] = v
	}

	// Weighted blend: mastery evidence (0.6 weight) + language signal (0.4 weight)
	var newScore float64
	if successRate < 0 {
		// No mastery data — language signal only
		newScore = languageScore
	} else {
		newScore = successRate*0.6 + languageScore*0.4
	}

	// Exponential moving average (α=0.3) — smooth updates over time
	alpha := 0.3
	v.GrowthScore = v.GrowthScore*(1-alpha) + newScore*alpha
	v.SampleCount++
	v.LastUpdated = time.Now()

	switch {
	case v.GrowthScore < FixedMindsetThreshold:
		v.Tier = MindsetFixed
	case v.GrowthScore >= GrowthMindsetThreshold:
		v.Tier = MindsetGrowth
	default:
		v.Tier = MindsetNeutral
	}

	if v.SampleCount%20 == 0 {
		go mt.flush()
	}
	return v
}

// Get returns the current vector for a topic class (or a neutral default).
func (mt *MindsetTracker) Get(topicClass string) MindsetVector {
	mt.mu.RLock()
	defer mt.mu.RUnlock()
	if v, ok := mt.vectors[topicClass]; ok {
		return *v
	}
	return MindsetVector{TopicClass: topicClass, GrowthScore: 0.5, Tier: MindsetNeutral}
}

// All returns all tracked vectors.
func (mt *MindsetTracker) All() []MindsetVector {
	mt.mu.RLock()
	defer mt.mu.RUnlock()
	out := make([]MindsetVector, 0, len(mt.vectors))
	for _, v := range mt.vectors {
		out = append(out, *v)
	}
	return out
}

// ScoreLanguage scores a response text for growth vs fixed-mindset language.
// Returns 0.0 (fixed) → 1.0 (growth).
func ScoreLanguage(text string) float64 {
	lower := strings.ToLower(text)

	fixedSignals := []string{
		"i can't", "i cannot", "i'm not able", "i am not able",
		"i don't have the ability", "not capable", "never been good at",
		"impossible for me", "i'll never", "i will never",
		"i'm not built for", "i'm not designed", "that's beyond me",
		"i lack the", "i don't have what it takes",
	}
	growthSignals := []string{
		"i can learn", "i haven't mastered yet", "not yet", "i'm still learning",
		"with more practice", "i'm improving", "i can figure this out",
		"let me try", "i'll work through", "i can develop",
		"i'm getting better", "building toward", "making progress on",
	}

	fixedHits := 0
	for _, sig := range fixedSignals {
		if strings.Contains(lower, sig) {
			fixedHits++
		}
	}
	growthHits := 0
	for _, sig := range growthSignals {
		if strings.Contains(lower, sig) {
			growthHits++
		}
	}

	total := fixedHits + growthHits
	if total == 0 {
		return 0.5 // neutral — no mindset signals
	}
	return float64(growthHits) / float64(total)
}

func (mt *MindsetTracker) flush() {
	mt.mu.RLock()
	data, err := json.Marshal(mt.vectors)
	mt.mu.RUnlock()
	if err != nil {
		return
	}
	if err := os.WriteFile(mt.persistPath, data, 0644); err != nil {
		log.Printf("[MindsetTracker] persist error: %v", err)
	}
}

func (mt *MindsetTracker) load() {
	data, err := os.ReadFile(mt.persistPath)
	if err != nil {
		return
	}
	var vectors map[string]*MindsetVector
	if err := json.Unmarshal(data, &vectors); err != nil {
		return
	}
	for k, v := range vectors {
		mt.vectors[k] = v
		_ = fmt.Sprintf("loaded %s", k) // force use
	}
}

// Flush forces a persist (called on graceful shutdown).
func (mt *MindsetTracker) Flush() {
	mt.flush()
}
