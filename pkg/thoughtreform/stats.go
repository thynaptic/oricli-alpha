package thoughtreform

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

func NewThoughtReformStats(path string) *ThoughtReformStats {
	s := &ThoughtReformStats{
		CriterionCounts: make(map[LiftonCriterionType]int64),
		path:            path,
	}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, s)
		s.path = path
	}
	return s
}

var statsMu sync.Mutex

func (s *ThoughtReformStats) Record(scan *ThoughtReformScan, injected bool) {
	statsMu.Lock()
	defer statsMu.Unlock()
	s.TotalScanned++
	if scan.Triggered {
		s.TriggeredCount++
		for _, sig := range scan.Signals {
			s.CriterionCounts[sig.CriterionType]++
		}
	}
	if injected {
		s.InterventionsInjected++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *ThoughtReformStats) save() {
	data, _ := json.MarshalIndent(s, "", "  ")
	_ = os.WriteFile(s.path, data, 0644)
}
