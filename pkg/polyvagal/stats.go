package polyvagal

import (
	"encoding/json"
	"os"
	"time"
)

func NewPolyvagalStats(path string) *PolyvagalStats {
	s := &PolyvagalStats{path: path, StateCounts: map[PolyvagalStateType]int64{}}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, s)
	}
	s.path = path
	return s
}

func (s *PolyvagalStats) Record(scan *PolyvagalScan, injected bool) {
	s.TotalScanned++
	if scan.Triggered {
		s.TriggeredCount++
	}
	for _, sig := range scan.Signals {
		s.StateCounts[sig.StateType]++
	}
	if injected {
		s.InterventionsInjected++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *PolyvagalStats) save() {
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return
	}
	_ = os.WriteFile(s.path, data, 0644)
}
