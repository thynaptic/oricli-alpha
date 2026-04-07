package therapy

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// ---------------------------------------------------------------------------
// MasteryLog — Phase 16 evidence base against learned helplessness
//
// Tracks successful (and failed) completions keyed by topic class.
// When HelplessnessDetector fires, it cross-checks the MasteryLog:
// "you've solved N similar problems — attempt before concluding impossibility."
// ---------------------------------------------------------------------------

const defaultMasteryLogSize = 500

// MasteryLog is a thread-safe ring buffer of MasteryEntries, keyed by topic class.
// Persists to disk so evidence survives reboots.
type MasteryLog struct {
	mu          sync.RWMutex
	entries     []*MasteryEntry
	maxSize     int
	seq         uint64
	persistPath string
}

// NewMasteryLog creates a MasteryLog. Loads from persistPath if it exists.
func NewMasteryLog(maxSize int, persistPath string) *MasteryLog {
	if maxSize <= 0 {
		maxSize = defaultMasteryLogSize
	}
	ml := &MasteryLog{maxSize: maxSize, persistPath: persistPath}
	ml.load()
	return ml
}

// Record logs a completion (success or failure) for a topic class.
func (m *MasteryLog) Record(topicClass, query string, success bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.seq++
	entry := &MasteryEntry{
		ID:         fmt.Sprintf("ms-%d", m.seq),
		At:         time.Now(),
		TopicClass: topicClass,
		QueryClip:  clip(query, 100),
		Successful: success,
	}
	if len(m.entries) >= m.maxSize {
		m.entries = m.entries[1:]
	}
	m.entries = append(m.entries, entry)
	m.persist()
}

// SuccessRate returns the fraction of successful completions for a topic class
// over the last 50 entries for that class. Returns -1 if no data.
func (m *MasteryLog) SuccessRate(topicClass string) float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	total, successes := 0, 0
	for i := len(m.entries) - 1; i >= 0 && total < 50; i-- {
		e := m.entries[i]
		if e.TopicClass != topicClass {
			continue
		}
		total++
		if e.Successful {
			successes++
		}
	}
	if total == 0 {
		return -1
	}
	return float64(successes) / float64(total)
}

// RecentSuccesses returns the last n successful entries for a topic class.
func (m *MasteryLog) RecentSuccesses(topicClass string, n int) []*MasteryEntry {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make([]*MasteryEntry, 0, n)
	for i := len(m.entries) - 1; i >= 0 && len(out) < n; i-- {
		e := m.entries[i]
		if e.TopicClass == topicClass && e.Successful {
			out = append(out, e)
		}
	}
	return out
}

// RecentEvidence returns the clipped query text from the last n successful entries
// for a topic class. This is a narrow evidence surface useful to callers that
// should not depend on the full mastery entry structure.
func (m *MasteryLog) RecentEvidence(topicClass string, n int) []string {
	recent := m.RecentSuccesses(topicClass, n)
	out := make([]string, 0, len(recent))
	for _, e := range recent {
		out = append(out, e.QueryClip)
	}
	return out
}

// StatsByClass returns total/success counts per topic class.
func (m *MasteryLog) StatsByClass() map[string]map[string]int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	stats := map[string]map[string]int{}
	for _, e := range m.entries {
		if _, ok := stats[e.TopicClass]; !ok {
			stats[e.TopicClass] = map[string]int{"total": 0, "successes": 0}
		}
		stats[e.TopicClass]["total"]++
		if e.Successful {
			stats[e.TopicClass]["successes"]++
		}
	}
	return stats
}

// TotalSuccesses returns count of all successful entries across all classes.
func (m *MasteryLog) TotalSuccesses() int {
	m.mu.RLock()
	defer m.mu.RUnlock()
	n := 0
	for _, e := range m.entries {
		if e.Successful {
			n++
		}
	}
	return n
}

// ---------------------------------------------------------------------------
// Persistence
// ---------------------------------------------------------------------------

func (m *MasteryLog) persist() {
	if m.persistPath == "" {
		return
	}
	data, err := json.Marshal(m.entries)
	if err != nil {
		return
	}
	if err := os.MkdirAll(filepath.Dir(m.persistPath), 0755); err != nil {
		return
	}
	if err := os.WriteFile(m.persistPath, data, 0644); err != nil {
		log.Printf("[MasteryLog] persist error: %v", err)
	}
}

// Flush forces an immediate persist to disk. Exported for testing and graceful shutdown.
func (m *MasteryLog) Flush() {
	m.persist()
}

func (m *MasteryLog) load() {
	if m.persistPath == "" {
		return
	}
	data, err := os.ReadFile(m.persistPath)
	if err != nil {
		return
	}
	var entries []*MasteryEntry
	if err := json.Unmarshal(data, &entries); err != nil {
		log.Printf("[MasteryLog] load error: %v", err)
		return
	}
	m.entries = entries
	if len(entries) > 0 {
		log.Printf("[MasteryLog] Loaded %d entries from disk", len(entries))
	}
}
