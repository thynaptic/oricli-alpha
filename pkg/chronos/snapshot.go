package chronos

import (
"encoding/json"
"fmt"
"os"
"path/filepath"
"sort"
"time"
)

// ---------------------------------------------------------------------------
// Snapshot types
// ---------------------------------------------------------------------------

// SnapshotEntry is a lightweight projection of a ChronosEntry into a snapshot.
type SnapshotEntry struct {
ID         string        `json:"id"`
Topic      string        `json:"topic"`
Category   DecayCategory `json:"category"`
Confidence float64       `json:"confidence"`
LearnedAt  time.Time     `json:"learned_at"`
}

// Snapshot captures the top-N knowledge entries at a point in time.
type Snapshot struct {
ID      string          `json:"id"`
TakenAt time.Time       `json:"taken_at"`
Entries []SnapshotEntry `json:"entries"`
}

// SnapshotDiff compares two consecutive snapshots.
type SnapshotDiff struct {
From            time.Time       `json:"from"`
To              time.Time       `json:"to"`
New             []SnapshotEntry `json:"new,omitempty"`
Removed         []SnapshotEntry `json:"removed,omitempty"`
ConfidenceDrop  []SnapshotEntry `json:"confidence_drop,omitempty"` // dropped > 20%
Reconfirmed     []SnapshotEntry `json:"reconfirmed,omitempty"`     // gained > 10%
HighChurnTopics []string        `json:"high_churn_topics,omitempty"`
}

// ChangeRecord pairs a SnapshotDiff with an LLM-generated summary.
type ChangeRecord struct {
DiffAt          time.Time    `json:"diff_at"`
Diff            SnapshotDiff `json:"diff"`
Summary         string       `json:"summary,omitempty"`
HighChurnTopics []string     `json:"high_churn_topics,omitempty"`
}

// ---------------------------------------------------------------------------
// Snapshotter
// ---------------------------------------------------------------------------

const snapshotTop = 200 // max entries per snapshot

// Snapshotter persists snapshots as JSON files under a configurable directory.
type Snapshotter struct {
dir string
}

// NewSnapshotter creates a Snapshotter writing to dir.
func NewSnapshotter(dir string) *Snapshotter {
os.MkdirAll(dir, 0755)
return &Snapshotter{dir: dir}
}

// Take builds a new snapshot from the top-N entries in the index.
func (s *Snapshotter) Take(idx *ChronosIndex) Snapshot {
now := time.Now()
all := idx.TopN(snapshotTop)
entries := make([]SnapshotEntry, 0, len(all))
for _, e := range all {
entries = append(entries, SnapshotEntry{
ID:         e.ID,
Topic:      e.Topic,
Category:   e.Category,
Confidence: e.DecayedConfidence(now),
LearnedAt:  e.LearnedAt,
})
}
snap := Snapshot{
ID:      fmt.Sprintf("snap_%d", now.UnixMilli()),
TakenAt: now,
Entries: entries,
}
s.save(snap)
return snap
}

// LoadLatest returns the most recent persisted snapshot, or a zero Snapshot
// if none exists yet.
func (s *Snapshotter) LoadLatest() Snapshot {
files, err := filepath.Glob(filepath.Join(s.dir, "snap_*.json"))
if err != nil || len(files) == 0 {
return Snapshot{}
}
sort.Strings(files) // lexicographic = chronological for snap_<millis>.json
data, err := os.ReadFile(files[len(files)-1])
if err != nil {
return Snapshot{}
}
var snap Snapshot
json.Unmarshal(data, &snap)
return snap
}

// Diff compares two snapshots and returns what changed.
func Diff(prev, curr Snapshot) SnapshotDiff {
d := SnapshotDiff{From: prev.TakenAt, To: curr.TakenAt}
if prev.TakenAt.IsZero() {
// First snapshot — everything is "new"
d.New = curr.Entries
return d
}

prevMap := make(map[string]SnapshotEntry, len(prev.Entries))
for _, e := range prev.Entries {
prevMap[e.ID] = e
}
currMap := make(map[string]SnapshotEntry, len(curr.Entries))
for _, e := range curr.Entries {
currMap[e.ID] = e
}

for id, ce := range currMap {
pe, existed := prevMap[id]
if !existed {
d.New = append(d.New, ce)
continue
}
delta := ce.Confidence - pe.Confidence
if delta < -0.20 {
d.ConfidenceDrop = append(d.ConfidenceDrop, ce)
} else if delta > 0.10 {
d.Reconfirmed = append(d.Reconfirmed, ce)
}
}
for id, pe := range prevMap {
if _, still := currMap[id]; !still {
d.Removed = append(d.Removed, pe)
}
}

// High-churn: topics that appear in both New and ConfidenceDrop
topicSet := make(map[string]int)
for _, e := range d.New {
topicSet[e.Topic]++
}
for _, e := range d.ConfidenceDrop {
topicSet[e.Topic]++
}
for t, n := range topicSet {
if n >= 2 && t != "" {
d.HighChurnTopics = append(d.HighChurnTopics, t)
}
}
return d
}

// TotalChanges returns the total number of changed entries in a diff.
func (d SnapshotDiff) TotalChanges() int {
return len(d.New) + len(d.Removed) + len(d.ConfidenceDrop) + len(d.Reconfirmed)
}

func (s *Snapshotter) save(snap Snapshot) {
data, err := json.MarshalIndent(snap, "", "  ")
if err != nil {
return
}
path := filepath.Join(s.dir, snap.ID+".json")
os.WriteFile(path, data, 0644)
}
