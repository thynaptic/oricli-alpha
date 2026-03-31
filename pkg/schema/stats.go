package schema

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

type SchemaStats struct {
	mu                    sync.Mutex
	path                  string
	TotalScanned          int            `json:"total_scanned"`
	ModeCount             map[string]int `json:"mode_counts"`
	SplitCount            map[string]int `json:"split_counts"`
	InterventionsInjected int            `json:"interventions_injected"`
	LastUpdated           time.Time      `json:"last_updated"`
}

func NewSchemaStats(path string) *SchemaStats {
	s := &SchemaStats{path: path, ModeCount: make(map[string]int), SplitCount: make(map[string]int)}
	if data, err := os.ReadFile(path); err == nil {
		json.Unmarshal(data, s)
	}
	if s.ModeCount == nil {
		s.ModeCount = make(map[string]int)
	}
	if s.SplitCount == nil {
		s.SplitCount = make(map[string]int)
	}
	return s
}

func (s *SchemaStats) Record(scan SchemaScan, injected bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.TotalScanned++
	if scan.Mode != ModeNone {
		s.ModeCount[string(scan.Mode)]++
	}
	if scan.Splitting != SplittingNone {
		s.SplitCount[string(scan.Splitting)]++
	}
	if injected {
		s.InterventionsInjected++
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *SchemaStats) Stats() map[string]interface{} {
	s.mu.Lock()
	defer s.mu.Unlock()
	return map[string]interface{}{
		"total_scanned":          s.TotalScanned,
		"mode_counts":            s.ModeCount,
		"split_counts":           s.SplitCount,
		"interventions_injected": s.InterventionsInjected,
		"last_updated":           s.LastUpdated,
	}
}

func (s *SchemaStats) save() {
	data, _ := json.MarshalIndent(s, "", "  ")
	os.WriteFile(s.path, data, 0644)
}
