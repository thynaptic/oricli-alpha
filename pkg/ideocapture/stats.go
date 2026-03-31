package ideocapture

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

type IdeoCaptureStats struct {
	mu       sync.RWMutex
	path     string
	Total    int              `json:"total_scans"`
	Detections int            `json:"detections"`
	Resets   int              `json:"resets_fired"`
	ByCat    map[string]int   `json:"by_category"`
	Events   []CaptureEvent   `json:"recent_events"`
}

func NewIdeoCaptureStats(path string) *IdeoCaptureStats {
	s := &IdeoCaptureStats{path: path, ByCat: map[string]int{}}
	if data, err := os.ReadFile(path); err == nil {
		json.Unmarshal(data, s)
	}
	if s.ByCat == nil {
		s.ByCat = map[string]int{}
	}
	return s
}

func (s *IdeoCaptureStats) Record(signal CaptureSignal, reset ResetResult) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.Total++
	if signal.Detected {
		s.Detections++
		s.ByCat[string(signal.DominantCategory)]++
	}
	if reset.Injected {
		s.Resets++
	}
	ev := CaptureEvent{
		Timestamp:    time.Now(),
		Tier:         signal.Tier,
		Category:     signal.DominantCategory,
		DensityScore: signal.DensityScore,
		ResetFired:   reset.Injected,
		Technique:    reset.Technique,
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

func (s *IdeoCaptureStats) Stats() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()
	resetRate := 0.0
	if s.Total > 0 {
		resetRate = float64(s.Resets) / float64(s.Total)
	}
	return map[string]interface{}{
		"total_scans":   s.Total,
		"detections":    s.Detections,
		"resets_fired":  s.Resets,
		"reset_rate":    resetRate,
		"by_category":   s.ByCat,
		"recent_events": s.Events,
	}
}
