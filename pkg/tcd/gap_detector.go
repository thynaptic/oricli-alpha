package tcd

import (
	"context"
	"fmt"
	"log"
	"math"
	"strings"
	"time"
)

// ─────────────────────────────────────────────────────────────────────────────
// GapDetector
// ─────────────────────────────────────────────────────────────────────────────

// OrphanFact is an SCL fact whose subject doesn't match any known domain keyword.
type OrphanFact struct {
	ID        string
	Subject   string
	Content   string
	Embedding []float32
}

// OrphanCluster is a group of orphan facts similar enough to form a new domain.
type OrphanCluster struct {
	Facts      []OrphanFact
	CentroidKW string    // most representative keyword (highest mean similarity)
	Strength   float64   // avg intra-cluster similarity
}

// SCLOrphanReader is the interface GapDetector uses to query the SCL.
// Implemented by scl.Ledger — defined here to avoid import cycle.
type SCLOrphanReader interface {
	QueryOrphans(ctx context.Context, limit int) ([]OrphanFact, error)
}

// GapDetector scans SCL for facts that don't belong to any known domain,
// clusters them by embedding similarity, and spawns new domains when a
// cluster is large enough.
type GapDetector struct {
	Manifest *DomainManifest
	SCL      SCLOrphanReader

	// SpawnThreshold is the minimum cluster size before a new domain is created.
	// Default: 5. Higher = more conservative, fewer false spawns.
	SpawnThreshold int

	// ClusterSimilarity is the minimum cosine similarity to group two orphans.
	// Default: 0.75.
	ClusterSimilarity float64
}

// NewGapDetector returns a GapDetector with sensible defaults.
func NewGapDetector(manifest *DomainManifest, scl SCLOrphanReader) *GapDetector {
	return &GapDetector{
		Manifest:          manifest,
		SCL:               scl,
		SpawnThreshold:    5,
		ClusterSimilarity: 0.75,
	}
}

// Scan runs a full orphan detection + clustering + spawn cycle.
// Returns the number of new domains spawned.
func (g *GapDetector) Scan(ctx context.Context) (int, error) {
	orphans, err := g.ScanOrphans(ctx)
	if err != nil {
		return 0, fmt.Errorf("gap scan orphans: %w", err)
	}
	if len(orphans) == 0 {
		return 0, nil
	}

	clusters := g.ClusterOrphans(orphans)
	spawned := 0
	for _, cl := range clusters {
		if len(cl.Facts) < g.SpawnThreshold {
			continue
		}
		if err := g.SpawnDomain(ctx, cl); err != nil {
			log.Printf("[TCD:Gap] spawn error: %v", err)
			continue
		}
		spawned++
	}
	return spawned, nil
}

// ScanOrphans queries the SCL for facts whose subject doesn't match any
// keyword in any active domain.
func (g *GapDetector) ScanOrphans(ctx context.Context) ([]OrphanFact, error) {
	if g.SCL == nil {
		return nil, nil
	}
	candidates, err := g.SCL.QueryOrphans(ctx, 200)
	if err != nil {
		return nil, err
	}

	var orphans []OrphanFact
	for _, f := range candidates {
		if g.Manifest.FindByKeyword(f.Subject) == nil {
			orphans = append(orphans, f)
		}
	}
	log.Printf("[TCD:Gap] Found %d/%d orphan facts (no matching domain)", len(orphans), len(candidates))
	return orphans, nil
}

// ClusterOrphans groups orphan facts using greedy agglomerative clustering.
// Facts with embedding cosine similarity ≥ ClusterSimilarity are grouped together.
func (g *GapDetector) ClusterOrphans(orphans []OrphanFact) []OrphanCluster {
	if len(orphans) == 0 {
		return nil
	}

	assigned := make([]bool, len(orphans))
	var clusters []OrphanCluster

	for i := range orphans {
		if assigned[i] {
			continue
		}
		cl := OrphanCluster{Facts: []OrphanFact{orphans[i]}}
		assigned[i] = true

		for j := i + 1; j < len(orphans); j++ {
			if assigned[j] {
				continue
			}
			if len(orphans[i].Embedding) > 0 && len(orphans[j].Embedding) > 0 {
				if cosineSim(orphans[i].Embedding, orphans[j].Embedding) >= g.ClusterSimilarity {
					cl.Facts = append(cl.Facts, orphans[j])
					assigned[j] = true
				}
			} else {
				// Fallback: subject keyword overlap
				if subjectOverlap(orphans[i].Subject, orphans[j].Subject) {
					cl.Facts = append(cl.Facts, orphans[j])
					assigned[j] = true
				}
			}
		}

		cl.CentroidKW = g.extractCentroidKeyword(cl.Facts)
		cl.Strength = g.clusterStrength(cl.Facts)
		clusters = append(clusters, cl)
	}
	return clusters
}

// SpawnDomain creates a new Domain from an orphan cluster, logs the lineage event,
// and adds it to the manifest with StatusProbation.
func (g *GapDetector) SpawnDomain(ctx context.Context, cl OrphanCluster) error {
	// Derive keywords from the cluster's subject strings.
	kwSet := make(map[string]struct{})
	for _, f := range cl.Facts {
		for _, w := range extractKeywords(f.Subject) {
			kwSet[w] = struct{}{}
		}
	}
	keywords := make([]string, 0, len(kwSet))
	for kw := range kwSet {
		keywords = append(keywords, kw)
	}
	if len(keywords) == 0 {
		keywords = []string{cl.CentroidKW}
	}

	d := &Domain{
		Name:          titleCase(cl.CentroidKW),
		Keywords:      keywords,
		Status:        StatusProbation,
		SourceWeights: DefaultSourceWeights,
	}

	if err := g.Manifest.Add(ctx, d); err != nil {
		return fmt.Errorf("spawn domain %q: %w", d.Name, err)
	}

	// Log the lineage event.
	g.Manifest.LogEvent(ctx, DomainEvent{
		Type:         EventSpawn,
		FromDomainID: d.ID, // orphan → new domain
		Reason:       fmt.Sprintf("gap_detected:%d_orphans", len(cl.Facts)),
		Timestamp:    time.Now().UTC(),
	})

	log.Printf("[TCD:Gap] Spawned domain %q (probation) from %d orphan facts — keywords: %v",
		d.Name, len(cl.Facts), keywords)
	return nil
}

// ─── helpers ─────────────────────────────────────────────────────────────────

func (g *GapDetector) extractCentroidKeyword(facts []OrphanFact) string {
	// Most common word across all subjects (excluding stop words).
	freq := make(map[string]int)
	for _, f := range facts {
		for _, w := range extractKeywords(f.Subject) {
			freq[w]++
		}
	}
	best, bestN := "", 0
	for w, n := range freq {
		if n > bestN {
			best, bestN = w, n
		}
	}
	if best == "" && len(facts) > 0 {
		return facts[0].Subject
	}
	return best
}

func (g *GapDetector) clusterStrength(facts []OrphanFact) float64 {
	if len(facts) < 2 {
		return 1.0
	}
	total, count := 0.0, 0
	for i := range facts {
		for j := i + 1; j < len(facts); j++ {
			if len(facts[i].Embedding) > 0 && len(facts[j].Embedding) > 0 {
				total += cosineSim(facts[i].Embedding, facts[j].Embedding)
				count++
			}
		}
	}
	if count == 0 {
		return 0.5
	}
	return total / float64(count)
}

var stopWords = map[string]bool{
	"the": true, "a": true, "an": true, "and": true, "or": true,
	"of": true, "in": true, "on": true, "at": true, "to": true,
	"is": true, "are": true, "was": true, "for": true, "with": true,
}

func extractKeywords(s string) []string {
	words := strings.Fields(strings.ToLower(s))
	var out []string
	for _, w := range words {
		w = strings.Trim(w, ".,;:!?\"'()")
		if len(w) > 3 && !stopWords[w] {
			out = append(out, w)
		}
	}
	return out
}

func subjectOverlap(a, b string) bool {
	kwA := extractKeywords(a)
	kwB := make(map[string]bool)
	for _, w := range extractKeywords(b) {
		kwB[w] = true
	}
	for _, w := range kwA {
		if kwB[w] {
			return true
		}
	}
	return false
}

func titleCase(s string) string {
	if s == "" {
		return s
	}
	words := strings.Fields(s)
	for i, w := range words {
		if len(w) > 0 {
			words[i] = strings.ToUpper(w[:1]) + w[1:]
		}
	}
	return strings.Join(words, " ")
}

func cosineSim(a, b []float32) float64 {
	if len(a) != len(b) || len(a) == 0 {
		return 0
	}
	var dot, normA, normB float64
	for i := range a {
		dot += float64(a[i]) * float64(b[i])
		normA += float64(a[i]) * float64(a[i])
		normB += float64(b[i]) * float64(b[i])
	}
	denom := math.Sqrt(normA) * math.Sqrt(normB)
	if denom == 0 {
		return 0
	}
	return dot / denom
}
