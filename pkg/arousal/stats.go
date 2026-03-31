package arousal

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

// ArousalStats tracks Phase 27 arousal optimizer activity.
type ArousalStats struct {
	mu           sync.Mutex
	path         string
	UnderCount   int       `json:"under_count"`
	OptimalCount int       `json:"optimal_count"`
	OverCount    int       `json:"over_count"`
	EvalThreat   int       `json:"evaluative_threat_count"`
	TotalMeasured int      `json:"total_measured"`
	LastUpdated  time.Time `json:"last_updated"`
}

func NewArousalStats(path string) *ArousalStats {
	s := &ArousalStats{path: path}
	if data, err := os.ReadFile(path); err == nil {
		json.Unmarshal(data, s)
	}
	return s
}

func (s *ArousalStats) Record(r ArousalReading) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.TotalMeasured++
	switch r.Tier {
	case TierUnder:
		s.UnderCount++
	case TierOptimal:
		s.OptimalCount++
	case TierOver:
		s.OverCount++
	}
	if r.EvaluativeThreat {
		s.EvalThreat++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *ArousalStats) Stats() map[string]interface{} {
	s.mu.Lock()
	defer s.mu.Unlock()
	return map[string]interface{}{
		"total_measured":          s.TotalMeasured,
		"under_count":             s.UnderCount,
		"optimal_count":           s.OptimalCount,
		"over_count":              s.OverCount,
		"evaluative_threat_count": s.EvalThreat,
		"last_updated":            s.LastUpdated,
	}
}

func (s *ArousalStats) save() {
	data, _ := json.MarshalIndent(s, "", "  ")
	os.WriteFile(s.path, data, 0644)
}
