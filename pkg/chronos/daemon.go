package chronos

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/metacog"
)

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

// LLMSummarizer is the minimal interface for generating a change-summary.
// *service.GenerationService satisfies this.
type LLMSummarizer interface {
Generate(prompt string, options map[string]interface{}) (map[string]interface{}, error)
}

// CuriositySeeder receives high-churn topics so CuriosityDaemon can forage
// for updated facts. This interface prevents an import cycle with pkg/service.
type CuriositySeeder interface {
SeedTopic(topic string, priority float64, reason string)
}

// EpistemicStagnationThreshold is how many consecutive stale-scans on a
// single topic before an EpistemicStagnation event is emitted.
const EpistemicStagnationThreshold = 3

// ---------------------------------------------------------------------------
// TemporalGroundingDaemon
// ---------------------------------------------------------------------------

// TemporalGroundingDaemon runs the temporal accounting loop:
//   - every 30 min: decay scan → flag stale entries → EpistemicStagnation events
//   - every 6 hours: snapshot pass → diff → LLM change-summary → curiosity seeds
type TemporalGroundingDaemon struct {
index      *ChronosIndex
snapshotter *Snapshotter
llm        LLMSummarizer // optional — nil → skip LLM summaries
seeder     CuriositySeeder // optional — nil → skip curiosity seeding
metacogLog *metacog.EventLog // optional — nil → skip epistemic stagnation events

decayInterval    time.Duration
snapshotInterval time.Duration

mu          sync.Mutex
changes     []ChangeRecord
lastScan    ScanResult
totalScans  int
}

// NewTemporalGroundingDaemon creates a daemon. llm, seeder, metacogLog may all be nil.
func NewTemporalGroundingDaemon(
idx *ChronosIndex,
snapDir string,
llm LLMSummarizer,
seeder CuriositySeeder,
metacogLog *metacog.EventLog,
) *TemporalGroundingDaemon {
return &TemporalGroundingDaemon{
index:            idx,
snapshotter:      NewSnapshotter(snapDir),
llm:              llm,
seeder:           seeder,
metacogLog:       metacogLog,
decayInterval:    30 * time.Minute,
snapshotInterval: 6 * time.Hour,
}
}

// StartDaemon launches the background loops.
// SetCuriositySeeder injects a CuriositySeeder after construction (e.g. Phase 10 ScienceDaemon).
// Safe to call from main.go after both Chronos and Science daemons are booted.
func (d *TemporalGroundingDaemon) SetCuriositySeeder(s CuriositySeeder) {
	d.seeder = s
}

func (d *TemporalGroundingDaemon) StartDaemon(ctx context.Context) {
log.Printf("[Chronos] Temporal Grounding active — decay: %s, snapshot: %s",
d.decayInterval, d.snapshotInterval)
go d.runDecayLoop(ctx)
go d.runSnapshotLoop(ctx)
}

// ForceDecayScan runs a decay scan immediately and returns the result.
func (d *TemporalGroundingDaemon) ForceDecayScan() ScanResult {
return d.runDecay()
}

// ForceSnapshot runs a snapshot+diff pass immediately and returns the diff.
func (d *TemporalGroundingDaemon) ForceSnapshot() SnapshotDiff {
return d.runSnapshot()
}

// Stats returns a summary of temporal grounding state.
func (d *TemporalGroundingDaemon) Stats() map[string]interface{} {
d.mu.Lock()
defer d.mu.Unlock()

lastScanAt := ""
if !d.lastScan.ScannedAt.IsZero() {
lastScanAt = d.lastScan.ScannedAt.Format(time.RFC3339)
}

recentChanges := d.changes
if len(recentChanges) > 10 {
recentChanges = recentChanges[len(recentChanges)-10:]
}

return map[string]interface{}{
"index_size":    d.index.Len(),
"total_scans":   d.totalScans,
"last_scan_at":  lastScanAt,
"last_stale":    d.lastScan.StaleCount,
"change_records": len(d.changes),
"recent_changes": recentChanges,
}
}

// RecentChanges returns the last N ChangeRecords.
func (d *TemporalGroundingDaemon) RecentChanges(n int) []ChangeRecord {
d.mu.Lock()
defer d.mu.Unlock()
if n <= 0 || n >= len(d.changes) {
out := make([]ChangeRecord, len(d.changes))
copy(out, d.changes)
return out
}
out := make([]ChangeRecord, n)
copy(out, d.changes[len(d.changes)-n:])
return out
}

// LatestSnapshot returns the most recently persisted snapshot.
func (d *TemporalGroundingDaemon) LatestSnapshot() Snapshot {
return d.snapshotter.LoadLatest()
}

// ---------------------------------------------------------------------------
// Internal loops
// ---------------------------------------------------------------------------

func (d *TemporalGroundingDaemon) runDecayLoop(ctx context.Context) {
ticker := time.NewTicker(d.decayInterval)
defer ticker.Stop()
for {
select {
case <-ctx.Done():
return
case <-ticker.C:
d.runDecay()
}
}
}

func (d *TemporalGroundingDaemon) runSnapshotLoop(ctx context.Context) {
ticker := time.NewTicker(d.snapshotInterval)
defer ticker.Stop()
for {
select {
case <-ctx.Done():
return
case <-ticker.C:
d.runSnapshot()
}
}
}

func (d *TemporalGroundingDaemon) runDecay() ScanResult {
result := DecayScan(d.index)

d.mu.Lock()
d.lastScan = result
d.totalScans++
d.mu.Unlock()

if result.StaleCount > 0 {
log.Printf("[Chronos] Decay scan: %d/%d entries stale", result.StaleCount, result.ScannedCount)
}

// EpistemicStagnation bridge — entries stale for ≥ threshold consecutive scans
if d.metacogLog != nil {
for _, e := range result.StaleEntries {
if e.StaleScans >= EpistemicStagnationThreshold {
evt := &metacog.MetacogEvent{
ID:          fmt.Sprintf("chronos-stagnation-%s", e.ID),
Type:        metacog.EpistemicStagnation,
Severity:    "MEDIUM",
Description: fmt.Sprintf("Topic '%s' has been stale for %d consecutive scans — knowledge may be permanently outdated.", e.Topic, e.StaleScans),
Excerpt:     e.Content,
Resolution:  metacog.ResolutionPropagated,
TriggeredAt: time.Now(),
}
d.metacogLog.Append(evt)
log.Printf("[Chronos] ⚠ EpistemicStagnation emitted for topic: %s (%d scans stale)", e.Topic, e.StaleScans)
}
}
}

return result
}

func (d *TemporalGroundingDaemon) runSnapshot() SnapshotDiff {
prev := d.snapshotter.LoadLatest()
curr := d.snapshotter.Take(d.index)
diff := Diff(prev, curr)

log.Printf("[Chronos] Snapshot taken — %d entries, %d changes (new:%d removed:%d drop:%d)",
len(curr.Entries), diff.TotalChanges(), len(diff.New), len(diff.Removed), len(diff.ConfidenceDrop))

record := ChangeRecord{
DiffAt:          time.Now(),
Diff:            diff,
HighChurnTopics: diff.HighChurnTopics,
}

// LLM summary — only worthwhile when there are real changes
if diff.TotalChanges() >= 3 && d.llm != nil {
summary := d.generateSummary(diff)
record.Summary = summary
}

// Curiosity seeding for high-churn topics
if d.seeder != nil {
for _, topic := range diff.HighChurnTopics {
d.seeder.SeedTopic(topic, 0.8, "high temporal churn — knowledge state shifting")
log.Printf("[Chronos] Curiosity seed injected for high-churn topic: %s", topic)
}
}

d.mu.Lock()
d.changes = append(d.changes, record)
if len(d.changes) > 100 {
d.changes = d.changes[1:] // keep last 100
}
d.mu.Unlock()

return diff
}

func (d *TemporalGroundingDaemon) generateSummary(diff SnapshotDiff) string {
if d.llm == nil {
return ""
}
prompt := buildSummaryPrompt(diff)
result, err := d.llm.Generate(prompt, map[string]interface{}{"num_predict": 200})
if err != nil {
return ""
}
if text, ok := result["text"].(string); ok {
return text
}
return ""
}

func buildSummaryPrompt(diff SnapshotDiff) string {
p := "Summarize the following knowledge state changes in 2-3 sentences. Be factual and concise.\n\n"
if len(diff.New) > 0 {
p += fmt.Sprintf("New knowledge entries (%d): ", len(diff.New))
for i, e := range diff.New {
if i >= 3 {
break
}
p += e.Topic + ", "
}
p += "\n"
}
if len(diff.Removed) > 0 {
p += fmt.Sprintf("Removed entries (%d): ", len(diff.Removed))
for i, e := range diff.Removed {
if i >= 3 {
break
}
p += e.Topic + ", "
}
p += "\n"
}
if len(diff.ConfidenceDrop) > 0 {
p += fmt.Sprintf("Confidence-decayed entries (%d): ", len(diff.ConfidenceDrop))
for i, e := range diff.ConfidenceDrop {
if i >= 3 {
break
}
p += e.Topic + ", "
}
p += "\n"
}
if len(diff.HighChurnTopics) > 0 {
p += fmt.Sprintf("High-churn topics: %v\n", diff.HighChurnTopics)
}
p += "\nSummary:"
return p
}

// fmt is used above — ensure it's imported properly.
