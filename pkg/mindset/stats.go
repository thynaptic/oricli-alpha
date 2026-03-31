package mindset

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"sync"
	"time"
)

// MindsetStats is a thread-safe ring buffer of MindsetEvents with JSON persistence.
type MindsetStats struct {
	mu          sync.RWMutex
	events      []*MindsetEvent
	maxSize     int
	seq         uint64
	persistPath string
	detections  int
	reframes    int
	total       int
}

// NewMindsetStats creates a MindsetStats. Loads from persistPath if it exists.
func NewMindsetStats(persistPath string) *MindsetStats {
	ms := &MindsetStats{maxSize: 500, persistPath: persistPath}
	ms.load()
	return ms
}

// Record logs a MindsetSignal + optional ReframeResult.
func (ms *MindsetStats) Record(signal MindsetSignal, reframe *ReframeResult) {
	ms.mu.Lock()
	defer ms.mu.Unlock()
	ms.seq++
	ms.total++

	if !signal.Detected {
		return
	}

	ms.detections++
	evt := &MindsetEvent{
		ID:     fmt.Sprintf("ms-%d", ms.seq),
		At:     time.Now(),
		Signal: signal,
	}
	if reframe != nil && reframe.Reframed {
		evt.Reframe = *reframe
		ms.reframes++
	}

	if len(ms.events) >= ms.maxSize {
		ms.events = ms.events[1:]
	}
	ms.events = append(ms.events, evt)

	if len(ms.events)%25 == 0 {
		go ms.flush()
	}
}

// Stats returns a summary map for the API endpoint.
func (ms *MindsetStats) Stats() map[string]interface{} {
	ms.mu.RLock()
	defer ms.mu.RUnlock()

	detectionRate := 0.0
	if ms.total > 0 {
		detectionRate = float64(ms.detections) / float64(ms.total)
	}
	reframeRate := 0.0
	if ms.detections > 0 {
		reframeRate = float64(ms.reframes) / float64(ms.detections)
	}

	return map[string]interface{}{
		"total_scans":     ms.total,
		"detections":      ms.detections,
		"reframes":        ms.reframes,
		"detection_rate":  detectionRate,
		"reframe_rate":    reframeRate,
		"recent_events":   ms.recentN(10),
	}
}

func (ms *MindsetStats) recentN(n int) []*MindsetEvent {
	if len(ms.events) == 0 {
		return nil
	}
	start := len(ms.events) - n
	if start < 0 {
		start = 0
	}
	return ms.events[start:]
}

func (ms *MindsetStats) flush() {
	ms.mu.RLock()
	data, err := json.Marshal(ms.events)
	ms.mu.RUnlock()
	if err != nil {
		return
	}
	if err := os.WriteFile(ms.persistPath, data, 0644); err != nil {
		log.Printf("[MindsetStats] persist error: %v", err)
	}
}

// Flush forces a persist.
func (ms *MindsetStats) Flush() {
	ms.flush()
}

func (ms *MindsetStats) load() {
	data, err := os.ReadFile(ms.persistPath)
	if err != nil {
		return
	}
	var events []*MindsetEvent
	if err := json.Unmarshal(data, &events); err != nil {
		return
	}
	ms.events = events
	for _, e := range events {
		ms.total++
		if e.Signal.Detected {
			ms.detections++
		}
		if e.Reframe.Reframed {
			ms.reframes++
		}
	}
}
