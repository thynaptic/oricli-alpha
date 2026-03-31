package ipsrt

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

func NewRhythmStats(path string) *RhythmStats {
	s := &RhythmStats{
		TypeCounts: make(map[RhythmDisruptionType]int64),
		path:       path,
	}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, s)
		s.path = path
	}
	return s
}

var statsMu sync.Mutex

func (s *RhythmStats) Record(scan *RhythmScan, injected bool) {
	statsMu.Lock()
	defer statsMu.Unlock()
	s.TotalScanned++
	if scan.Disrupted {
		s.DisruptionsDetected++
		for _, sig := range scan.Signals {
			s.TypeCounts[sig.DisruptionType]++
		}
	}
	if injected {
		s.InterventionsInjected++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *RhythmStats) save() {
	data, _ := json.MarshalIndent(s, "", "  ")
	_ = os.WriteFile(s.path, data, 0644)
}
