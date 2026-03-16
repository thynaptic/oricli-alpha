package service

import (
	"log"
	"sort"
	"strings"
	"sync"
)

type GraphNode struct {
	ID        string                 `json:"id"`
	Type      string                 `json:"type"`
	Content   string                 `json:"content"`
	Metadata  map[string]interface{} `json:"metadata"`
	Timestamp float64                `json:"timestamp"`
}

type GraphEdge struct {
	Source   string  `json:"source"`
	Target   string  `json:"target"`
	Type     string  `json:"type"`
	Strength float64 `json:"strength"`
}

type MemoryGraphService struct {
	Nodes        map[string]*GraphNode
	Edges        map[string][]*GraphEdge // source -> edges
	Neo4j        *GraphService
	MemoryBridge *MemoryBridge
	mu           sync.RWMutex
}

func NewMemoryGraphService(neo4j *GraphService, mb *MemoryBridge) *MemoryGraphService {
	return &MemoryGraphService{
		Nodes:        make(map[string]*GraphNode),
		Edges:        make(map[string][]*GraphEdge),
		Neo4j:        neo4j,
		MemoryBridge: mb,
	}
}

func (s *MemoryGraphService) AddNode(node *GraphNode) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.Nodes[node.ID] = node
	
	// Sync to Neo4j
	if s.Neo4j != nil {
		s.Neo4j.AddNode("Memory", map[string]interface{}{
			"id":      node.ID,
			"content": node.Content,
			"type":    node.Type,
		})
	}
}

func (s *MemoryGraphService) AddEdge(edge *GraphEdge) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.Edges[edge.Source] = append(s.Edges[edge.Source], edge)

	// Sync to Neo4j
	if s.Neo4j != nil {
		s.Neo4j.AddRelationship(edge.Source, edge.Target, edge.Type, map[string]interface{}{
			"strength": edge.Strength,
		})
	}
}

func (s *MemoryGraphService) Traverse(startID string, maxHops int) []string {
	s.mu.RLock()
	defer s.mu.RUnlock()

	visited := make(map[string]bool)
	var result []string
	
	var dfs func(id string, depth int)
	dfs = func(id string, depth int) {
		if depth > maxHops || visited[id] {
			return
		}
		visited[id] = true
		result = append(result, id)

		for _, edge := range s.Edges[id] {
			dfs(edge.Target, depth+1)
		}
	}

	dfs(startID, 0)
	return result
}

func (s *MemoryGraphService) SemanticSearch(query string, limit int) ([]VectorResult, error) {
	// 1. If MemoryBridge is available, use vector search
	if s.MemoryBridge != nil {
		// Need to generate query vector first - for now fallback to simple string match
		// in our local graph nodes.
		log.Println("[MemoryGraph] Performing local semantic fallback search...")
	}

	s.mu.RLock()
	defer s.mu.RUnlock()

	var results []VectorResult
	queryLower := strings.ToLower(query)
	queryWords := strings.Fields(queryLower)

	for _, node := range s.Nodes {
		score := 0.0
		contentLower := strings.ToLower(node.Content)
		for _, word := range queryWords {
			if strings.Contains(contentLower, word) {
				score += 1.0
			}
		}

		if score > 0 {
			results = append(results, VectorResult{
				ID:       node.ID,
				Score:    float32(score / float64(len(queryWords))),
				Metadata: node.Metadata,
			})
		}
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Score > results[j].Score
	})

	if len(results) > limit {
		results = results[:limit]
	}

	return results, nil
}
