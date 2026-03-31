package hopecircuit

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"sync"
	"time"
)

// AgencyStats is a thread-safe ring buffer of AgencyEvents with JSON persistence.
type AgencyStats struct {
	mu          sync.RWMutex
	events      []*AgencyEvent
	maxSize     int
	seq         uint64
	persistPath string
	activations int
	total       int
}

// NewAgencyStats creates an AgencyStats. Loads from persistPath if it exists.
func NewAgencyStats(persistPath string) *AgencyStats {
	s := &AgencyStats{maxSize: 500, persistPath: persistPath}
	s.load()
	return s
}

// Record logs a HopeActivation (fired or not).
func (s *AgencyStats) Record(activation HopeActivation) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.seq++
	s.total++

	if !activation.Activated {
		return
	}

	s.activations++
	evt := &AgencyEvent{
		ID:         fmt.Sprintf("hc-%d", s.seq),
		At:         time.Now(),
		Activation: activation,
	}
	if len(s.events) >= s.maxSize {
		s.events = s.events[1:]
	}
	s.events = append(s.events, evt)

	if len(s.events)%25 == 0 {
		go s.flush()
	}
}

// Stats returns a summary map for the API endpoint.
func (s *AgencyStats) Stats() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()

	activationRate := 0.0
	if s.total > 0 {
		activationRate = float64(s.activations) / float64(s.total)
	}

	return map[string]interface{}{
		"total_checks":    s.total,
		"activations":     s.activations,
		"activation_rate": activationRate,
		"recent_events":   s.recentN(10),
	}
}

func (s *AgencyStats) recentN(n int) []*AgencyEvent {
	if len(s.events) == 0 {
		return nil
	}
	start := len(s.events) - n
	if start < 0 {
		start = 0
	}
	return s.events[start:]
}

func (s *AgencyStats) flush() {
	s.mu.RLock()
	data, err := json.Marshal(s.events)
	s.mu.RUnlock()
	if err != nil {
		return
	}
	if err := os.WriteFile(s.persistPath, data, 0644); err != nil {
		log.Printf("[AgencyStats] persist error: %v", err)
	}
}

// Flush forces a persist.
func (s *AgencyStats) Flush() { s.flush() }

func (s *AgencyStats) load() {
	data, err := os.ReadFile(s.persistPath)
	if err != nil {
		return
	}
	var events []*AgencyEvent
	if err := json.Unmarshal(data, &events); err != nil {
		return
	}
	s.events = events
	for _, e := range events {
		s.total++
		if e.Activation.Activated {
			s.activations++
		}
	}
}
