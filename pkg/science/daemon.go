package science

import (
"context"
"log"
"sync"
"time"
)

// ---------------------------------------------------------------------------
// submitJob — internal queue item
// ---------------------------------------------------------------------------

type submitJob struct {
topic       string
factSummary string
priority    float64
reason      string
}

// ---------------------------------------------------------------------------
// ScienceDaemon
// ---------------------------------------------------------------------------

// ScienceDaemon is the main entry-point for Phase 10.
// It implements chronos.CuriositySeeder so Chronos can inject stale topics.
type ScienceDaemon struct {
formulator *Formulator
engine     *ScienceEngine
store      *HypothesisStore

queue chan submitJob

// inconclusiveRetry ticker
retryInterval time.Duration

mu      sync.Mutex
started bool
}

// NewScienceDaemon creates a ScienceDaemon ready to be started.
func NewScienceDaemon(f *Formulator, engine *ScienceEngine, store *HypothesisStore) *ScienceDaemon {
return &ScienceDaemon{
formulator:    f,
engine:        engine,
store:         store,
queue:         make(chan submitJob, 64),
retryInterval: 2 * time.Hour,
}
}

// Submit enqueues a topic+factSummary pair for hypothesis formation and testing.
func (d *ScienceDaemon) Submit(topic, factSummary string) {
d.queue <- submitJob{topic: topic, factSummary: factSummary, priority: 0.5, reason: "direct submit"}
}

// SeedTopic implements chronos.CuriositySeeder — called by TemporalGroundingDaemon.
func (d *ScienceDaemon) SeedTopic(topic string, priority float64, reason string) {
d.queue <- submitJob{
topic:       topic,
factSummary: reason, // use the chronos reason as a summary hint
priority:    priority,
reason:      reason,
}
}

// StartDaemon starts the background worker and re-test ticker.
// ctx cancellation stops both goroutines.
func (d *ScienceDaemon) StartDaemon(ctx context.Context) {
d.mu.Lock()
if d.started {
d.mu.Unlock()
return
}
d.started = true
d.mu.Unlock()

log.Println("[ScienceDaemon] starting — Phase 10 Active Science online")

go d.worker(ctx)
go d.retryWorker(ctx)
}

// Stats returns engine + store statistics.
func (d *ScienceDaemon) Stats() map[string]interface{} {
stats := d.engine.Stats()
stats["queue_len"] = len(d.queue)
return stats
}

// ---------------------------------------------------------------------------
// Background workers
// ---------------------------------------------------------------------------

func (d *ScienceDaemon) worker(ctx context.Context) {
for {
select {
case <-ctx.Done():
return
case job := <-d.queue:
d.process(ctx, job)
}
}
}

func (d *ScienceDaemon) process(ctx context.Context, job submitJob) {
// Skip if we've already confirmed or refuted this topic recently
existing := d.store.FindByTopic(job.topic)
for _, h := range existing {
if h.Status == StatusConfirmed || h.Status == StatusRefuted {
log.Printf("[ScienceDaemon] skip %q — already %s", job.topic, h.Status)
return
}
if h.Status == StatusTesting {
log.Printf("[ScienceDaemon] skip %q — currently testing", job.topic)
return
}
}

log.Printf("[ScienceDaemon] forming hypothesis for topic %q (priority=%.2f)", job.topic, job.priority)

h, err := d.formulator.Form(job.topic, job.factSummary)
if err != nil {
log.Printf("[ScienceDaemon] formulator error for %q: %v", job.topic, err)
return
}

d.engine.RunHypothesis(ctx, h)
}

func (d *ScienceDaemon) retryWorker(ctx context.Context) {
ticker := time.NewTicker(d.retryInterval)
defer ticker.Stop()

for {
select {
case <-ctx.Done():
return
case <-ticker.C:
d.retryInconclusive(ctx)
}
}
}

func (d *ScienceDaemon) retryInconclusive(ctx context.Context) {
candidates := d.store.ByStatus(StatusInconclusive)
if len(candidates) == 0 {
return
}
log.Printf("[ScienceDaemon] re-testing %d inconclusive hypotheses", len(candidates))
for _, h := range candidates {
if h.RequeueCount >= requeueMax {
log.Printf("[ScienceDaemon] dropping %q after %d requeues", h.Claim, h.RequeueCount)
h.Status = StatusRefuted
h.NegativeKnowledge = false // not refuted — just expired
d.store.Save(h)
continue
}
h.Status = StatusPending
d.store.Save(h)
d.engine.RunHypothesis(ctx, h)
}
}

// Store returns the HypothesisStore for direct read access (API handlers).
func (d *ScienceDaemon) Store() *HypothesisStore {
return d.store
}
