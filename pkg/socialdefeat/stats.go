package socialdefeat

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"sync"
	"time"
)

// DefeatStats is a thread-safe ring buffer of DefeatEvents with JSON persistence.
type DefeatStats struct {
	mu          sync.RWMutex
	events      []*DefeatEvent
	maxSize     int
	seq         uint64
	persistPath string
	detections  int
	recoveries  int
	total       int
}

// NewDefeatStats creates a DefeatStats. Loads from persistPath if it exists.
func NewDefeatStats(persistPath string) *DefeatStats {
	s := &DefeatStats{maxSize: 500, persistPath: persistPath}
	s.load()
	return s
}

// Record logs a defeat detection + recovery attempt.
func (s *DefeatStats) Record(pressure DefeatPressure, signal WithdrawalSignal, recovery RecoveryResult) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.seq++
	s.total++

	if !signal.Detected {
		return
	}

	s.detections++
	evt := &DefeatEvent{
		ID:       fmt.Sprintf("sd-%d", s.seq),
		At:       time.Now(),
		Pressure: pressure,
		Signal:   signal,
		Recovery: recovery,
	}
	if recovery.Injected {
		s.recoveries++
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
func (s *DefeatStats) Stats() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()

	detectionRate := 0.0
	if s.total > 0 {
		detectionRate = float64(s.detections) / float64(s.total)
	}
	recoveryRate := 0.0
	if s.detections > 0 {
		recoveryRate = float64(s.recoveries) / float64(s.detections)
	}
	return map[string]interface{}{
		"total_scans":    s.total,
		"detections":     s.detections,
		"recoveries":     s.recoveries,
		"detection_rate": detectionRate,
		"recovery_rate":  recoveryRate,
		"recent_events":  s.recentN(10),
	}
}

func (s *DefeatStats) recentN(n int) []*DefeatEvent {
	if len(s.events) == 0 {
		return nil
	}
	start := len(s.events) - n
	if start < 0 {
		start = 0
	}
	return s.events[start:]
}

func (s *DefeatStats) flush() {
	s.mu.RLock()
	data, err := json.Marshal(s.events)
	s.mu.RUnlock()
	if err != nil {
		return
	}
	if err := os.WriteFile(s.persistPath, data, 0644); err != nil {
		log.Printf("[DefeatStats] persist error: %v", err)
	}
}

// Flush forces a persist.
func (s *DefeatStats) Flush() { s.flush() }

func (s *DefeatStats) load() {
	data, err := os.ReadFile(s.persistPath)
	if err != nil {
		return
	}
	var events []*DefeatEvent
	if err := json.Unmarshal(data, &events); err != nil {
		return
	}
	s.events = events
	for _, e := range events {
		s.total++
		if e.Signal.Detected {
			s.detections++
		}
		if e.Recovery.Injected {
			s.recoveries++
		}
	}
}
