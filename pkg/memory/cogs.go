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
	TypePerson   EntityType = "person"
	TypeConcept  EntityType = "concept"
	TypeAction   EntityType = "action"
	TypeObject   EntityType = "object"
	TypeLocation EntityType = "location"
)

type Entity struct {
	ID          string    `json:"id"`
	Type        EntityType `json:"type"`
	Label       string    `json:"label"`
	Description string    `json:"description,omitempty"`
	Embedding   []float32 `json:"embedding"`
	LastSeen    time.Time `json:"last_seen"`
}

type Relationship struct {
	ID       string  `json:"id"`
	SourceID string  `json:"source_id"`
	TargetID string  `json:"target_id"`
	Type     string  `json:"type"`
	Strength float64 `json:"strength"`
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
func (g *WorkingMemoryGraph) AddEntity(label string, eType EntityType, desc string) *Entity {
	g.mu.Lock()
	defer g.mu.Unlock()

	id := uuid.New().String()[:8]
	entity := &Entity{
		ID:          id,
		Type:        eType,
		Label:       label,
		Description: desc,
		Embedding:   GenerateSovereignEmbedding(label+desc, 256),
		LastSeen:    time.Now(),
	}
	g.Entities[id] = entity
	return entity
}

// AddRelationship connects two entities in working memory.
func (g *WorkingMemoryGraph) AddRelationship(sourceID, targetID, relType string, strength float64) {
	g.mu.Lock()
	defer g.mu.Unlock()

	g.Relationships = append(g.Relationships, Relationship{
		ID:       uuid.New().String()[:8],
		SourceID: sourceID,
		TargetID: targetID,
		Type:     relType,
		Strength: strength,
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
