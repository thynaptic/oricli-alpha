package tcd

import (
	"context"
	"fmt"
	"log"
	"sort"
	"time"
)

// ─────────────────────────────────────────────────────────────────────────────
// FreshnessAuditor
// ─────────────────────────────────────────────────────────────────────────────

// DomainAudit is the result of auditing a single domain.
type DomainAudit struct {
	Domain    *Domain
	Decision  FreshnessDecision
	Urgency   float64 // 0.0–1.0; higher = process first
	AgeDays   float64
	Reason    string
}

// DomainWorkQueue is a prioritised list of domains to process this TCD tick.
type DomainWorkQueue []DomainAudit

// FreshnessAuditor evaluates all domains and produces an ordered work queue
// for the current TCD tick. Mirrors SmartResumePolicy from train_curriculum.py:
//   - SKIP        ← already fresh + high confidence
//   - REFRESH     ← marginal; light top-up
//   - DEEP_INGEST ← stale or low confidence; full pass
//   - PROBE       ← probation domain; 1 ingest + merge check
type FreshnessAuditor struct {
	Manifest *DomainManifest

	// Thresholds (tunable via env, defaulted here)
	SkipMinConfidence    float64 // default 0.85
	SkipMaxAgeDays       float64 // default 3
	DeepIngestMaxConf    float64 // default 0.60
	DeepIngestMinAgeDays float64 // default 14
}

// NewFreshnessAuditor creates an auditor with sensible defaults.
func NewFreshnessAuditor(manifest *DomainManifest) *FreshnessAuditor {
	return &FreshnessAuditor{
		Manifest:             manifest,
		SkipMinConfidence:    0.85,
		SkipMaxAgeDays:       3,
		DeepIngestMaxConf:    0.60,
		DeepIngestMinAgeDays: 14,
	}
}

// AuditAll evaluates every active domain and returns a full audit report.
func (a *FreshnessAuditor) AuditAll(_ context.Context) []DomainAudit {
	domains := a.Manifest.All()
	audits := make([]DomainAudit, 0, len(domains))

	for _, d := range domains {
		audit := a.auditOne(d)
		audits = append(audits, audit)
	}
	return audits
}

// Prioritize filters out SKIP decisions and sorts the rest by urgency descending.
// Returns a DomainWorkQueue ready for the TCD ingestion loop.
func (a *FreshnessAuditor) Prioritize(ctx context.Context) DomainWorkQueue {
	all := a.AuditAll(ctx)

	var queue DomainWorkQueue
	skipped := 0
	for _, au := range all {
		if au.Decision == DecisionSkip {
			skipped++
			continue
		}
		queue = append(queue, au)
	}

	sort.Slice(queue, func(i, j int) bool {
		return queue[i].Urgency > queue[j].Urgency
	})

	log.Printf("[TCD:Auditor] %d domains: %d queued, %d skipped",
		len(all), len(queue), skipped)
	return queue
}

// ─── internal ─────────────────────────────────────────────────────────────────

func (a *FreshnessAuditor) auditOne(d *Domain) DomainAudit {
	ageDays := 999.0 // never ingested
	if !d.LastIngested.IsZero() {
		ageDays = time.Since(d.LastIngested).Hours() / 24
	}

	decision := a.decide(d, ageDays)
	urgency := a.urgency(d, ageDays, decision)
	reason := a.reason(d, ageDays, decision)

	return DomainAudit{
		Domain:   d,
		Decision: decision,
		Urgency:  urgency,
		AgeDays:  ageDays,
		Reason:   reason,
	}
}

func (a *FreshnessAuditor) decide(d *Domain, ageDays float64) FreshnessDecision {
	switch d.Status {
	case StatusProbation:
		return DecisionProbe
	case StatusDormant, StatusArchived:
		return DecisionSkip
	}

	if d.AvgConfidence >= a.SkipMinConfidence && ageDays < a.SkipMaxAgeDays {
		return DecisionSkip
	}
	if d.AvgConfidence < a.DeepIngestMaxConf || ageDays > a.DeepIngestMinAgeDays {
		return DecisionDeepIngest
	}
	return DecisionRefresh
}

func (a *FreshnessAuditor) urgency(d *Domain, ageDays float64, dec FreshnessDecision) float64 {
	switch dec {
	case DecisionSkip:
		return 0
	case DecisionProbe:
		return 0.5 // probation domains get medium priority
	}
	// Blend confidence deficit (60%) + age (40%) — mirrors SmartResumePolicy gap/span logic
	confDeficit := 1.0 - d.AvgConfidence
	ageScore := min64(ageDays/30.0, 1.0)
	return confDeficit*0.6 + ageScore*0.4
}

func (a *FreshnessAuditor) reason(d *Domain, ageDays float64, dec FreshnessDecision) string {
	switch dec {
	case DecisionSkip:
		return "fresh"
	case DecisionProbe:
		return "probation_first_ingest"
	case DecisionDeepIngest:
		if ageDays > a.DeepIngestMinAgeDays {
			return fmt.Sprintf("stale:%.0fd", ageDays)
		}
		return fmt.Sprintf("low_confidence:%.2f", d.AvgConfidence)
	case DecisionRefresh:
		return fmt.Sprintf("marginal:conf=%.2f,age=%.0fd", d.AvgConfidence, ageDays)
	}
	return "unknown"
}
