// Package tcd implements the Temporal Curriculum Daemon — a live, scheduled
// knowledge maintenance system that keeps the SCL current with the world.
//
// Architecture: take the curriculum script's progression logic (SmartResumePolicy,
// staged ingestion, gap detection) and replace HuggingFace + weight updates with
// live web sources + SCL writes.
//
// Domains are the unit of knowledge organisation. They are stored in SCL
// (TierRelations) so the full SCL lifecycle (inspect, revise, decay) applies.
// A DomainEvent log records every spawn/merge/prune, giving a complete lineage
// of how knowledge evolved over time.
package tcd

import (
	"time"
)

// ─────────────────────────────────────────────────────────────────────────────
// Domain
// ─────────────────────────────────────────────────────────────────────────────

// DomainStatus represents the lifecycle stage of a knowledge domain.
type DomainStatus string

const (
	StatusActive     DomainStatus = "active"
	StatusProbation  DomainStatus = "probation" // newly gap-spawned, not yet verified
	StatusDormant    DomainStatus = "dormant"   // low confidence + no recent activity
	StatusArchived   DomainStatus = "archived"  // zero surviving SCL facts
)

// FreshnessDecision is the TCD equivalent of SmartResumePolicy's SKIP/RETOUCH/FULL.
type FreshnessDecision string

const (
	DecisionSkip       FreshnessDecision = "SKIP"        // fresh + high confidence
	DecisionRefresh    FreshnessDecision = "REFRESH"     // light top-up (3 sources)
	DecisionDeepIngest FreshnessDecision = "DEEP_INGEST" // full pass (all sources)
	DecisionProbe      FreshnessDecision = "PROBE"       // probation: 1 ingest + merge check
)

// SourceWeight maps source identifiers to a trust weight (0.0–1.0).
// Higher weight → facts from this source start with higher confidence.
// Weights are updated over time based on SpotVerify() pass rates.
type SourceWeight map[string]float64

// Domain is a knowledge area managed by the TCD.
// Stored in SCL TierRelations so the full SCL lifecycle applies.
type Domain struct {
	ID            string       `json:"id"`
	Name          string       `json:"name"`
	Keywords      []string     `json:"keywords"`
	Status        DomainStatus `json:"status"`
	AvgConfidence float64      `json:"avg_confidence"`
	LastIngested  time.Time    `json:"last_ingested"`
	IngestCount   int          `json:"ingest_count"`
	FactCount     int          `json:"fact_count"` // live SCL record count

	// Lineage — set on spawn/merge, never mutated afterwards.
	SpawnedFrom string   `json:"spawned_from,omitempty"` // parent domain ID
	Merges      []string `json:"merges,omitempty"`       // domain IDs absorbed into this one

	// Source configuration — per-domain, updated by SpotVerify().
	SourceWeights SourceWeight `json:"source_weights"`
}

// DefaultSourceWeights are the starting weights assigned to new domains.
// arXiv > wikipedia > HN > rss (arXiv has citations, lowest hallucination risk).
var DefaultSourceWeights = SourceWeight{
	"arxiv":     0.85,
	"wikipedia": 0.75,
	"hackernews": 0.60,
	"rss":        0.50,
}

// FreshnessScore returns a 0.0–1.0 staleness score.
// 0.0 = perfectly fresh, 1.0 = completely stale. Used for prioritisation.
func (d *Domain) FreshnessScore() float64 {
	if d.LastIngested.IsZero() {
		return 1.0 // never ingested → maximum priority
	}
	ageDays := time.Since(d.LastIngested).Hours() / 24

	// Confidence component: low confidence → higher score
	confPenalty := 1.0 - d.AvgConfidence

	// Age component: normalised at 14-day window
	agePenalty := min64(ageDays/14.0, 1.0)

	return (confPenalty*0.6 + agePenalty*0.4)
}

// Decide returns the FreshnessDecision for this domain.
func (d *Domain) Decide() FreshnessDecision {
	switch d.Status {
	case StatusProbation:
		return DecisionProbe
	case StatusDormant, StatusArchived:
		return DecisionSkip
	}

	ageDays := time.Since(d.LastIngested).Hours() / 24

	// SKIP: high confidence and recently ingested
	if d.AvgConfidence >= 0.85 && ageDays < 3 {
		return DecisionSkip
	}
	// DEEP_INGEST: low confidence or very stale
	if d.AvgConfidence < 0.60 || ageDays > 14 {
		return DecisionDeepIngest
	}
	// REFRESH: everything in between
	return DecisionRefresh
}

func min64(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

// ─────────────────────────────────────────────────────────────────────────────
// DomainEvent — append-only lineage log
// ─────────────────────────────────────────────────────────────────────────────

// EventType describes a domain lifecycle transition.
type EventType string

const (
	EventSpawn  EventType = "spawn"  // new domain born from a parent gap
	EventMerge  EventType = "merge"  // this domain folded into another
	EventPrune  EventType = "prune"  // domain moved to dormant/archived
	EventSplit  EventType = "split"  // domain divided into two specialisations
	EventRename EventType = "rename" // domain name/keywords updated
)

// DomainEvent records a single lifecycle transition.
// Stored in SCL TierRelations as an append-only log.
type DomainEvent struct {
	ID           string    `json:"id"`
	Type         EventType `json:"type"`
	FromDomainID string    `json:"from_domain_id"`
	ToDomainID   string    `json:"to_domain_id,omitempty"`   // target for merge/spawn
	Timestamp    time.Time `json:"timestamp"`
	Reason       string    `json:"reason"` // e.g. "gap_detected:7_orphans" | "cosine:0.91" | "manual"
	MigratedFacts int      `json:"migrated_facts,omitempty"` // facts transferred on merge
	ConfidenceAt float64   `json:"confidence_at"`            // snapshot of from_domain confidence at event time
}

// ─────────────────────────────────────────────────────────────────────────────
// Seed manifest
// ─────────────────────────────────────────────────────────────────────────────

// SeedDomains is the starting manifest — broad enough to have gravitational pull,
// narrow enough that gap detection fills in the rest organically.
var SeedDomains = []struct {
	Name     string
	Keywords []string
}{
	{"tech", []string{"technology", "software", "hardware", "cloud", "cybersecurity", "semiconductors"}},
	{"AI/ML", []string{"artificial intelligence", "machine learning", "deep learning", "LLM", "neural network", "transformer"}},
	{"geopolitics", []string{"geopolitics", "diplomacy", "war", "sanctions", "NATO", "UN", "foreign policy"}},
	{"science", []string{"physics", "chemistry", "biology", "astronomy", "climate", "quantum", "neuroscience"}},
	{"finance", []string{"finance", "markets", "stocks", "crypto", "central bank", "inflation", "GDP"}},
	{"health", []string{"health", "medicine", "biotech", "FDA", "pandemic", "drug", "clinical trial"}},
	{"engineering", []string{"engineering", "materials", "robotics", "aerospace", "manufacturing", "3D printing"}},
	{"law/policy", []string{"law", "regulation", "policy", "court", "legislation", "antitrust", "GDPR"}},
	{"culture", []string{"culture", "art", "music", "film", "literature", "philosophy", "social media"}},
	{"energy", []string{"energy", "oil", "gas", "solar", "wind", "nuclear", "battery", "grid"}},
}
