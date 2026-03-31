package socratic

import (
	"encoding/json"
	"os"
	"time"
)

func NewSocraticStats(path string) *SocraticStats {
	s := &SocraticStats{path: path, TypeCounts: map[SocraticSignalType]int64{}}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, s)
	}
	s.path = path
	return s
}

func (s *SocraticStats) Record(scan *SocraticScan, injected bool) {
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

func (s *SocraticStats) save() {
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return
	}
	_ = os.WriteFile(s.path, data, 0644)
}
