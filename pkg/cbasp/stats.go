package cbasp

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

func NewCBASPStats(path string) *CBASPStats {
	s := &CBASPStats{
		TypeCounts: make(map[DisconnectionType]int64),
		path:       path,
	}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, s)
		s.path = path
	}
	return s
}

var statsMu sync.Mutex

func (s *CBASPStats) Record(scan *CBASPScan, injected bool) {
	statsMu.Lock()
	defer statsMu.Unlock()
	s.TotalScanned++
	if scan.Triggered {
		s.TriggeredCount++
		for _, sig := range scan.Signals {
			s.TypeCounts[sig.DisconnectionType]++
		}
	}
	if injected {
		s.InterventionsInjected++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *CBASPStats) save() {
	data, _ := json.MarshalIndent(s, "", "  ")
	_ = os.WriteFile(s.path, data, 0644)
}
