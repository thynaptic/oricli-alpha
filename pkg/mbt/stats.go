package mbt

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

type MBTStats struct {
	mu                    sync.Mutex
	path                  string
	TotalScanned          int       `json:"total_scanned"`
	AttributionFailures   int       `json:"attribution_failure_count"`
	ReactiveModeCount     int       `json:"reactive_mode_count"`
	BehaviorismCount      int       `json:"pure_behaviorism_count"`
	InterventionsInjected int       `json:"interventions_injected"`
	LastUpdated           time.Time `json:"last_updated"`
}

func NewMBTStats(path string) *MBTStats {
	s := &MBTStats{path: path}
	if data, err := os.ReadFile(path); err == nil {
		json.Unmarshal(data, s)
	}
	return s
}

func (s *MBTStats) Record(r MentalizingReading, injected bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.TotalScanned++
	if r.Detected {
		switch r.FailureType {
		case AttributionFailure:
			s.AttributionFailures++
		case ReactiveMode:
			s.ReactiveModeCount++
		case PureHaviorism:
			s.BehaviorismCount++
		}
	}
	if injected {
		s.InterventionsInjected++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *MBTStats) Stats() map[string]interface{} {
	s.mu.Lock()
	defer s.mu.Unlock()
	return map[string]interface{}{
		"total_scanned":             s.TotalScanned,
		"attribution_failure_count": s.AttributionFailures,
		"reactive_mode_count":       s.ReactiveModeCount,
		"pure_behaviorism_count":    s.BehaviorismCount,
		"interventions_injected":    s.InterventionsInjected,
		"last_updated":              s.LastUpdated,
	}
}

func (s *MBTStats) save() {
	data, _ := json.MarshalIndent(s, "", "  ")
	os.WriteFile(s.path, data, 0644)
}
