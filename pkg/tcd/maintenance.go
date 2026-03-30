package tcd

import (
	"context"
	"fmt"
	"log"
	"time"
)

// ─────────────────────────────────────────────────────────────────────────────
// ManifestMaintainer
// ─────────────────────────────────────────────────────────────────────────────

// DomainEmbedder generates a vector for a domain name + keywords.
// Implemented by scl.Ledger's embedder — defined here to avoid import cycle.
type DomainEmbedder interface {
	Embed(ctx context.Context, text string) []float32
}

// ManifestMaintainer runs merge and prune checks at the end of each TCD tick.
// Mirrors the DreamDaemon SCL maintenance pattern: called once per idle cycle,
// keeps the manifest lean without losing lineage history.
type ManifestMaintainer struct {
	Manifest  *DomainManifest
	Embedder  DomainEmbedder // nil = skip cosine merge, fallback to keyword overlap

	// MergeThreshold: cosine similarity ≥ this → fold smaller into larger.
	// Tighter than SCL dedup (0.92) — domains should be meaningfully distinct.
	MergeThreshold float64 // default 0.88

	// PruneMaxConfidence: below this avg_confidence...
	PruneMaxConfidence float64 // default 0.15
	// PruneMinStaleDays: ...AND not ingested for this many days → DORMANT
	PruneMinStaleDays float64 // default 90
	// ArchiveIfZeroFacts: domains with 0 surviving SCL facts → ARCHIVED
	ArchiveIfZeroFacts bool // default true
}

// NewManifestMaintainer creates a maintainer with sensible defaults.
func NewManifestMaintainer(manifest *DomainManifest, embedder DomainEmbedder) *ManifestMaintainer {
	return &ManifestMaintainer{
		Manifest:           manifest,
		Embedder:           embedder,
		MergeThreshold:     0.88,
		PruneMaxConfidence: 0.15,
		PruneMinStaleDays:  90,
		ArchiveIfZeroFacts: true,
	}
}

// Run executes both merge and prune checks. Called at end of each TCD tick.
func (m *ManifestMaintainer) Run(ctx context.Context) {
	merged, err := m.MergeCheck(ctx)
	if err != nil {
		log.Printf("[TCD:Maintain] MergeCheck error: %v", err)
	} else if merged > 0 {
		log.Printf("[TCD:Maintain] Merged %d domain pair(s).", merged)
	}

	dormant, archived, err := m.PruneCheck(ctx)
	if err != nil {
		log.Printf("[TCD:Maintain] PruneCheck error: %v", err)
	} else {
		if dormant > 0 {
			log.Printf("[TCD:Maintain] Marked %d domain(s) dormant.", dormant)
		}
		if archived > 0 {
			log.Printf("[TCD:Maintain] Archived %d domain(s).", archived)
		}
	}
}

// MergeCheck finds pairs of active domains that are semantically near-duplicate
// and folds the smaller (fewer facts) into the larger.
// Returns the number of merges performed.
func (m *ManifestMaintainer) MergeCheck(ctx context.Context) (int, error) {
	domains := m.Manifest.All()
	if len(domains) < 2 {
		return 0, nil
	}

	// Embed all domains.
	type embeddedDomain struct {
		domain *Domain
		vec    []float32
	}
	embedded := make([]embeddedDomain, 0, len(domains))
	for _, d := range domains {
		if d.Status == StatusDormant || d.Status == StatusArchived {
			continue
		}
		var vec []float32
		if m.Embedder != nil {
			text := d.Name + " " + joinKeywords(d.Keywords)
			vec = m.Embedder.Embed(ctx, text)
		}
		embedded = append(embedded, embeddedDomain{domain: d, vec: vec})
	}

	merged := 0
	mergedIDs := make(map[string]bool)

	for i := range embedded {
		if mergedIDs[embedded[i].domain.ID] {
			continue
		}
		for j := i + 1; j < len(embedded); j++ {
			if mergedIDs[embedded[j].domain.ID] {
				continue
			}

			similar := false
			if len(embedded[i].vec) > 0 && len(embedded[j].vec) > 0 {
				sim := cosineSim(embedded[i].vec, embedded[j].vec)
				similar = sim >= m.MergeThreshold
				if similar {
					log.Printf("[TCD:Maintain] Merge candidate: %q + %q (cosine %.3f)",
						embedded[i].domain.Name, embedded[j].domain.Name, sim)
				}
			} else {
				// Fallback: keyword overlap score
				similar = keywordOverlapScore(embedded[i].domain.Keywords, embedded[j].domain.Keywords) >= 0.6
			}

			if !similar {
				continue
			}

			// Keep the domain with more facts; fold the other in.
			keep, drop := embedded[i].domain, embedded[j].domain
			if drop.FactCount > keep.FactCount {
				keep, drop = drop, keep
			}

			factsMigrated := drop.FactCount
			if err := m.foldInto(ctx, keep, drop); err != nil {
				log.Printf("[TCD:Maintain] fold %q→%q: %v", drop.Name, keep.Name, err)
				continue
			}

			m.Manifest.LogEvent(ctx, DomainEvent{
				Type:          EventMerge,
				FromDomainID:  drop.ID,
				ToDomainID:    keep.ID,
				Reason:        fmt.Sprintf("cosine:%.2f", cosineSim(embedded[i].vec, embedded[j].vec)),
				MigratedFacts: factsMigrated,
				ConfidenceAt:  drop.AvgConfidence,
				Timestamp:     time.Now().UTC(),
			})

			mergedIDs[drop.ID] = true
			merged++
			break // i absorbed j; move to next i
		}
	}
	return merged, nil
}

// PruneCheck marks stale low-confidence domains as DORMANT, and domains with
// zero surviving SCL facts as ARCHIVED.
// Returns (dormant count, archived count, error).
func (m *ManifestMaintainer) PruneCheck(ctx context.Context) (int, int, error) {
	domains := m.Manifest.All()
	dormant, archived := 0, 0

	for _, d := range domains {
		if d.Status == StatusDormant || d.Status == StatusArchived {
			continue
		}

		// Archive: zero facts and not new
		if m.ArchiveIfZeroFacts && d.FactCount == 0 && d.IngestCount > 0 {
			d.Status = StatusArchived
			if err := m.Manifest.Update(ctx, d); err != nil {
				log.Printf("[TCD:Maintain] archive update %q: %v", d.Name, err)
				continue
			}
			m.Manifest.LogEvent(ctx, DomainEvent{
				Type:         EventPrune,
				FromDomainID: d.ID,
				Reason:       "archived:zero_facts",
				ConfidenceAt: d.AvgConfidence,
				Timestamp:    time.Now().UTC(),
			})
			archived++
			continue
		}

		// Dormant: low confidence + stale
		ageDays := 0.0
		if !d.LastIngested.IsZero() {
			ageDays = time.Since(d.LastIngested).Hours() / 24
		}
		if d.AvgConfidence < m.PruneMaxConfidence && ageDays > m.PruneMinStaleDays {
			d.Status = StatusDormant
			if err := m.Manifest.Update(ctx, d); err != nil {
				log.Printf("[TCD:Maintain] dormant update %q: %v", d.Name, err)
				continue
			}
			m.Manifest.LogEvent(ctx, DomainEvent{
				Type:         EventPrune,
				FromDomainID: d.ID,
				Reason:       fmt.Sprintf("dormant:conf=%.2f,age=%.0fd", d.AvgConfidence, ageDays),
				ConfidenceAt: d.AvgConfidence,
				Timestamp:    time.Now().UTC(),
			})
			dormant++
		}
	}
	return dormant, archived, nil
}

// ─── internal ─────────────────────────────────────────────────────────────────

func (m *ManifestMaintainer) foldInto(ctx context.Context, keep, drop *Domain) error {
	// Absorb drop's keywords into keep (deduplicated).
	kwSet := make(map[string]bool)
	for _, kw := range keep.Keywords {
		kwSet[kw] = true
	}
	for _, kw := range drop.Keywords {
		if !kwSet[kw] {
			keep.Keywords = append(keep.Keywords, kw)
		}
	}
	keep.Merges = append(keep.Merges, drop.ID)
	keep.FactCount += drop.FactCount

	// Re-average confidence.
	if drop.FactCount+keep.FactCount > 0 {
		keep.AvgConfidence = (keep.AvgConfidence*float64(keep.FactCount-drop.FactCount) +
			drop.AvgConfidence*float64(drop.FactCount)) /
			float64(keep.FactCount)
	}

	if err := m.Manifest.Update(ctx, keep); err != nil {
		return fmt.Errorf("update keep domain: %w", err)
	}

	drop.Status = StatusArchived
	drop.SpawnedFrom = keep.ID // redirect pointer
	if err := m.Manifest.Update(ctx, drop); err != nil {
		return fmt.Errorf("archive drop domain: %w", err)
	}
	return nil
}

func joinKeywords(kws []string) string {
	result := ""
	for i, kw := range kws {
		if i > 0 {
			result += " "
		}
		result += kw
	}
	return result
}

func keywordOverlapScore(a, b []string) float64 {
	if len(a) == 0 || len(b) == 0 {
		return 0
	}
	setB := make(map[string]bool, len(b))
	for _, kw := range b {
		setB[kw] = true
	}
	matches := 0
	for _, kw := range a {
		if setB[kw] {
			matches++
		}
	}
	// Jaccard-like: matches / union
	union := len(a) + len(b) - matches
	if union == 0 {
		return 0
	}
	return float64(matches) / float64(union)
}
