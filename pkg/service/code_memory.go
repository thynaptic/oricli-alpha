package service

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

type CodePattern struct {
	ID        string                 `json:"id"`
	Pattern   string                 `json:"pattern"`
	Context   map[string]interface{} `json:"context"`
	Timestamp int64                  `json:"timestamp"`
}

type CodeMemoryResult struct {
	Success bool                   `json:"success"`
	ID      string                 `json:"id,omitempty"`
	Data    interface{}            `json:"data,omitempty"`
	Summary string                 `json:"summary,omitempty"`
}

type CodeMemoryService struct {
	Graph        *GraphService
	Memory       *MemoryBridge
	Orchestrator *GoOrchestrator
	PatternCache map[string]CodePattern
	StoragePath  string
	mu           sync.RWMutex
}

func NewCodeMemoryService(graph *GraphService, mem *MemoryBridge, orch *GoOrchestrator, storagePath string) *CodeMemoryService {
	if storagePath == "" {
		storagePath = "oricli_core/data/code_memory_cache.json"
	}
	s := &CodeMemoryService{
		Graph:        graph,
		Memory:       mem,
		Orchestrator: orch,
		PatternCache: make(map[string]CodePattern),
		StoragePath:  storagePath,
	}
	s.loadCache()
	return s
}

func (s *CodeMemoryService) loadCache() {
	data, err := os.ReadFile(s.StoragePath)
	if err == nil {
		var cache map[string]CodePattern
		if err := json.Unmarshal(data, &cache); err == nil {
			s.mu.Lock()
			s.PatternCache = cache
			s.mu.Unlock()
		}
	}
}

func (s *CodeMemoryService) saveCache() {
	s.mu.RLock()
	cache := s.PatternCache
	s.mu.RUnlock()

	data, _ := json.MarshalIndent(cache, "", "  ")
	os.MkdirAll(filepath.Dir(s.StoragePath), 0755)
	os.WriteFile(s.StoragePath, data, 0644)
}

func (s *CodeMemoryService) RememberCodePattern(pattern string, context map[string]interface{}) (*CodeMemoryResult, error) {
	log.Printf("[CodeMemory] Remembering code pattern")

	hash := sha256.Sum256([]byte(pattern))
	id := fmt.Sprintf("pattern_%x", hash[:8])

	cp := CodePattern{
		ID:        id,
		Pattern:   pattern,
		Context:   context,
		Timestamp: time.Now().Unix(),
	}

	s.mu.Lock()
	s.PatternCache[id] = cp
	s.mu.Unlock()

	go s.saveCache()

	// Persist to graph
	go func() {
		cypher := "MERGE (p:CodePattern {id: $id}) SET p.pattern = $pattern, p.timestamp = $ts"
		s.Graph.ExecuteQuery(cypher, map[string]interface{}{
			"id":      id,
			"pattern": pattern,
			"ts":      cp.Timestamp,
		})
	}()

	return &CodeMemoryResult{
		Success: true,
		ID:      id,
		Summary: "Pattern remembered.",
	}, nil
}

func (s *CodeMemoryService) RecallSimilarPatterns(code string, limit int) (*CodeMemoryResult, error) {
	log.Printf("[CodeMemory] Recalling patterns similar to provided code")

	// Fallback heuristic if MemoryBridge isn't available
	var matches []CodePattern
	s.mu.RLock()
	for _, p := range s.PatternCache {
		if strings.Contains(p.Pattern, code) || strings.Contains(code, p.Pattern) {
			matches = append(matches, p)
		}
	}
	s.mu.RUnlock()

	if len(matches) > limit {
		matches = matches[:limit]
	}

	return &CodeMemoryResult{
		Success: true,
		Data:    matches,
		Summary: fmt.Sprintf("Found %d similar patterns.", len(matches)),
	}, nil
}

func (s *CodeMemoryService) GetCodeIdioms(languageFeature string) (*CodeMemoryResult, error) {
	log.Printf("[CodeMemory] Fetching idioms for: %s", languageFeature)

	// Hardcoded fallback for speed
	idioms := map[string][]string{
		"list_comprehension": {"[x for x in items if x > 0]"},
		"dictionary_merge":   {"{**dict1, **dict2}", "dict1 | dict2"},
		"file_reading":       {"with open('file.txt', 'r') as f:\n    data = f.read()"},
	}

	res := idioms[languageFeature]
	if res == nil {
		res = []string{}
	}

	return &CodeMemoryResult{
		Success: true,
		Data:    res,
	}, nil
}
