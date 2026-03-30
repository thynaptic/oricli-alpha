package service

// TCDDaemon — Temporal Curriculum Daemon
//
// Runs on a configurable interval and keeps the SCL knowledge base current.
//
// Each tick:
//  1. AuditDomains     — compute avg confidence + age per domain
//  2. PrioritizeDomains — sort by FreshnessPolicy urgency
//  3. IngestDomains    — fetch live sources → LLM distill → SCL.WriteFact
//  4. MergeCheck       — fold near-duplicate domains (cosine ≥ 0.88)
//  5. PruneCheck       — mark dormant / archive dead domains
//  6. GapScan          — detect orphan facts and spawn new domains
//  7. EmitReport       — log stats diff
//
// Env vars:
//
//	ORICLI_TCD_ENABLED=true        — enable the daemon (default: false)
//	ORICLI_TCD_INTERVAL=6h         — tick interval (default: 6h)
//	ORICLI_TCD_MAX_DOMAINS_PER_TICK=5 — cap to avoid long ticks (default: 5)

import (
	"context"
	"log"
	"os"
	"strconv"
	"time"

	"github.com/thynaptic/oricli-go/pkg/tcd"
)

// TCDDaemon orchestrates the Temporal Curriculum Daemon tick loop.
type TCDDaemon struct {
	manifest    *tcd.DomainManifest
	auditor     *tcd.FreshnessAuditor
	ingestor    *tcd.DomainIngestor
	maintainer  *tcd.ManifestMaintainer
	gapDetector *tcd.GapDetector

	interval         time.Duration
	maxDomainsPerTick int
	enabled          bool

	// ManualTick can be sent to trigger an immediate tick (admin endpoint).
	ManualTick chan struct{}
}

// NewTCDDaemon builds a TCDDaemon from env config.
// All component pointers may be nil — the daemon skips nil components gracefully.
func NewTCDDaemon(
	manifest *tcd.DomainManifest,
	auditor *tcd.FreshnessAuditor,
	ingestor *tcd.DomainIngestor,
	maintainer *tcd.ManifestMaintainer,
	gapDetector *tcd.GapDetector,
) *TCDDaemon {
	d := &TCDDaemon{
		manifest:         manifest,
		auditor:          auditor,
		ingestor:         ingestor,
		maintainer:       maintainer,
		gapDetector:      gapDetector,
		interval:         6 * time.Hour,
		maxDomainsPerTick: 5,
		enabled:          os.Getenv("ORICLI_TCD_ENABLED") == "true",
		ManualTick:       make(chan struct{}, 1),
	}

	if v := os.Getenv("ORICLI_TCD_INTERVAL"); v != "" {
		if dur, err := time.ParseDuration(v); err == nil && dur > 0 {
			d.interval = dur
		}
	}
	if v := os.Getenv("ORICLI_TCD_MAX_DOMAINS_PER_TICK"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			d.maxDomainsPerTick = n
		}
	}
	return d
}

// Run starts the daemon loop. Blocking — call as goroutine.
func (d *TCDDaemon) Run() {
	if !d.enabled {
		log.Println("[TCD] disabled (ORICLI_TCD_ENABLED != true)")
		return
	}
	log.Printf("[TCD] started — interval: %v, maxDomains/tick: %d", d.interval, d.maxDomainsPerTick)

	// Bootstrap manifest on first run (seeds 10 domains if empty).
	if d.manifest != nil {
		ctx := context.Background()
		if err := d.manifest.Bootstrap(ctx); err != nil {
			log.Printf("[TCD] manifest bootstrap error: %v", err)
		}
	}

	ticker := time.NewTicker(d.interval)
	defer ticker.Stop()

	// Run one tick immediately after boot so we don't wait a full interval.
	d.Tick()

	for {
		select {
		case <-ticker.C:
			d.Tick()
		case <-d.ManualTick:
			log.Println("[TCD] manual tick triggered")
			d.Tick()
		}
	}
}

// Tick executes one full TCD cycle. Public so the admin endpoint can call it.
func (d *TCDDaemon) Tick() {
	start := time.Now()
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	log.Println("[TCD] tick start")
	totalFacts := 0

	// ── 1. Audit + Prioritize ──────────────────────────────────────────────────
	if d.auditor == nil || d.manifest == nil {
		log.Println("[TCD] auditor or manifest nil — skipping tick")
		return
	}
	domains := d.manifest.All()
	if len(domains) == 0 {
		log.Println("[TCD] no domains — skipping tick")
		return
	}

	_ = d.auditor.AuditAll(ctx)
	queue := d.auditor.Prioritize(ctx)

	// ── 2. Ingest (capped at maxDomainsPerTick) ────────────────────────────────
	if d.ingestor != nil {
		workItems := []tcd.DomainAudit(queue)
		ingestCap := d.maxDomainsPerTick
		if ingestCap > len(workItems) {
			ingestCap = len(workItems)
		}
		for _, audit := range workItems[:ingestCap] {
			if audit.Decision == tcd.DecisionSkip {
				continue
			}
			n, err := d.ingestor.IngestDomain(ctx, audit)
			if err != nil {
				log.Printf("[TCD] ingest %q: %v", audit.Domain.Name, err)
				continue
			}
			totalFacts += n
		}
	}

	// ── 3. Merge + Prune ───────────────────────────────────────────────────────
	if d.maintainer != nil {
		if _, err := d.maintainer.MergeCheck(ctx); err != nil {
			log.Printf("[TCD] MergeCheck: %v", err)
		}
		if _, _, err := d.maintainer.PruneCheck(ctx); err != nil {
			log.Printf("[TCD] PruneCheck: %v", err)
		}
	}

	// ── 4. Gap scan ────────────────────────────────────────────────────────────
	if d.gapDetector != nil {
		spawned, err := d.gapDetector.Scan(ctx)
		if err != nil {
			log.Printf("[TCD] GapScan: %v", err)
		} else if spawned > 0 {
			log.Printf("[TCD] GapScan spawned %d new domains", spawned)
		}
	}

	// ── 5. Report ──────────────────────────────────────────────────────────────
	log.Printf("[TCD] tick complete — domains: %d, facts written: %d, elapsed: %s",
		len(domains), totalFacts, time.Since(start).Round(time.Second))
}

// TriggerManualTick sends a non-blocking signal to run an immediate tick.
func (d *TCDDaemon) TriggerManualTick() {
	select {
	case d.ManualTick <- struct{}{}:
	default: // already pending
	}
}
