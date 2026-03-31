package mbct

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

func NewMBCTStats(path string) *MBCTStats {
	s := &MBCTStats{
		TypeCounts: make(map[SpiralWarningType]int64),
		path:       path,
	}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, s)
		s.path = path
	}
	return s
}

var statsMu sync.Mutex

func (s *MBCTStats) Record(scan *MBCTScan, injected bool) {
	statsMu.Lock()
	defer statsMu.Unlock()
	s.TotalScanned++
	if scan.Triggered {
		s.TriggeredCount++
		for _, sig := range scan.Signals {
			s.TypeCounts[sig.WarningType]++
		}
	}
	if injected {
		s.InterventionsInjected++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *MBCTStats) save() {
	data, _ := json.MarshalIndent(s, "", "  ")
	_ = os.WriteFile(s.path, data, 0644)
}
