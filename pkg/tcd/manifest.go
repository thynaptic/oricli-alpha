package tcd

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	pb "github.com/thynaptic/oricli-go/pkg/connectors/pocketbase"
	"github.com/google/uuid"
)

const (
	domainCollection = "tcd_domains"
	eventCollection  = "tcd_events"
)

// ─────────────────────────────────────────────────────────────────────────────
// DomainManifest
// ─────────────────────────────────────────────────────────────────────────────

// DomainManifest manages the full set of known domains and their lineage.
// It maintains an in-process cache for fast iteration and persists to PocketBase
// (same collection as SCL TierRelations) for durability and admin inspection.
type DomainManifest struct {
	client *pb.Client

	mu      sync.RWMutex
	domains map[string]*Domain      // id → Domain
	events  map[string][]DomainEvent // domainID → ordered event log
}

// NewDomainManifest creates a manifest backed by the given PocketBase client.
func NewDomainManifest(client *pb.Client) *DomainManifest {
	return &DomainManifest{
		client:  client,
		domains: make(map[string]*Domain),
		events:  make(map[string][]DomainEvent),
	}
}

// Bootstrap ensures PB collections exist and loads existing domains.
// If the manifest is empty, seeds the 10 default domains.
func (m *DomainManifest) Bootstrap(ctx context.Context) error {
	if err := m.ensureCollections(ctx); err != nil {
		return err
	}
	if err := m.load(ctx); err != nil {
		return err
	}

	m.mu.RLock()
	count := len(m.domains)
	m.mu.RUnlock()

	if count == 0 {
		log.Printf("[TCD] Manifest empty — seeding %d default domains", len(SeedDomains))
		for _, s := range SeedDomains {
			d := &Domain{
				ID:            uuid.New().String(),
				Name:          s.Name,
				Keywords:      s.Keywords,
				Status:        StatusActive,
				SourceWeights: DefaultSourceWeights,
			}
			if err := m.Add(ctx, d); err != nil {
				log.Printf("[TCD] Seed domain %q: %v", s.Name, err)
			}
		}
	}
	return nil
}

// ─── CRUD ─────────────────────────────────────────────────────────────────────

// Add inserts a new domain into the manifest and persists it.
func (m *DomainManifest) Add(ctx context.Context, d *Domain) error {
	if d.ID == "" {
		d.ID = uuid.New().String()
	}
	if len(d.SourceWeights) == 0 {
		d.SourceWeights = DefaultSourceWeights
	}

	data, err := m.domainToRecord(d)
	if err != nil {
		return err
	}
	id, err := m.client.CreateRecord(ctx, domainCollection, data)
	if err != nil {
		return fmt.Errorf("tcd manifest add: %w", err)
	}
	d.ID = id

	m.mu.Lock()
	m.domains[d.ID] = d
	m.mu.Unlock()
	return nil
}

// Update persists changes to an existing domain.
func (m *DomainManifest) Update(ctx context.Context, d *Domain) error {
	data, err := m.domainToRecord(d)
	if err != nil {
		return err
	}
	if err := m.client.UpdateRecord(ctx, domainCollection, d.ID, data); err != nil {
		return fmt.Errorf("tcd manifest update: %w", err)
	}
	m.mu.Lock()
	m.domains[d.ID] = d
	m.mu.Unlock()
	return nil
}

// Get returns a domain by ID (from cache).
func (m *DomainManifest) Get(id string) (*Domain, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	d, ok := m.domains[id]
	return d, ok
}

// All returns all non-archived domains (copy slice, safe for iteration).
func (m *DomainManifest) All() []*Domain {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make([]*Domain, 0, len(m.domains))
	for _, d := range m.domains {
		if d.Status != StatusArchived {
			out = append(out, d)
		}
	}
	return out
}

// FindByKeyword returns the best-matching domain for a subject string.
// Returns nil if no domain keyword matches.
func (m *DomainManifest) FindByKeyword(subject string) *Domain {
	subjectLower := strings.ToLower(subject)
	m.mu.RLock()
	defer m.mu.RUnlock()
	for _, d := range m.domains {
		if d.Status == StatusArchived {
			continue
		}
		for _, kw := range d.Keywords {
			if strings.Contains(subjectLower, strings.ToLower(kw)) {
				return d
			}
		}
	}
	return nil
}

// ─── Lineage ──────────────────────────────────────────────────────────────────

// LogEvent appends a DomainEvent to the lineage log and persists it to PB.
func (m *DomainManifest) LogEvent(ctx context.Context, e DomainEvent) {
	if e.ID == "" {
		e.ID = uuid.New().String()
	}
	if e.Timestamp.IsZero() {
		e.Timestamp = time.Now().UTC()
	}

	data := map[string]any{
		"event_id":       e.ID,
		"type":           string(e.Type),
		"from_domain_id": e.FromDomainID,
		"to_domain_id":   e.ToDomainID,
		"timestamp":      e.Timestamp.Format(time.RFC3339),
		"reason":         e.Reason,
		"migrated_facts": e.MigratedFacts,
		"confidence_at":  e.ConfidenceAt,
	}
	if _, err := m.client.CreateRecord(ctx, eventCollection, data); err != nil {
		log.Printf("[TCD] LogEvent write error: %v", err)
	}

	m.mu.Lock()
	m.events[e.FromDomainID] = append(m.events[e.FromDomainID], e)
	if e.ToDomainID != "" {
		m.events[e.ToDomainID] = append(m.events[e.ToDomainID], e)
	}
	m.mu.Unlock()
}

// GetLineage returns the ordered event history for a domain.
// Includes events where the domain was the source OR destination.
func (m *DomainManifest) GetLineage(domainID string) []DomainEvent {
	m.mu.RLock()
	defer m.mu.RUnlock()
	evts := m.events[domainID]
	out := make([]DomainEvent, len(evts))
	copy(out, evts)
	return out
}

// GetEvolutionTree returns the full lineage DAG keyed by domain ID.
// Used by the admin viz endpoint GET /v1/tcd/lineage.
func (m *DomainManifest) GetEvolutionTree() map[string][]DomainEvent {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make(map[string][]DomainEvent, len(m.events))
	for id, evts := range m.events {
		cp := make([]DomainEvent, len(evts))
		copy(cp, evts)
		out[id] = cp
	}
	return out
}

// ─── Internal ─────────────────────────────────────────────────────────────────

func (m *DomainManifest) ensureCollections(ctx context.Context) error {
	domainExists, err := m.client.CollectionExists(ctx, domainCollection)
	if err != nil {
		return fmt.Errorf("tcd bootstrap: %w", err)
	}
	if !domainExists {
		if err := m.client.CreateCollection(ctx, pb.CollectionSchema{
			Name: domainCollection,
			Type: "base",
			Schema: []pb.FieldSchema{
				{Name: "name", Type: "text"},
				{Name: "keywords", Type: "text"},       // JSON array
				{Name: "status", Type: "text"},
				{Name: "avg_confidence", Type: "number"},
				{Name: "last_ingested", Type: "text"},
				{Name: "ingest_count", Type: "number"},
				{Name: "fact_count", Type: "number"},
				{Name: "spawned_from", Type: "text"},
				{Name: "merges", Type: "text"},          // JSON array of IDs
				{Name: "source_weights", Type: "json", Options: map[string]any{"maxSize": 64000}},
			},
		}); err != nil {
			return fmt.Errorf("tcd create domains collection: %w", err)
		}
		log.Printf("[TCD] Collection %q created.", domainCollection)
	}

	eventExists, err := m.client.CollectionExists(ctx, eventCollection)
	if err != nil {
		return err
	}
	if !eventExists {
		if err := m.client.CreateCollection(ctx, pb.CollectionSchema{
			Name: eventCollection,
			Type: "base",
			Schema: []pb.FieldSchema{
				{Name: "event_id", Type: "text"},
				{Name: "type", Type: "text"},
				{Name: "from_domain_id", Type: "text"},
				{Name: "to_domain_id", Type: "text"},
				{Name: "timestamp", Type: "text"},
				{Name: "reason", Type: "text"},
				{Name: "migrated_facts", Type: "number"},
				{Name: "confidence_at", Type: "number"},
			},
		}); err != nil {
			return fmt.Errorf("tcd create events collection: %w", err)
		}
		log.Printf("[TCD] Collection %q created.", eventCollection)
	}
	return nil
}

func (m *DomainManifest) load(ctx context.Context) error {
	// Load domains
	result, err := m.client.QueryRecords(ctx, domainCollection, "status!='archived'", "-avg_confidence", 200)
	if err != nil {
		return fmt.Errorf("tcd load domains: %w", err)
	}
	m.mu.Lock()
	for _, item := range result.Items {
		d := m.recordToDomain(item)
		m.domains[d.ID] = d
	}
	m.mu.Unlock()

	// Load recent events (last 500)
	evtResult, err := m.client.QueryRecords(ctx, eventCollection, "", "-timestamp", 500)
	if err != nil {
		log.Printf("[TCD] Could not load events: %v", err)
		return nil
	}
	m.mu.Lock()
	for _, item := range evtResult.Items {
		e := m.recordToEvent(item)
		if e.FromDomainID != "" {
			m.events[e.FromDomainID] = append(m.events[e.FromDomainID], e)
		}
		if e.ToDomainID != "" {
			m.events[e.ToDomainID] = append(m.events[e.ToDomainID], e)
		}
	}
	m.mu.Unlock()

	log.Printf("[TCD] Loaded %d domains, %d event chains", len(m.domains), len(m.events))
	return nil
}

func (m *DomainManifest) domainToRecord(d *Domain) (map[string]any, error) {
	kwJSON, _ := json.Marshal(d.Keywords)
	mergesJSON, _ := json.Marshal(d.Merges)
	swJSON, _ := json.Marshal(d.SourceWeights)

	li := ""
	if !d.LastIngested.IsZero() {
		li = d.LastIngested.Format(time.RFC3339)
	}

	return map[string]any{
		"name":           d.Name,
		"keywords":       string(kwJSON),
		"status":         string(d.Status),
		"avg_confidence": d.AvgConfidence,
		"last_ingested":  li,
		"ingest_count":   d.IngestCount,
		"fact_count":     d.FactCount,
		"spawned_from":   d.SpawnedFrom,
		"merges":         string(mergesJSON),
		"source_weights": json.RawMessage(swJSON),
	}, nil
}

func (m *DomainManifest) recordToDomain(item map[string]any) *Domain {
	d := &Domain{
		ID:            str(item["id"]),
		Name:          str(item["name"]),
		Status:        DomainStatus(str(item["status"])),
		AvgConfidence: float64Val(item["avg_confidence"]),
		IngestCount:   intVal(item["ingest_count"]),
		FactCount:     intVal(item["fact_count"]),
		SpawnedFrom:   str(item["spawned_from"]),
	}
	if li := str(item["last_ingested"]); li != "" {
		if t, err := time.Parse(time.RFC3339, li); err == nil {
			d.LastIngested = t
		}
	}
	if kw := str(item["keywords"]); kw != "" {
		_ = json.Unmarshal([]byte(kw), &d.Keywords)
	}
	if mg := str(item["merges"]); mg != "" {
		_ = json.Unmarshal([]byte(mg), &d.Merges)
	}
	if sw, ok := item["source_weights"]; ok {
		b, _ := json.Marshal(sw)
		_ = json.Unmarshal(b, &d.SourceWeights)
	}
	if len(d.SourceWeights) == 0 {
		d.SourceWeights = DefaultSourceWeights
	}
	return d
}

func (m *DomainManifest) recordToEvent(item map[string]any) DomainEvent {
	e := DomainEvent{
		ID:            str(item["event_id"]),
		Type:          EventType(str(item["type"])),
		FromDomainID:  str(item["from_domain_id"]),
		ToDomainID:    str(item["to_domain_id"]),
		Reason:        str(item["reason"]),
		MigratedFacts: intVal(item["migrated_facts"]),
		ConfidenceAt:  float64Val(item["confidence_at"]),
	}
	if ts := str(item["timestamp"]); ts != "" {
		if t, err := time.Parse(time.RFC3339, ts); err == nil {
			e.Timestamp = t
		}
	}
	return e
}

// ─── helpers ─────────────────────────────────────────────────────────────────

func str(v any) string {
	if v == nil {
		return ""
	}
	if s, ok := v.(string); ok {
		return s
	}
	return fmt.Sprintf("%v", v)
}

func float64Val(v any) float64 {
	if v == nil {
		return 0
	}
	switch n := v.(type) {
	case float64:
		return n
	case float32:
		return float64(n)
	case int:
		return float64(n)
	}
	return 0
}

func intVal(v any) int {
	if v == nil {
		return 0
	}
	switch n := v.(type) {
	case float64:
		return int(n)
	case int:
		return n
	}
	return 0
}
