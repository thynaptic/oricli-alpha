package interference

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

// InterferenceStats tracks Phase 28 cognitive interference activity.
type InterferenceStats struct {
	mu             sync.Mutex
	path           string
	TotalScanned   int            `json:"total_scanned"`
	ConflictsFound int            `json:"conflicts_found"`
	ByType         map[string]int `json:"by_type"`
	LastUpdated    time.Time      `json:"last_updated"`
}

func NewInterferenceStats(path string) *InterferenceStats {
	s := &InterferenceStats{path: path, ByType: make(map[string]int)}
	if data, err := os.ReadFile(path); err == nil {
		json.Unmarshal(data, s)
	}
	if s.ByType == nil {
		s.ByType = make(map[string]int)
	}
	return s
}

func (s *InterferenceStats) Record(r InterferenceReading) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.TotalScanned++
	if r.Detected {
		s.ConflictsFound++
		for _, c := range r.Conflicts {
			s.ByType[string(c.Type)]++
		}
	}
	s.LastUpdated = time.Now()
	s.save()
}

func (s *InterferenceStats) Stats() map[string]interface{} {
	s.mu.Lock()
	defer s.mu.Unlock()
	return map[string]interface{}{
		"total_scanned":   s.TotalScanned,
		"conflicts_found": s.ConflictsFound,
		"by_type":         s.ByType,
		"last_updated":    s.LastUpdated,
	}
}

func (s *InterferenceStats) save() {
	data, _ := json.MarshalIndent(s, "", "  ")
	os.WriteFile(s.path, data, 0644)
}
