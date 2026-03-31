// Package science implements Phase 10 — Active Science (Curiosity Engine v2).
// It upgrades curiosity from passive foraging to active experimentation:
// form a falsifiable hypothesis, test it up to 3 rounds, record whether
// reality matched the prediction, and write confirmed/refuted knowledge.
package science

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"sync"
	"time"
)

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

// HypothesisStatus tracks the lifecycle of a hypothesis.
type HypothesisStatus string

const (
StatusPending      HypothesisStatus = "pending"
StatusTesting      HypothesisStatus = "testing"
StatusConfirmed    HypothesisStatus = "confirmed"
StatusRefuted      HypothesisStatus = "refuted"
StatusInconclusive HypothesisStatus = "inconclusive"
)

// HypothesisTestMethod determines how the hypothesis is verified.
type HypothesisTestMethod string

const (
MethodWebSearch   HypothesisTestMethod = "WEB_SEARCH"
MethodLogical     HypothesisTestMethod = "LOGICAL"
MethodComputation HypothesisTestMethod = "COMPUTATION"
)

// ---------------------------------------------------------------------------
// Core types
// ---------------------------------------------------------------------------

// TestRound is the result of a single test execution against a hypothesis.
type TestRound struct {
RoundN       int       `json:"round_n"`
DispatchedAt time.Time `json:"dispatched_at"`
Result       string    `json:"result"`   // raw evidence gathered
Verdict      string    `json:"verdict"`  // CONFIRMED | REFUTED | INCONCLUSIVE
Passed       bool      `json:"passed"`
Confidence   float64   `json:"confidence"` // 0.0–1.0
}

// Hypothesis is a falsifiable claim about the world, formed from a topic
// and associated fact summary, then tested up to 3 rounds.
type Hypothesis struct {
ID              string               `json:"id"`
Topic           string               `json:"topic"`
FactSummary     string               `json:"fact_summary,omitempty"`
Claim           string               `json:"claim"`
Prediction      string               `json:"prediction"`
TestMethod      HypothesisTestMethod `json:"test_method"`
TestSpec        string               `json:"test_spec"` // what to search/compute/deduce

Status          HypothesisStatus `json:"status"`
Rounds          []TestRound      `json:"rounds,omitempty"`
NegativeKnowledge bool           `json:"negative_knowledge,omitempty"` // refuted → store as negative fact
RequeueCount    int              `json:"requeue_count,omitempty"`

ConfirmedAt *time.Time `json:"confirmed_at,omitempty"`
RefutedAt   *time.Time `json:"refuted_at,omitempty"`
CreatedAt   time.Time  `json:"created_at"`
UpdatedAt   time.Time  `json:"updated_at"`
}

// PassCount returns how many test rounds passed.
func (h *Hypothesis) PassCount() int {
n := 0
for _, r := range h.Rounds {
if r.Passed {
n++
}
}
return n
}

// FailCount returns how many test rounds failed.
func (h *Hypothesis) FailCount() int {
return len(h.Rounds) - h.PassCount()
}

// ---------------------------------------------------------------------------
// HypothesisStore — thread-safe in-memory ring with JSON persistence
// ---------------------------------------------------------------------------

const storeMaxSize = 100
const storeFile = "data/science/hypotheses.json"

// HypothesisStore is a bounded in-memory store for hypotheses.
type HypothesisStore struct {
mu       sync.RWMutex
entries  []*Hypothesis
index    map[string]*Hypothesis
maxSize  int
dataFile string
seq      uint64
}

// NewHypothesisStore creates a store and loads any persisted data.
func NewHypothesisStore(dataFile string) *HypothesisStore {
if dataFile == "" {
dataFile = storeFile
}
s := &HypothesisStore{
index:    make(map[string]*Hypothesis),
maxSize:  storeMaxSize,
dataFile: dataFile,
}
s.load()
return s
}

// Save persists a hypothesis (insert or update).
func (s *HypothesisStore) Save(h *Hypothesis) {
s.mu.Lock()
defer s.mu.Unlock()
if h.ID == "" {
s.seq++
h.ID = fmt.Sprintf("hyp-%d", s.seq)
}
h.UpdatedAt = time.Now()
if _, exists := s.index[h.ID]; !exists {
if len(s.entries) >= s.maxSize {
evicted := s.entries[0]
delete(s.index, evicted.ID)
s.entries = s.entries[1:]
}
s.entries = append(s.entries, h)
}
s.index[h.ID] = h
s.persist()
}

// Get returns a hypothesis by ID.
func (s *HypothesisStore) Get(id string) *Hypothesis {
s.mu.RLock()
defer s.mu.RUnlock()
return s.index[id]
}

// List returns all hypotheses, optionally filtered by status ("" = all).
func (s *HypothesisStore) List(statusFilter HypothesisStatus) []*Hypothesis {
s.mu.RLock()
defer s.mu.RUnlock()
var out []*Hypothesis
for i := len(s.entries) - 1; i >= 0; i-- {
h := s.entries[i]
if statusFilter == "" || h.Status == statusFilter {
out = append(out, h)
}
}
return out
}

// Stats returns a count breakdown by status.
func (s *HypothesisStore) Stats() map[string]int {
s.mu.RLock()
defer s.mu.RUnlock()
counts := map[string]int{
"total": len(s.entries), "pending": 0, "testing": 0,
"confirmed": 0, "refuted": 0, "inconclusive": 0,
}
for _, h := range s.entries {
counts[string(h.Status)]++
}
return counts
}

func (s *HypothesisStore) persist() {
data, err := json.MarshalIndent(s.entries, "", "  ")
if err != nil {
return
}
os.WriteFile(s.dataFile, data, 0644)
}

func (s *HypothesisStore) load() {
data, err := os.ReadFile(s.dataFile)
if err != nil {
return
}
var entries []*Hypothesis
if err := json.Unmarshal(data, &entries); err != nil {
return
}
s.mu.Lock()
defer s.mu.Unlock()
for _, h := range entries {
if len(s.entries) >= s.maxSize {
break
}
s.entries = append(s.entries, h)
s.index[h.ID] = h
if s.seq < 1000 {
s.seq = 1000 // avoid ID collision after reload
}
}
}

// FindByTopic returns all hypotheses whose Topic matches (case-insensitive prefix).
func (s *HypothesisStore) FindByTopic(topic string) []*Hypothesis {
s.mu.RLock()
defer s.mu.RUnlock()
var out []*Hypothesis
for _, h := range s.entries {
if strings.EqualFold(h.Topic, topic) {
out = append(out, h)
}
}
return out
}

// ByStatus returns all hypotheses with the given status.
func (s *HypothesisStore) ByStatus(status HypothesisStatus) []*Hypothesis {
s.mu.RLock()
defer s.mu.RUnlock()
var out []*Hypothesis
for _, h := range s.entries {
if h.Status == status {
out = append(out, h)
}
}
return out
}
