package metacog

import (
"context"
"log"
"time"
)

// WSBroadcaster is the minimal interface for emitting metacog alerts to the UI.
type WSBroadcaster interface {
BroadcastEvent(eventType string, payload interface{})
}

// MetacogDaemon scans the EventLog on a rolling window, detects recurring
// anomaly patterns, broadcasts alerts, and surfaces high-recurrence events.
type MetacogDaemon struct {
log      *EventLog
hub      WSBroadcaster
interval time.Duration
window   time.Duration

recurrenceThreshold int
}

// NewMetacogDaemon creates a MetacogDaemon. hub may be nil.
func NewMetacogDaemon(log *EventLog, hub WSBroadcaster) *MetacogDaemon {
return &MetacogDaemon{
log:                 log,
hub:                 hub,
interval:            5 * time.Minute,
window:              30 * time.Minute,
recurrenceThreshold: 4,
}
}

// StartDaemon launches the background scan loop.
func (d *MetacogDaemon) StartDaemon(ctx context.Context) {
log.Printf("[MetacogDaemon] Sentience layer active — scan interval: %s, window: %s", d.interval, d.window)
go func() {
ticker := time.NewTicker(d.interval)
defer ticker.Stop()
for {
select {
case <-ctx.Done():
return
case <-ticker.C:
d.scan()
}
}
}()
}

// Scan runs a single scan cycle on demand.
func (d *MetacogDaemon) Scan() map[EventType]int {
return d.scan()
}

// Stats returns per-type totals and rolling-window recurrence rates.
func (d *MetacogDaemon) Stats() map[string]interface{} {
totals := d.log.Stats()
window := d.log.Since(time.Now().Add(-d.window))
windowCounts := make(map[EventType]int)
for _, e := range window {
windowCounts[e.Type]++
}

rateMap := make(map[string]interface{})
for _, t := range []EventType{LoopDetected, Overconfidence, HallucinationSignal, EpistemicStagnation} {
rateMap[string(t)] = map[string]interface{}{
"total":        totals[t],
"last_30m":     windowCounts[t],
"alert_active": windowCounts[t] >= d.recurrenceThreshold,
}
}

recent := d.log.Recent(10)
lastEvent := ""
if len(recent) > 0 {
lastEvent = recent[len(recent)-1].TriggeredAt.Format(time.RFC3339)
}

return map[string]interface{}{
"by_type":        rateMap,
"total_all_time": len(d.log.Recent(0)),
"last_event_at":  lastEvent,
"window_minutes": int(d.window.Minutes()),
"threshold":      d.recurrenceThreshold,
}
}

func (d *MetacogDaemon) scan() map[EventType]int {
cutoff := time.Now().Add(-d.window)
recent := d.log.Since(cutoff)

counts := make(map[EventType]int)
for _, e := range recent {
counts[e.Type]++
}

alertMessages := map[EventType]string{
LoopDetected:        "Reasoning loop detected repeatedly — she may be stuck.",
Overconfidence:      "Repeated ungrounded certainty — review recent responses.",
HallucinationSignal: "Repeated hallucination signals — grounding may be failing.",
EpistemicStagnation: "Knowledge gaps are recurring without resolution.",
}

for t, n := range counts {
if n >= d.recurrenceThreshold {
log.Printf("[MetacogDaemon] ⚠ HIGH RECURRENCE — %s fired %d times in last %s", t, n, d.window)
if d.hub != nil {
d.hub.BroadcastEvent("metacog_alert", map[string]interface{}{
"type":        t,
"count":       n,
"window_mins": int(d.window.Minutes()),
"message":     alertMessages[t],
})
}
}
}

return counts
}
