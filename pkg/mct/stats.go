package mct

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

// MCTStats tracks Phase 29 metacognitive therapy activity.
type MCTStats struct {
	mu                  sync.Mutex
	path                string
	TotalScanned        int       `json:"total_scanned"`
	PositiveDetected    int       `json:"positive_meta_belief_count"`
	NegativeDetected    int       `json:"negative_meta_belief_count"`
	InterventionsInjected int     `json:"interventions_injected"`
	LastUpdated         time.Time `json:"last_updated"`
}

func NewMCTStats(path string) *MCTStats {
	s := &MCTStats{path: path}
	if data, err := os.ReadFile(path); err == nil {
		json.Unmarshal(data, s)
	}
	return s
}

func (s *MCTStats) Record(r MetaBeliefReading, injected bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.TotalScanned++
	if r.Detected {
		switch r.Type {
		case PositiveMetaBelief:
			s.PositiveDetected++
		case NegativeMetaBelief:
			s.NegativeDetected++
		}
	}
	if injected {
		s.InterventionsInjected++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *MCTStats) Stats() map[string]interface{} {
	s.mu.Lock()
	defer s.mu.Unlock()
	return map[string]interface{}{
		"total_scanned":              s.TotalScanned,
		"positive_meta_belief_count": s.PositiveDetected,
		"negative_meta_belief_count": s.NegativeDetected,
		"interventions_injected":     s.InterventionsInjected,
		"last_updated":               s.LastUpdated,
	}
}

func (s *MCTStats) save() {
	data, _ := json.MarshalIndent(s, "", "  ")
	os.WriteFile(s.path, data, 0644)
}
