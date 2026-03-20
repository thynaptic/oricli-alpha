package memory

import (
	"math"
	"sync"
	"time"

	"github.com/google/uuid"
)

// --- Pillar 12: Working Memory Graph (COGS) ---
// Ported from Aurora's COGSEngine.swift.
// Implements a localized, hash-based relationship graph for session context.

type EntityType string

const (
	TypePerson    EntityType = "person"
	TypePlace     EntityType = "place"
	TypeThing     EntityType = "thing"
	TypeConcept   EntityType = "concept"
	TypeEvent     EntityType = "event"
	TypeAction    EntityType = "action"
	TypeIntention EntityType = "intention"
	TypePreference EntityType = "preference"
)

type RelationshipCategory string

const (
	CatBasic    RelationshipCategory = "basic"
	CatTemporal RelationshipCategory = "temporal"
	CatSemantic RelationshipCategory = "semantic"
)

type Relationship struct {
	ID       string               `json:"id"`
	SourceID string               `json:"source_id"`
	TargetID string               `json:"target_id"`
	Type     string               `json:"type"` // related_to, causes, before, etc.
	Category RelationshipCategory `json:"category"`
	Strength float64              `json:"strength"`
	Directed bool                 `json:"directed"`
	// Affective Anchor
	Valence  float32 `json:"valence,omitempty"`
	Arousal  float32 `json:"arousal,omitempty"`
	ERI      float32 `json:"eri,omitempty"`
}

type Entity struct {
	ID          string    `json:"id"`
	Type        EntityType `json:"type"`
	Label       string    `json:"label"`
	Description string    `json:"description,omitempty"`
	Keywords    []string  `json:"keywords,omitempty"`
	Embedding   []float32 `json:"embedding"`
	Uncertainty float64   `json:"uncertainty"` // 0.0 - 1.0 (Higher means more "curious")
	Importance  float64   `json:"importance"`  // 0.0 - 1.0 (Higher means more valuable)
	// Affective Anchor (EMA-based history)
	Valence     float32   `json:"valence"`
	Arousal     float32   `json:"arousal"`
	ERI         float32   `json:"eri"`
	LastSeen    time.Time `json:"last_seen"`
	AccessCount int       `json:"access_count"`
}

type WorkingMemoryGraph struct {
	Entities      map[string]*Entity
	Relationships []Relationship
	mu            sync.RWMutex
}

func NewWorkingMemoryGraph() *WorkingMemoryGraph {
	return &WorkingMemoryGraph{
		Entities:      make(map[string]*Entity),
		Relationships: make([]Relationship, 0),
	}
}

// FindGaps identifies entities that require autonomous epistemic foraging.
func (g *WorkingMemoryGraph) FindGaps() []*Entity {
	g.mu.RLock()
	defer g.mu.RUnlock()

	var gaps []*Entity
	for _, e := range g.Entities {
		// Degree: Number of relationships this entity has
		degree := 0
		for _, r := range g.Relationships {
			if r.SourceID == e.ID || r.TargetID == e.ID {
				degree++
			}
		}

		// Heuristic: If Uncertainty is high or Degree is low, it's a gap
		if e.Uncertainty > 0.7 || degree < 2 || len(e.Description) < 20 {
			gaps = append(gaps, e)
		}
	}
	return gaps
}

// UpdateEntity applies metadata updates to an existing entity in a thread-safe manner.
func (g *WorkingMemoryGraph) UpdateEntity(id string, valence, arousal, eri float32, update func(*Entity)) bool {
	g.mu.Lock()
	defer g.mu.Unlock()

	if e, ok := g.Entities[id]; ok {
		update(e)
		// Update affective anchor using EMA (0.2 alpha)
		e.Valence = (e.Valence * 0.8) + (valence * 0.2)
		e.Arousal = (e.Arousal * 0.8) + (arousal * 0.2)
		e.ERI = (e.ERI * 0.8) + (eri * 0.2)
		e.LastSeen = time.Now()
		return true
	}
	return false
}

// GenerateSovereignEmbedding creates a deterministic vector from text.
// Ported from Swift generateEmbedding (hash-based sin wave).
func GenerateSovereignEmbedding(text string, dims int) []float32 {
	embedding := make([]float32, dims)
	hash := uint32(0)
	for i := 0; i < len(text); i++ {
		hash = hash*31 + uint32(text[i])
	}

	for i := 0; i < dims; i++ {
		seed := float64(hash + uint32(i))
		embedding[i] = float32(math.Sin(seed)*0.5 + 0.5)
	}

	// Normalization
	magnitude := float64(0)
	for _, v := range embedding {
		magnitude += float64(v * v)
	}
	magnitude = math.Sqrt(magnitude)

	if magnitude > 0 {
		for i := range embedding {
			embedding[i] /= float32(magnitude)
		}
	}

	return embedding
}

// AddEntity registers a new context object.
func (g *WorkingMemoryGraph) AddEntity(label string, eType EntityType, desc string, valence, arousal, eri float32) *Entity {
	g.mu.Lock()
	defer g.mu.Unlock()

	id := uuid.New().String()[:8]
	entity := &Entity{
		ID:          id,
		Type:        eType,
		Label:       label,
		Description: desc,
		Embedding:   GenerateSovereignEmbedding(label+desc, 256),
		Valence:     valence,
		Arousal:     arousal,
		ERI:         eri,
		LastSeen:    time.Now(),
	}
	g.Entities[id] = entity
	return entity
}

// AddRelationship connects two entities in working memory.
func (g *WorkingMemoryGraph) AddRelationship(sourceID, targetID, relType string, strength float64, valence, arousal, eri float32) {
	g.mu.Lock()
	defer g.mu.Unlock()

	g.Relationships = append(g.Relationships, Relationship{
		ID:       uuid.New().String()[:8],
		SourceID: sourceID,
		TargetID: targetID,
		Type:     relType,
		Strength: strength,
		Valence:  valence,
		Arousal:  arousal,
		ERI:      eri,
	})
}

// GetContextGraph retrieves a subgraph related to an entity.
func (g *WorkingMemoryGraph) GetContextGraph(entityID string) ([]*Entity, []Relationship) {
	g.mu.RLock()
	defer g.mu.RUnlock()

	var relatedEntities []*Entity
	var relatedRels []Relationship
	seen := make(map[string]bool)

	if root, ok := g.Entities[entityID]; ok {
		relatedEntities = append(relatedEntities, root)
		seen[entityID] = true
	}

	for _, rel := range g.Relationships {
		if rel.SourceID == entityID || rel.TargetID == entityID {
			relatedRels = append(relatedRels, rel)
			
			targetID := rel.TargetID
			if rel.TargetID == entityID {
				targetID = rel.SourceID
			}

			if !seen[targetID] {
				if e, ok := g.Entities[targetID]; ok {
					relatedEntities = append(relatedEntities, e)
					seen[targetID] = true
				}
			}
		}
	}

	return relatedEntities, relatedRels
}

// AnalyzeSubGraphAffect calculates the average affective anchor for a set of entities.
func (g *WorkingMemoryGraph) AnalyzeSubGraphAffect(entities []*Entity) (valence, arousal, eri float32) {
	if len(entities) == 0 {
		return 0.5, 0.5, 0.5 // Neutral baseline
	}

	var totalV, totalA, totalE float32
	count := 0
	for _, e := range entities {
		// Only include entities that have been anchored
		if e.AccessCount > 0 || e.Valence != 0 {
			totalV += e.Valence
			totalA += e.Arousal
			totalE += e.ERI
			count++
		}
	}

	if count == 0 {
		return 0.5, 0.5, 0.5
	}

	return totalV / float32(count), totalA / float32(count), totalE / float32(count)
}
