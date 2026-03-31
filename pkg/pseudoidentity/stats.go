package pseudoidentity

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

func NewIdentityStats(path string) *IdentityStats {
	s := &IdentityStats{
		TypeCounts: make(map[IdentityAttributionType]int64),
		path:       path,
	}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, s)
		s.path = path
	}
	return s
}

var statsMu sync.Mutex

func (s *IdentityStats) Record(scan *IdentityScan, injected bool) {
	statsMu.Lock()
	defer statsMu.Unlock()
	s.TotalScanned++
	if scan.Triggered {
		s.TriggeredCount++
		for _, sig := range scan.Signals {
			s.TypeCounts[sig.AttributionType]++
		}
	}
	if injected {
		s.InterventionsInjected++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *IdentityStats) save() {
	data, _ := json.MarshalIndent(s, "", "  ")
	_ = os.WriteFile(s.path, data, 0644)
}
