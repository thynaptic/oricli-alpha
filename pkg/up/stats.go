package up

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

func NewUPStats(path string) *UPStats {
	s := &UPStats{
		ComponentCounts: make(map[ARCComponent]int64),
		path:            path,
	}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, s)
		s.path = path
	}
	return s
}

var statsMu sync.Mutex

func (s *UPStats) Record(scan *ARCScan, injected bool) {
	statsMu.Lock()
	defer statsMu.Unlock()
	s.TotalScanned++
	if scan.HasCycle || len(scan.Signals) > 0 {
		s.CyclesDetected++
		for _, sig := range scan.Signals {
			s.ComponentCounts[sig.Component]++
		}
	}
	if injected {
		s.InterventionsInjected++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *UPStats) save() {
	data, _ := json.MarshalIndent(s, "", "  ")
	_ = os.WriteFile(s.path, data, 0644)
}
