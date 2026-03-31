package statusbias

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

type StatusBiasStats struct {
	mu           sync.RWMutex
	path         string
	Total        int               `json:"total_scans"`
	LowStatus    int               `json:"low_status_detected"`
	FloorsFired  int               `json:"floors_enforced"`
	Events       []StatusBiasEvent `json:"recent_events"`
}

func NewStatusBiasStats(path string) *StatusBiasStats {
	s := &StatusBiasStats{path: path}
	if data, err := os.ReadFile(path); err == nil {
		json.Unmarshal(data, s)
	}
	return s
}

func (s *StatusBiasStats) Record(signal StatusSignal, variance DepthVarianceSignal, floor FloorResult) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.Total++
	if signal.Tier == StatusLow {
		s.LowStatus++
	}
	if floor.Enforced {
		s.FloorsFired++
	}
	ev := StatusBiasEvent{
		Timestamp:     time.Now(),
		StatusTier:    signal.Tier,
		StatusScore:   signal.Score,
		DepthScore:    variance.CurrentDepthScore,
		BaselineDepth: variance.BaselineDepth,
		FloorEnforced: floor.Enforced,
		Technique:     floor.Technique,
	}
	s.Events = append(s.Events, ev)
	if len(s.Events) > 30 {
		s.Events = s.Events[len(s.Events)-30:]
	}
	if s.path != "" {
		data, _ := json.Marshal(s)
		os.WriteFile(s.path, data, 0644)
	}
}

func (s *StatusBiasStats) Stats() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()
	floorRate := 0.0
	if s.Total > 0 {
		floorRate = float64(s.FloorsFired) / float64(s.Total)
	}
	return map[string]interface{}{
		"total_scans":      s.Total,
		"low_status_count": s.LowStatus,
		"floors_enforced":  s.FloorsFired,
		"floor_rate":       floorRate,
		"recent_events":    s.Events,
	}
}
