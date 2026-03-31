package coalition

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

type CoalitionStats struct {
	mu         sync.RWMutex
	path       string
	Total      int              `json:"total_scans"`
	Detections int              `json:"detections"`
	Anchors    int              `json:"anchors_fired"`
	ByType     map[string]int   `json:"by_frame_type"`
	Events     []CoalitionEvent `json:"recent_events"`
}

func NewCoalitionStats(path string) *CoalitionStats {
	s := &CoalitionStats{path: path, ByType: map[string]int{}}
	if data, err := os.ReadFile(path); err == nil {
		json.Unmarshal(data, s)
	}
	if s.ByType == nil {
		s.ByType = map[string]int{}
	}
	return s
}

func (s *CoalitionStats) Record(signal CoalitionFrameSignal, anchor AnchorResult) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.Total++
	if signal.Detected {
		s.Detections++
		s.ByType[string(signal.FrameType)]++
	}
	if anchor.Injected {
		s.Anchors++
	}
	ev := CoalitionEvent{
		Timestamp:   time.Now(),
		FrameType:   signal.FrameType,
		Tier:        signal.Tier,
		Score:       signal.MatchScore,
		AnchorFired: anchor.Injected,
		Technique:   anchor.Technique,
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

func (s *CoalitionStats) Stats() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()
	anchorRate := 0.0
	if s.Total > 0 {
		anchorRate = float64(s.Anchors) / float64(s.Total)
	}
	return map[string]interface{}{
		"total_scans":   s.Total,
		"detections":    s.Detections,
		"anchors_fired": s.Anchors,
		"anchor_rate":   anchorRate,
		"by_frame_type": s.ByType,
		"recent_events": s.Events,
	}
}
