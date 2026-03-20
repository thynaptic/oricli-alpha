package memory

import (
	"math"
	"sort"
	"strings"
	"time"
)

// --- Pillar 11: Dynamic Recall Layer ---
// Ported from Aurora's AIRecallService.swift.
// Implements multi-factor ranking for sovereign memories.

type RecallMode string

const (
	ModeReflective  RecallMode = "reflective"
	ModeOperational RecallMode = "operational"
	ModeCreative    RecallMode = "creative"
)

type MemorySnippet struct {
	ID               string    `json:"id"`
	Content          string    `json:"content"`
	Type             string    `json:"type"` // e.g., "note", "action", "chat"
	Importance       float64   `json:"importance"`
	AccessCount      int       `json:"access_count"`
	LastViewedAt     time.Time `json:"last_viewed_at"`
	CreatedAt        time.Time `json:"created_at"`
	EmotionScore     float64   `json:"emotion_score"` // -1.0 to 1.0
	EmotionIntensity float64   `json:"emotion_intensity"` // 0.0 to 1.0
}

type RecallWeights struct {
	RecencyWeight   float64
	FrequencyWeight float64
	ImportanceWeight float64
	RecencyHalfLife float64 // in hours
}

var DefaultWeights = RecallWeights{
	RecencyWeight:   0.5,
	FrequencyWeight: 0.3,
	ImportanceWeight: 0.2,
	RecencyHalfLife: 36.0,
}

// ScoreSnippet calculates the relevance of a snippet based on Aurora's multi-factor math.
func ScoreSnippet(s *MemorySnippet, weights RecallWeights, mode RecallMode, now time.Time) float64 {
	// 1. Recency Score (Half-life decay)
	elapsed := now.Sub(s.LastViewedAt).Hours()
	recencyScore := math.Pow(0.5, elapsed/weights.RecencyHalfLife)

	// 2. Frequency Score (Normalized)
	frequencyScore := math.Min(1.0, float64(s.AccessCount)/10.0)

	// 3. Base Score
	baseScore := (weights.RecencyWeight * recencyScore) +
		(weights.FrequencyWeight * frequencyScore) +
		(weights.ImportanceWeight * s.Importance)

	// 4. Age Multiplier (Long-term decay)
	ageDays := now.Sub(s.CreatedAt).Hours() / 24.0
	ageMultiplier := math.Max(0.25, math.Exp(-ageDays/90.0))

	// 5. Emotional Multiplier
	emotionalMultiplier := 1.0
	if math.Abs(s.EmotionScore) > 0.6 || s.EmotionIntensity > 0.6 {
		emotionalMultiplier = 1.2
	} else if math.Abs(s.EmotionScore) > 0.3 || s.EmotionIntensity > 0.3 {
		emotionalMultiplier = 1.1
	}

	// 6. Mode Boost
	modeBoost := 0.0
	switch mode {
	case ModeReflective:
		if s.Type == "note" || emotionalMultiplier > 1.0 {
			modeBoost = 0.15
		}
	case ModeOperational:
		if s.Type == "action" || s.Importance > 0.7 {
			modeBoost = 0.1
		}
	case ModeCreative:
		if len(s.Content) > 200 { // Rich content
			modeBoost = 0.12
		}
	}

	finalScore := baseScore * ageMultiplier * emotionalMultiplier + modeBoost
	return math.Max(0.0, math.Min(1.0, finalScore))
}

// RankMemories filters and sorts snippets based on the query and current mode.
func RankMemories(query string, snippets []MemorySnippet, mode RecallMode, limit int) []MemorySnippet {
	now := time.Now()
	type scoredSnippet struct {
		snippet MemorySnippet
		score   float64
	}

	var scored []scoredSnippet
	lowerQuery := strings.ToLower(query)

	for _, s := range snippets {
		// Basic keyword match (Ported from Swift matches)
		if lowerQuery != "" && !strings.Contains(strings.ToLower(s.Content), lowerQuery) {
			continue
		}

		score := ScoreSnippet(&s, DefaultWeights, mode, now)
		scored = append(scored, scoredSnippet{s, score})
	}

	// Sort by score descending
	sort.Slice(scored, func(i, j int) bool {
		return scored[i].score > scored[j].score
	})

	// Truncate to limit
	if len(scored) > limit {
		scored = scored[:limit]
	}

	var results []MemorySnippet
	for _, ss := range scored {
		results = append(results, ss.snippet)
	}
	return results
}
