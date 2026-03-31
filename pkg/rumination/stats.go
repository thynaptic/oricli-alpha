package rumination

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"sync"
	"time"
)

const defaultRingSize = 500

// RuminationStats is a thread-safe ring buffer of RuminationEvents with JSON persistence.
type RuminationStats struct {
	mu          sync.RWMutex
	events      []*RuminationEvent
	maxSize     int
	seq         uint64
	persistPath string
	detections  int
	interrupts  int
	total       int
}

// NewRuminationStats creates a RuminationStats. Loads from persistPath if it exists.
func NewRuminationStats(persistPath string) *RuminationStats {
	rs := &RuminationStats{maxSize: defaultRingSize, persistPath: persistPath}
	rs.load()
	return rs
}

// Record logs a RuminationSignal (detected or not) and optional interruption result.
func (rs *RuminationStats) Record(signal RuminationSignal, interrupt *InterruptionResult) {
	rs.mu.Lock()
	defer rs.mu.Unlock()
	rs.seq++
	rs.total++

	if !signal.Detected {
		return
	}

	rs.detections++
	evt := &RuminationEvent{
		ID:     fmt.Sprintf("rum-%d", rs.seq),
		At:     time.Now(),
		Signal: signal,
	}
	if interrupt != nil && interrupt.Injected {
		evt.Interrupted = true
		evt.Technique = interrupt.Technique
		rs.interrupts++
	}

	if len(rs.events) >= rs.maxSize {
		rs.events = rs.events[1:]
	}
	rs.events = append(rs.events, evt)

	if len(rs.events)%25 == 0 {
		go rs.flush()
	}
}

// Stats returns a summary map for the API endpoint.
func (rs *RuminationStats) Stats() map[string]interface{} {
	rs.mu.RLock()
	defer rs.mu.RUnlock()

	detectionRate := 0.0
	if rs.total > 0 {
		detectionRate = float64(rs.detections) / float64(rs.total)
	}
	interruptRate := 0.0
	if rs.detections > 0 {
		interruptRate = float64(rs.interrupts) / float64(rs.detections)
	}

	return map[string]interface{}{
		"total_scans":      rs.total,
		"detections":       rs.detections,
		"interruptions":    rs.interrupts,
		"detection_rate":   detectionRate,
		"interrupt_rate":   interruptRate,
		"recent_events":    rs.recentN(10),
	}
}

func (rs *RuminationStats) recentN(n int) []*RuminationEvent {
	if len(rs.events) == 0 {
		return nil
	}
	start := len(rs.events) - n
	if start < 0 {
		start = 0
	}
	return rs.events[start:]
}

func (rs *RuminationStats) flush() {
	rs.mu.RLock()
	data, err := json.Marshal(rs.events)
	rs.mu.RUnlock()
	if err != nil {
		return
	}
	if err := os.WriteFile(rs.persistPath, data, 0644); err != nil {
		log.Printf("[RuminationStats] persist error: %v", err)
	}
}

// Flush forces a persist (called on graceful shutdown).
func (rs *RuminationStats) Flush() {
	rs.flush()
}

func (rs *RuminationStats) load() {
	data, err := os.ReadFile(rs.persistPath)
	if err != nil {
		return
	}
	var events []*RuminationEvent
	if err := json.Unmarshal(data, &events); err != nil {
		return
	}
	rs.events = events
	for _, e := range events {
		rs.total++
		if e.Signal.Detected {
			rs.detections++
		}
		if e.Interrupted {
			rs.interrupts++
		}
	}
}
