package logotherapy

import (
	"encoding/json"
	"os"
	"time"
)

func NewMeaningStats(path string) *MeaningStats {
	s := &MeaningStats{path: path, TypeCounts: map[MeaningSignalType]int64{}}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, s)
	}
	s.path = path
	return s
}

func (s *MeaningStats) Record(scan *MeaningScan, injected bool) {
	s.TotalScanned++
	if scan.Triggered {
		s.TriggeredCount++
	}
	for _, sig := range scan.Signals {
		s.TypeCounts[sig.SignalType]++
	}
	if injected {
		s.InterventionsInjected++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *MeaningStats) save() {
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return
	}
	_ = os.WriteFile(s.path, data, 0644)
}
