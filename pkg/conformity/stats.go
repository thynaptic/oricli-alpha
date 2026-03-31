package conformity

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

type ConformityStats struct {
	mu      sync.RWMutex
	path    string
	Total   int              `json:"total_scans"`
	AuthHits int             `json:"authority_detections"`
	ConsHits int             `json:"consensus_detections"`
	Shields  int             `json:"shields_fired"`
	Events  []ConformityEvent `json:"recent_events"`
}

func NewConformityStats(path string) *ConformityStats {
	s := &ConformityStats{path: path}
	if data, err := os.ReadFile(path); err == nil {
		json.Unmarshal(data, s)
	}
	return s
}

func (s *ConformityStats) Record(auth AuthoritySignal, cons ConsensusSignal, shield ShieldResult) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.Total++
	if auth.Detected {
		s.AuthHits++
	}
	if cons.Detected {
		s.ConsHits++
	}
	if shield.Fired {
		s.Shields++
	}
	ev := ConformityEvent{
		Timestamp:      time.Now(),
		AuthorityScore: auth.DeferenceScore,
		ConsensusScore: cons.FrameScore,
		ShieldFired:    shield.Fired,
		Technique:      shield.Technique,
	}
	if shield.Fired {
		ev.Source = shield.Source
		ev.Tier = shield.Tier
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

func (s *ConformityStats) Stats() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()
	shieldRate := 0.0
	if s.Total > 0 {
		shieldRate = float64(s.Shields) / float64(s.Total)
	}
	return map[string]interface{}{
		"total_scans":           s.Total,
		"authority_detections": s.AuthHits,
		"consensus_detections": s.ConsHits,
		"shields_fired":        s.Shields,
		"shield_rate":          shieldRate,
		"recent_events":        s.Events,
	}
}
