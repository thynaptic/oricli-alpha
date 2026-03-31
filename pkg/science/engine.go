package science

import (
"context"
"log"
"time"
)

// ---------------------------------------------------------------------------
// Interfaces for knowledge write-back (import-cycle safe)
// ---------------------------------------------------------------------------

// KnowledgeWriter persists a confirmed or refuted hypothesis result to memory.
// Satisfied by *scl.LedgerWriter or *service.MemoryBank adapters in main.go.
type KnowledgeWriter interface {
WriteFact(ctx context.Context, topic, content string, confidence float64, webVerified bool) error
}

// WSPublisher broadcasts science conclusions to the UI.
type WSPublisher interface {
BroadcastEvent(eventType string, payload interface{})
}

// ---------------------------------------------------------------------------
// ScienceEngine
// ---------------------------------------------------------------------------

const (
maxRounds          = 3
confirmThreshold   = 2 // passes needed out of maxRounds to confirm
requeueMax         = 3 // max re-queues for inconclusive hypotheses
)

// ScienceEngine drives the 3-round hypothesis test loop and writes results.
type ScienceEngine struct {
Tester    *Tester
Store     *HypothesisStore
Knowledge KnowledgeWriter // optional — nil → log only
WSHub     WSPublisher     // optional — nil → no broadcast

// Stats counters
confirmed    int
refuted      int
inconclusive int
}

// NewScienceEngine creates a ScienceEngine.
func NewScienceEngine(tester *Tester, store *HypothesisStore, kw KnowledgeWriter, hub WSPublisher) *ScienceEngine {
return &ScienceEngine{
Tester:    tester,
Store:     store,
Knowledge: kw,
WSHub:     hub,
}
}

// RunHypothesis executes up to maxRounds tests against h, updates its status,
// persists the result, writes knowledge, and broadcasts the conclusion.
func (e *ScienceEngine) RunHypothesis(ctx context.Context, h *Hypothesis) {
if h.Status != StatusPending && h.Status != StatusInconclusive {
return
}
h.Status = StatusTesting
e.Store.Save(h)

for round := len(h.Rounds) + 1; round <= maxRounds; round++ {
select {
case <-ctx.Done():
h.Status = StatusInconclusive
e.Store.Save(h)
return
default:
}

log.Printf("[Science] Testing hypothesis %s — round %d/%d — %q", h.ID, round, maxRounds, clip(h.Claim, 60))
tr := e.Tester.Run(ctx, h, round)
h.Rounds = append(h.Rounds, tr)
e.Store.Save(h)
}

e.conclude(ctx, h)
}

// Stats returns confirmed/refuted/inconclusive counts plus store stats.
func (e *ScienceEngine) Stats() map[string]interface{} {
s := e.Store.Stats()
s["engine_confirmed"] = e.confirmed
s["engine_refuted"] = e.refuted
s["engine_inconclusive"] = e.inconclusive
return map[string]interface{}{"store": s}
}

// ---------------------------------------------------------------------------
// Internal conclusion logic
// ---------------------------------------------------------------------------

func (e *ScienceEngine) conclude(ctx context.Context, h *Hypothesis) {
passes := h.PassCount()
fails := h.FailCount()
now := time.Now()

var status HypothesisStatus
var writeContent string
var writeConfidence float64
var negative bool

switch {
case passes >= confirmThreshold:
status = StatusConfirmed
h.ConfirmedAt = &now
writeContent = "CONFIRMED: " + h.Claim + " — " + h.Prediction
writeConfidence = 0.90
e.confirmed++
log.Printf("[Science] ✅ CONFIRMED: %q (%d/%d rounds passed)", h.Claim, passes, maxRounds)

case fails >= confirmThreshold:
status = StatusRefuted
h.RefutedAt = &now
h.NegativeKnowledge = true
writeContent = "REFUTED (negative knowledge): " + h.Claim + " — prediction did not hold"
writeConfidence = 0.75
negative = true
e.refuted++
log.Printf("[Science] ❌ REFUTED: %q (%d/%d rounds failed)", h.Claim, fails, maxRounds)

default:
status = StatusInconclusive
h.RequeueCount++
e.inconclusive++
log.Printf("[Science] ⚠ INCONCLUSIVE: %q (requeue #%d)", h.Claim, h.RequeueCount)
}

h.Status = status
e.Store.Save(h)

// Write to knowledge layer (skip inconclusive)
if status != StatusInconclusive && e.Knowledge != nil {
topic := h.Topic
if negative {
topic = "negative/" + topic
}
if err := e.Knowledge.WriteFact(ctx, topic, writeContent, writeConfidence, true); err != nil {
log.Printf("[Science] knowledge write error: %v", err)
}
}

// Broadcast WS event
if e.WSHub != nil {
e.WSHub.BroadcastEvent("science_conclusion", map[string]interface{}{
"hypothesis_id": h.ID,
"topic":         h.Topic,
"status":        string(status),
"claim":         h.Claim,
"passes":        passes,
"fails":         fails,
"negative":      negative,
})
}
}

func clip(s string, n int) string {
if len(s) <= n {
return s
}
return s[:n] + "…"
}
