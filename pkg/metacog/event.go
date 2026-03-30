// Package metacog implements Phase 8 — Metacognitive Sentience.
// It detects looping, overconfidence, hallucination signals, and epistemic
// stagnation at runtime, logs structured events, and triggers self-correction.
package metacog

import (
"sync"
"time"
)

// EventType classifies a metacognitive anomaly.
type EventType string

const (
LoopDetected        EventType = "LOOP_DETECTED"
Overconfidence      EventType = "OVERCONFIDENCE"
HallucinationSignal EventType = "HALLUCINATION_SIGNAL"
EpistemicStagnation EventType = "EPISTEMIC_STAGNATION"
)

// Resolution describes what action was taken when an event was detected.
type Resolution string

const (
ResolutionLogOnly    Resolution = "log_only"
ResolutionRetried    Resolution = "retried"
ResolutionPropagated Resolution = "propagated_to_reform"
)

// MetacogEvent is a single metacognitive anomaly observation.
type MetacogEvent struct {
ID          string     `json:"id"`
Type        EventType  `json:"type"`
Severity    string     `json:"severity"`
Description string     `json:"description"`
Excerpt     string     `json:"excerpt,omitempty"`
Prompt      string     `json:"prompt,omitempty"`
Resolution  Resolution `json:"resolution"`
TriggeredAt time.Time  `json:"triggered_at"`
}

const defaultMaxEvents = 500

// EventLog is a bounded, thread-safe ring buffer of MetacogEvents.
type EventLog struct {
mu     sync.RWMutex
events []*MetacogEvent
maxLen int
}

// NewEventLog creates an EventLog with capacity maxLen (0 → default 500).
func NewEventLog(maxLen int) *EventLog {
if maxLen <= 0 {
maxLen = defaultMaxEvents
}
return &EventLog{maxLen: maxLen}
}

// Append adds an event to the ring buffer, evicting the oldest if full.
func (l *EventLog) Append(e *MetacogEvent) {
l.mu.Lock()
defer l.mu.Unlock()
if len(l.events) >= l.maxLen {
l.events = l.events[1:]
}
l.events = append(l.events, e)
}

// Recent returns the last n events (all if n <= 0).
func (l *EventLog) Recent(n int) []*MetacogEvent {
l.mu.RLock()
defer l.mu.RUnlock()
if n <= 0 || n >= len(l.events) {
out := make([]*MetacogEvent, len(l.events))
copy(out, l.events)
return out
}
out := make([]*MetacogEvent, n)
copy(out, l.events[len(l.events)-n:])
return out
}

// Since returns all events triggered after the given time.
func (l *EventLog) Since(t time.Time) []*MetacogEvent {
l.mu.RLock()
defer l.mu.RUnlock()
var out []*MetacogEvent
for _, e := range l.events {
if e.TriggeredAt.After(t) {
out = append(out, e)
}
}
return out
}

// Stats returns per-type event counts across all time.
func (l *EventLog) Stats() map[EventType]int {
l.mu.RLock()
defer l.mu.RUnlock()
counts := make(map[EventType]int)
for _, e := range l.events {
counts[e.Type]++
}
return counts
}
