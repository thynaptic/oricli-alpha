// Package scl implements the Sovereign Cognitive Ledger — a tiered, versioned,
// hot-queryable knowledge substrate that replaces weight-based training.
//
// Architecture axiom: the LLM (Ollama) is a pure reasoning engine.
// All domain-specific knowledge lives here, is inspectable, revisable, and auditable.
//
//	Write path: agent verifies fact → Ledger.Write() → dedup check → PB record
//	Read path:  query → embed → tiered fan-out → cosine rank → context window
package scl

import (
	"context"
	"fmt"
	"log"
	"math"
	"os"
	"strings"
	"sync"
	"time"

	pb "github.com/thynaptic/oricli-go/pkg/connectors/pocketbase"
)

// ---------------------------------------------------------------------------
// Tier constants — every record belongs to exactly one tier.
// ---------------------------------------------------------------------------

type Tier string

const (
	TierFacts       Tier = "facts"       // world knowledge: web-verified, user-stated, swarm-universal
	TierSkills      Tier = "skills"      // procedural "how to" traces from ESI and LearningSystem
	TierCorrections Tier = "corrections" // explicit override rules: "when X, do Y not Z"
	TierPreferences Tier = "preferences" // tone, style, behavioral tuning per owner/tenant
	TierRelations   Tier = "relations"   // knowledge graph edges (subject → predicate → object)
)

// TierPriority controls injection order in the context window.
// Lower index = injected first (highest priority).
var TierPriority = []Tier{TierCorrections, TierPreferences, TierFacts, TierSkills, TierRelations}

// ---------------------------------------------------------------------------
// Provenance — matches MemoryBank provenance for cross-system consistency.
// ---------------------------------------------------------------------------

type Provenance string

const (
	ProvenanceUserStated  Provenance = "user_stated"  // owner explicitly stated this (anchor — never decayed)
	ProvenanceWebVerified Provenance = "web_verified"  // retrieved from a live URL with timestamp
	ProvenanceSwarmUniversal Provenance = "swarm_universal" // validated by 3+ independent swarm nodes
	ProvenanceSynthetic   Provenance = "synthetic"    // curiosity/summarisation derived
	ProvenancePeer        Provenance = "peer"          // ESI skill trace from peer node
	ProvenanceGold        Provenance = "gold"          // 0.95+ confidence, never decayed
)

// provenanceWeight controls RAG ranking multiplier per provenance level.
var provenanceWeight = map[Provenance]float64{
	ProvenanceUserStated:     1.5,
	ProvenanceSwarmUniversal: 1.4,
	ProvenanceGold:           1.3,
	ProvenanceWebVerified:    1.2,
	ProvenancePeer:           0.9,
	ProvenanceSynthetic:      0.7,
}

func (p Provenance) Weight() float64 {
	if w, ok := provenanceWeight[p]; ok {
		return w
	}
	return 0.8
}

// ---------------------------------------------------------------------------
// SCLRecord — the canonical knowledge unit.
// ---------------------------------------------------------------------------

type SCLRecord struct {
	ID           string     `json:"id"`
	Tier         Tier       `json:"tier"`
	Content      string     `json:"content"`      // human-readable knowledge text
	Subject      string     `json:"subject"`      // topic / category for tier-scoped recall
	Provenance   Provenance `json:"provenance"`
	Confidence   float64    `json:"confidence"`   // 0.0–1.0; source quality × corroboration
	Author       string     `json:"author"`       // which agent or user wrote this
	Tags         []string   `json:"tags"`
	SupersededBy string     `json:"superseded_by,omitempty"` // set on Revise(); points to new record ID
	Embedding    []float32  `json:"embedding,omitempty"`     // populated async
	CreatedAt    time.Time  `json:"created_at"`
	UpdatedAt    time.Time  `json:"updated_at"`
}

// Score returns the composite ranking score for retrieval.
// score = confidence × provenanceWeight × semanticSimilarity
func (r *SCLRecord) Score(similarity float64) float64 {
	return r.Confidence * r.Provenance.Weight() * similarity
}

// ---------------------------------------------------------------------------
// Ledger — the unified read/write API.
// ---------------------------------------------------------------------------

// Ledger is the single interface all agents use to read and write knowledge.
// It wraps PocketBase for durable storage and uses the Embedder for dedup.
type Ledger struct {
	client  *pb.Client
	embedder Embedder
	mu      sync.RWMutex
	enabled bool
}

// Embedder is a minimal interface so Ledger doesn't import pkg/service (cycle).
type Embedder interface {
	Embed(ctx context.Context, text string) []float32
}

const sclCollection = "scl_records"

// New creates a Ledger backed by the provided PocketBase admin client.
func New(client *pb.Client, embedder Embedder) *Ledger {
	l := &Ledger{
		client:   client,
		embedder: embedder,
		enabled:  client != nil && client.IsConfigured(),
	}
	if embedder == nil {
		l.embedder = noopEmbedder{}
	}
	return l
}

type noopEmbedder struct{}

func (noopEmbedder) Embed(_ context.Context, _ string) []float32 { return nil }

// IsEnabled returns true if PocketBase is configured and the ledger is usable.
func (l *Ledger) IsEnabled() bool { return l.enabled }

// Bootstrap ensures the scl_records collection exists in PocketBase.
func (l *Ledger) Bootstrap(ctx context.Context) error {
	if !l.enabled {
		return nil
	}
	exists, err := l.client.CollectionExists(ctx, sclCollection)
	if err != nil {
		return fmt.Errorf("scl bootstrap: %w", err)
	}
	if exists {
		return nil
	}
	schema := pb.CollectionSchema{
		Name: sclCollection,
		Type: "base",
		Schema: []pb.FieldSchema{
			{Name: "tier", Type: "text"},
			{Name: "content", Type: "text"},
			{Name: "subject", Type: "text"},
			{Name: "provenance", Type: "text"},
			{Name: "confidence", Type: "number"},
			{Name: "author", Type: "text"},
			{Name: "tags", Type: "text"},  // comma-separated
			{Name: "superseded_by", Type: "text"},
			{Name: "embedding", Type: "json", Options: map[string]any{"maxSize": 2000000}},
		},
	}
	if err := l.client.CreateCollection(ctx, schema); err != nil {
		return fmt.Errorf("scl create collection: %w", err)
	}
	log.Printf("[SCL] Collection %q created.", sclCollection)
	return nil
}

// ---------------------------------------------------------------------------
// Write — the only write path for all agents.
// ---------------------------------------------------------------------------

// Write inserts or updates a knowledge record.
// Dedup logic: if a record in the same tier+subject already has cosine similarity
// ≥ 0.92 to the new content, the existing record is updated (confidence bumped,
// content refreshed) rather than creating a duplicate.
func (l *Ledger) Write(ctx context.Context, r SCLRecord) (string, error) {
	if !l.enabled {
		return "", nil
	}
	if r.Content == "" || r.Tier == "" {
		return "", fmt.Errorf("scl write: content and tier are required")
	}
	if r.Confidence == 0 {
		r.Confidence = defaultConfidence(r.Provenance)
	}
	if r.Author == "" {
		r.Author = "oricli"
	}

	// Generate embedding for dedup check + future retrieval.
	vec := l.embedder.Embed(ctx, r.Content)

	// Dedup: check existing records in the same tier+subject.
	if existing := l.findDuplicate(ctx, r.Tier, r.Subject, vec); existing != "" {
		// Update in place — bump confidence slightly, refresh content.
		newConf := math.Min(1.0, r.Confidence+0.02)
		err := l.client.UpdateRecord(ctx, sclCollection, existing, map[string]any{
			"content":    r.Content,
			"confidence": newConf,
			"provenance": string(r.Provenance),
			"author":     r.Author,
			"embedding":  float32SliceToJSON(vec),
			"updated":    time.Now().UTC().Format(time.RFC3339),
		})
		if err != nil {
			return "", fmt.Errorf("scl dedup update: %w", err)
		}
		return existing, nil
	}

	// New record.
	data := map[string]any{
		"tier":       string(r.Tier),
		"content":    r.Content,
		"subject":    r.Subject,
		"provenance": string(r.Provenance),
		"confidence": r.Confidence,
		"author":     r.Author,
		"tags":       strings.Join(r.Tags, ","),
		"embedding":  float32SliceToJSON(vec),
	}
	id, err := l.client.CreateRecord(ctx, sclCollection, data)
	if err != nil {
		// Lazy collection creation: retry once after bootstrapping.
		if bErr := l.Bootstrap(ctx); bErr == nil {
			id, err = l.client.CreateRecord(ctx, sclCollection, data)
		}
		if err != nil {
			return "", fmt.Errorf("scl write: %w", err)
		}
	}
	return id, nil
}

// ---------------------------------------------------------------------------
// Read — tiered fan-out retrieval.
// ---------------------------------------------------------------------------

// Read retrieves the topK most relevant records across the specified tiers.
// If tiers is empty, all tiers are searched.
// Records are ranked by: confidence × provenance_weight × cosine_similarity.
func (l *Ledger) Read(ctx context.Context, query string, tiers []Tier, topK int) ([]SCLRecord, error) {
	if !l.enabled {
		return nil, nil
	}
	if topK <= 0 {
		topK = 5
	}
	if len(tiers) == 0 {
		tiers = TierPriority
	}

	queryVec := l.embedder.Embed(ctx, query)

	var mu sync.Mutex
	var all []scoredRecord

	// Fan-out: query each tier in parallel.
	var wg sync.WaitGroup
	for _, tier := range tiers {
		wg.Add(1)
		go func(t Tier) {
			defer wg.Done()
			recs, err := l.fetchTier(ctx, t, query, 30)
			if err != nil {
				log.Printf("[SCL] read tier %s: %v", t, err)
				return
			}
			for _, rec := range recs {
				sim := cosineSimilarity(queryVec, rec.Embedding)
				score := rec.Score(sim)
				if score > 0.01 { // filter noise
					mu.Lock()
					all = append(all, scoredRecord{rec, score})
					mu.Unlock()
				}
			}
		}(tier)
	}
	wg.Wait()

	// Sort by score descending.
	sortScoredRecords(all)

	// Dedup by content prefix (first 80 chars) — prevents near-duplicate injection.
	seen := make(map[string]bool)
	var results []SCLRecord
	for _, sr := range all {
		key := contentKey(sr.Record.Content)
		if seen[key] {
			continue
		}
		seen[key] = true
		results = append(results, sr.Record)
		if len(results) >= topK {
			break
		}
	}
	return results, nil
}

// ---------------------------------------------------------------------------
// Delete + Revise
// ---------------------------------------------------------------------------

// Delete hard-deletes a record by ID. This is the "why does she think X? → kill it" operation.
func (l *Ledger) Delete(ctx context.Context, id string) error {
	if !l.enabled {
		return nil
	}
	if err := l.client.DeleteRecord(ctx, sclCollection, id); err != nil {
		return fmt.Errorf("scl delete %s: %w", id, err)
	}
	log.Printf("[SCL] Record %s deleted.", id)
	return nil
}

// Revise updates the content of a record, preserving the old content in a
// companion record marked superseded_by=newID. Full audit trail preserved.
func (l *Ledger) Revise(ctx context.Context, id, newContent string, newConfidence float64) (string, error) {
	if !l.enabled {
		return "", nil
	}
	// Fetch the existing record.
	raw, err := l.client.GetRecord(ctx, sclCollection, id)
	if err != nil {
		return "", fmt.Errorf("scl revise fetch: %w", err)
	}
	tier, _ := raw["tier"].(string)
	subject, _ := raw["subject"].(string)
	provStr, _ := raw["provenance"].(string)
	author, _ := raw["author"].(string)

	// Write new record.
	newID, err := l.Write(ctx, SCLRecord{
		Tier:       Tier(tier),
		Content:    newContent,
		Subject:    subject,
		Provenance: Provenance(provStr),
		Confidence: newConfidence,
		Author:     author + ":revised",
	})
	if err != nil {
		return "", fmt.Errorf("scl revise write: %w", err)
	}

	// Mark old record as superseded.
	_ = l.client.UpdateRecord(ctx, sclCollection, id, map[string]any{
		"superseded_by": newID,
		"confidence":    0.0, // suppress from retrieval
	})

	log.Printf("[SCL] Record %s revised → %s", id, newID)
	return newID, nil
}

// ---------------------------------------------------------------------------
// Maintenance operations (called by DreamDaemon)
// ---------------------------------------------------------------------------

// Deduplicate scans all records and merges pairs with cosine similarity ≥ threshold.
// The record with higher confidence is kept; the other is marked superseded.
// Returns the number of pairs merged.
func (l *Ledger) Deduplicate(ctx context.Context, threshold float64) (int, error) {
	if !l.enabled {
		return 0, nil
	}
	if threshold <= 0 {
		threshold = 0.95
	}
	total := 0
	for _, tier := range TierPriority {
		n, err := l.deduplicateTier(ctx, tier, threshold)
		if err != nil {
			log.Printf("[SCL] dedup tier %s: %v", tier, err)
			continue
		}
		total += n
	}
	return total, nil
}

// DecayStale lowers confidence by decayRate on records not updated in staleDays.
// Records at ProvenanceUserStated or ProvenanceGold are immune.
func (l *Ledger) DecayStale(ctx context.Context, staleDays int, decayRate float64) (int, error) {
	if !l.enabled {
		return 0, nil
	}
	if staleDays <= 0 {
		staleDays = 30
	}
	if decayRate <= 0 {
		decayRate = 0.05
	}
	cutoff := time.Now().AddDate(0, 0, -staleDays).Format("2006-01-02")
	filter := fmt.Sprintf("updated<='%s' && provenance!='user_stated' && provenance!='gold' && confidence>0.1", cutoff)
	result, err := l.client.QueryRecords(ctx, sclCollection, filter, "-confidence", 500)
	if err != nil {
		return 0, fmt.Errorf("scl decay query: %w", err)
	}
	n := 0
	for _, item := range result.Items {
		id, _ := item["id"].(string)
		conf, _ := item["confidence"].(float64)
		newConf := math.Max(0.1, conf-decayRate)
		if err := l.client.UpdateRecord(ctx, sclCollection, id, map[string]any{"confidence": newConf}); err == nil {
			n++
		}
	}
	return n, nil
}

// PromoteHighConfidence promotes records that have reached ≥ threshold confidence
// to ProvenanceGold so they are immune to decay and get top RAG weight.
func (l *Ledger) PromoteHighConfidence(ctx context.Context, threshold float64) (int, error) {
	if !l.enabled {
		return 0, nil
	}
	if threshold <= 0 {
		threshold = 0.95
	}
	filter := fmt.Sprintf("confidence>=%f && provenance!='gold' && provenance!='user_stated'", threshold)
	result, err := l.client.QueryRecords(ctx, sclCollection, filter, "-confidence", 200)
	if err != nil {
		return 0, fmt.Errorf("scl promote query: %w", err)
	}
	n := 0
	for _, item := range result.Items {
		id, _ := item["id"].(string)
		if err := l.client.UpdateRecord(ctx, sclCollection, id, map[string]any{
			"provenance": string(ProvenanceGold),
		}); err == nil {
			n++
		}
	}
	if n > 0 {
		log.Printf("[SCL] Promoted %d records to gold tier.", n)
	}
	return n, nil
}

// ---------------------------------------------------------------------------
// Stats (for admin API)
// ---------------------------------------------------------------------------

type Stats struct {
	TotalRecords    int            `json:"total_records"`
	ByTier          map[string]int `json:"by_tier"`
	AvgConfidence   float64        `json:"avg_confidence"`
	StaleCount      int            `json:"stale_count"`
	GoldCount       int            `json:"gold_count"`
}

func (l *Ledger) Stats(ctx context.Context) Stats {
	s := Stats{ByTier: make(map[string]int)}
	if !l.enabled {
		return s
	}
	staleCutoff := time.Now().AddDate(0, 0, -30).Format("2006-01-02")
	for _, tier := range TierPriority {
		res, err := l.client.QueryRecords(ctx, sclCollection, "tier='"+string(tier)+"' && superseded_by=''", "", 1)
		if err == nil {
			s.ByTier[string(tier)] = res.TotalItems
			s.TotalRecords += res.TotalItems
		}
	}
	// avg confidence
	res, err := l.client.QueryRecords(ctx, sclCollection, "superseded_by=''", "-confidence", 500)
	if err == nil && len(res.Items) > 0 {
		var sum float64
		for _, item := range res.Items {
			if c, ok := item["confidence"].(float64); ok {
				sum += c
			}
		}
		s.AvgConfidence = sum / float64(len(res.Items))
	}
	// stale
	if res2, err2 := l.client.QueryRecords(ctx, sclCollection, "updated<='"+staleCutoff+"' && superseded_by=''", "", 1); err2 == nil {
		s.StaleCount = res2.TotalItems
	}
	// gold
	if res3, err3 := l.client.QueryRecords(ctx, sclCollection, "provenance='gold' && superseded_by=''", "", 1); err3 == nil {
		s.GoldCount = res3.TotalItems
	}
	return s
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

type scoredRecord struct {
	Record SCLRecord
	Score  float64
}

func sortScoredRecords(recs []scoredRecord) {
	// Simple insertion sort — typical topK is ≤ 50, so O(n²) is fine.
	for i := 1; i < len(recs); i++ {
		key := recs[i]
		j := i - 1
		for j >= 0 && recs[j].Score < key.Score {
			recs[j+1] = recs[j]
			j--
		}
		recs[j+1] = key
	}
}

func contentKey(s string) string {
	if len(s) > 80 {
		return s[:80]
	}
	return s
}

func defaultConfidence(p Provenance) float64 {
	switch p {
	case ProvenanceUserStated, ProvenanceSwarmUniversal:
		return 0.9
	case ProvenanceWebVerified, ProvenanceGold:
		return 0.85
	case ProvenancePeer:
		return 0.75
	default:
		return 0.65
	}
}

// findDuplicate checks if an embedding is within threshold of any existing record
// in the same tier+subject. Returns the matching ID or "".
func (l *Ledger) findDuplicate(ctx context.Context, tier Tier, subject string, vec []float32) string {
	if len(vec) == 0 {
		return ""
	}
	filter := "tier='" + string(tier) + "' && superseded_by=''"
	if subject != "" {
		filter += " && subject='" + subject + "'"
	}
	result, err := l.client.QueryRecords(ctx, sclCollection, filter, "-confidence", 30)
	if err != nil || len(result.Items) == 0 {
		return ""
	}
	const dupThreshold = 0.92
	for _, item := range result.Items {
		existing := jsonToFloat32Slice(item["embedding"])
		if len(existing) == 0 {
			continue
		}
		if cosineSimilarity(vec, existing) >= dupThreshold {
			if id, ok := item["id"].(string); ok {
				return id
			}
		}
	}
	return ""
}

func (l *Ledger) fetchTier(ctx context.Context, tier Tier, _ string, limit int) ([]SCLRecord, error) {
	filter := "tier='" + string(tier) + "' && superseded_by='' && confidence>0.1"
	result, err := l.client.QueryRecords(ctx, sclCollection, filter, "-confidence,-updated", limit)
	if err != nil {
		// Lazy collection creation: retry once after bootstrapping.
		if bErr := l.Bootstrap(ctx); bErr == nil {
			result, err = l.client.QueryRecords(ctx, sclCollection, filter, "-confidence,-updated", limit)
		}
		if err != nil {
			return nil, err
		}
	}
	var recs []SCLRecord
	for _, item := range result.Items {
		recs = append(recs, itemToRecord(item))
	}
	return recs, nil
}

func (l *Ledger) deduplicateTier(ctx context.Context, tier Tier, threshold float64) (int, error) {
	recs, err := l.fetchTier(ctx, tier, "", 200)
	if err != nil {
		return 0, err
	}
	merged := 0
	for i := 0; i < len(recs); i++ {
		for j := i + 1; j < len(recs); j++ {
			if len(recs[i].Embedding) == 0 || len(recs[j].Embedding) == 0 {
				continue
			}
			if cosineSimilarity(recs[i].Embedding, recs[j].Embedding) < threshold {
				continue
			}
			// Keep higher confidence; suppress lower.
			keep, drop := recs[i], recs[j]
			if recs[j].Confidence > recs[i].Confidence {
				keep, drop = recs[j], recs[i]
			}
			if drop.ID == "" {
				continue
			}
			_ = l.client.UpdateRecord(ctx, sclCollection, drop.ID, map[string]any{
				"superseded_by": keep.ID,
				"confidence":    0.0,
			})
			merged++
		}
	}
	return merged, nil
}

func itemToRecord(item map[string]any) SCLRecord {
	r := SCLRecord{}
	r.ID, _ = item["id"].(string)
	r.Content, _ = item["content"].(string)
	r.Subject, _ = item["subject"].(string)
	r.Author, _ = item["author"].(string)
	r.SupersededBy, _ = item["superseded_by"].(string)
	if tier, ok := item["tier"].(string); ok {
		r.Tier = Tier(tier)
	}
	if prov, ok := item["provenance"].(string); ok {
		r.Provenance = Provenance(prov)
	}
	if conf, ok := item["confidence"].(float64); ok {
		r.Confidence = conf
	}
	if tags, ok := item["tags"].(string); ok && tags != "" {
		r.Tags = strings.Split(tags, ",")
	}
	r.Embedding = jsonToFloat32Slice(item["embedding"])
	return r
}

// ---------------------------------------------------------------------------
// Math helpers
// ---------------------------------------------------------------------------

func cosineSimilarity(a, b []float32) float64 {
	if len(a) == 0 || len(b) == 0 || len(a) != len(b) {
		return 0
	}
	var dot, normA, normB float64
	for i := range a {
		dot += float64(a[i]) * float64(b[i])
		normA += float64(a[i]) * float64(a[i])
		normB += float64(b[i]) * float64(b[i])
	}
	if normA == 0 || normB == 0 {
		return 0
	}
	return dot / (math.Sqrt(normA) * math.Sqrt(normB))
}

func float32SliceToJSON(v []float32) []float64 {
	if len(v) == 0 {
		return nil
	}
	out := make([]float64, len(v))
	for i, f := range v {
		out[i] = float64(f)
	}
	return out
}

func jsonToFloat32Slice(raw any) []float32 {
	switch v := raw.(type) {
	case []any:
		out := make([]float32, len(v))
		for i, x := range v {
			if f, ok := x.(float64); ok {
				out[i] = float32(f)
			}
		}
		return out
	case []float64:
		out := make([]float32, len(v))
		for i, f := range v {
			out[i] = float32(f)
		}
		return out
	}
	return nil
}

// ---------------------------------------------------------------------------
// Environment gating — mirrors MAVAIA_* convention
// ---------------------------------------------------------------------------

func IsEnabled() bool {
	pbURL := os.Getenv("POCKETBASE_URL")
	if pbURL == "" {
		pbURL = os.Getenv("MAVAIA_PB_URL")
	}
	return pbURL != ""
}
