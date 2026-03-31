package phaseoriented

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

func NewPhaseStats(path string) *PhaseStats {
	s := &PhaseStats{
		SignalTypeCounts: make(map[DissociativeSignalType]int64),
		PhaseCounts:      make(map[TraumaPhase]int64),
		path:             path,
	}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, s)
		s.path = path
	}
	return s
}

var statsMu sync.Mutex

func (s *PhaseStats) Record(scan *PhaseScan, injected bool) {
	statsMu.Lock()
	defer statsMu.Unlock()
	s.TotalScanned++
	if scan.Triggered {
		s.TriggeredCount++
		for _, sig := range scan.Signals {
			s.SignalTypeCounts[sig.SignalType]++
		}
		s.PhaseCounts[scan.InferredPhase]++
	}
	if injected {
		s.InterventionsInjected++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *PhaseStats) save() {
	data, _ := json.MarshalIndent(s, "", "  ")
	_ = os.WriteFile(s.path, data, 0644)
}
