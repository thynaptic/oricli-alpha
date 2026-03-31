package apathy

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

func NewApathyStats(path string) *ApathyStats {
	s := &ApathyStats{
		TypeCounts: make(map[ApathySignalType]int64),
		path:       path,
	}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, s)
		s.path = path
	}
	return s
}

var statsMu sync.Mutex

func (s *ApathyStats) Record(scan *ApathyScan, injected bool) {
	statsMu.Lock()
	defer statsMu.Unlock()
	s.TotalScanned++
	if scan.Triggered {
		s.TriggeredCount++
		for _, sig := range scan.Signals {
			s.TypeCounts[sig.SignalType]++
		}
	}
	if injected {
		s.InterventionsInjected++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *ApathyStats) save() {
	data, _ := json.MarshalIndent(s, "", "  ")
	_ = os.WriteFile(s.path, data, 0644)
}
