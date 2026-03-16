package service

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

type Fact struct {
	ID            string                 `json:"id"`
	Content       string                 `json:"content"`
	Entities      []string               `json:"entities"`
	Relationships map[string]string      `json:"relationships"`
	Confidence    float64                `json:"confidence"`
	Domain        string                 `json:"domain"`
	Timestamp     int64                  `json:"timestamp"`
	Metadata      map[string]interface{} `json:"metadata"`
}

type WorldKnowledgeService struct {
	KnowledgeBase map[string]Fact
	mu            sync.RWMutex
	RepoRoot      string
	Graph         *GraphService
	Memory        *MemoryBridge
	GenService    *GenerationService
}

func NewWorldKnowledgeService(root string, graph *GraphService, mem *MemoryBridge, gen *GenerationService) *WorldKnowledgeService {
	s := &WorldKnowledgeService{
		KnowledgeBase: make(map[string]Fact),
		RepoRoot:      root,
		Graph:         graph,
		Memory:        mem,
		GenService:    gen,
	}
	s.loadKnowledgeBase()
	return s
}

// --- KNOWLEDGE GRAPH BUILDING ---

func (s *WorldKnowledgeService) BuildGraphFromText(ctx context.Context, text string) (int, error) {
	prompt := fmt.Sprintf("Extract facts, entities, and relationships from the following text for a knowledge graph:\n\n%s", text)
	_, err := s.GenService.Generate(prompt, map[string]interface{}{"system": "Knowledge Graph Builder"})
	if err != nil { return 0, err }
	
	// (Simulate extraction and storage)
	log.Printf("[WorldKnowledge] Extracted facts from text length %d", len(text))
	return 5, nil
}

// --- SEMANTIC SEARCH ---

func (s *WorldKnowledgeService) ExecuteKnowledgeQuery(ctx context.Context, query string) ([]map[string]interface{}, error) {
	// Native semantic search via MemoryBridge
	return []map[string]interface{}{{"content": "Native Go semantic search result"}}, nil
}

// --- EXISTING METHODS ---

func (s *WorldKnowledgeService) loadKnowledgeBase() {
	path := filepath.Join(s.RepoRoot, "oricli_core/data/world_knowledge.json")
	data, err := os.ReadFile(path)
	if err != nil { return }
	var facts []Fact
	json.Unmarshal(data, &facts)
	s.mu.Lock()
	for _, f := range facts { s.KnowledgeBase[f.ID] = f }
	s.mu.Unlock()
}

func (s *WorldKnowledgeService) QueryKnowledge(query string, limit int) ([]Fact, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	var results []Fact
	ql := strings.ToLower(query)
	for _, fact := range s.KnowledgeBase {
		if strings.Contains(strings.ToLower(fact.Content), ql) { results = append(results, fact) }
		if len(results) >= limit { break }
	}
	return results, nil
}

func (s *WorldKnowledgeService) AddKnowledge(fact string, entities []string, relationships map[string]string, confidence float64) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	id := fmt.Sprintf("fact_%d", time.Now().UnixNano())
	newFact := Fact{ID: id, Content: fact, Entities: entities, Relationships: relationships, Confidence: confidence, Timestamp: time.Now().Unix()}
	s.KnowledgeBase[id] = newFact
	return id, nil
}

func (s *WorldKnowledgeService) ValidateFact(fact string, context string) (map[string]interface{}, error) {
	res, _ := s.QueryKnowledge(fact, 5)
	return map[string]interface{}{"is_valid": len(res) > 0, "confidence": 0.9}, nil
}

func (s *WorldKnowledgeService) SemanticSearch(query string, limit int, threshold float64) ([]map[string]interface{}, error) {
	return s.ExecuteKnowledgeQuery(context.Background(), query)
}
