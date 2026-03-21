package rag

import (
	"context"
	"crypto/md5"
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"
)

// --- Pillar 19: Hybrid Retrieval Engine ---
// Ported from Aurora's HybridRetrievalEngine.swift.
// Blends Lexical (Keyword) and Semantic (Vector) search results into unified context.

type DocumentSource string

const (
	SourceWeb    DocumentSource = "web"
	SourceMemory DocumentSource = "memory"
	SourceHybrid DocumentSource = "hybrid"
)

type RetrievedDoc struct {
	ID             string         `json:"id"`
	Title          string         `json:"title"`
	Content        string         `json:"content"`
	URL            string         `json:"url,omitempty"`
	Source         DocumentSource `json:"source"`
	RelevanceScore float64        `json:"relevance_score"`
	LexicalScore   float64        `json:"lexical_score"`
	SemanticScore  float64        `json:"semantic_score"`
	Tags           []string       `json:"tags,omitempty"`
}

type HybridResult struct {
	Query      string         `json:"query"`
	Documents  []RetrievedDoc `json:"documents"`
	Latency    time.Duration  `json:"latency"`
	TopSource  DocumentSource `json:"top_source"`
}

type HybridEngine struct {
	MaxResults int
}

func NewHybridEngine(maxResults int) *HybridEngine {
	if maxResults <= 0 {
		maxResults = 10
	}
	return &HybridEngine{MaxResults: maxResults}
}

// Retrieve runs parallel lexical and semantic search and fuses the results.
func (e *HybridEngine) Retrieve(ctx context.Context, query string) (*HybridResult, error) {
	start := time.Now()
	var wg sync.WaitGroup
	var mu sync.Mutex
	
	var allDocs []RetrievedDoc
	seenHashes := make(map[string]bool)
	seenURLs := make(map[string]int) // maps URL to index in allDocs

	// Track 1: Semantic (Simulated Vector Search)
	wg.Add(1)
	go func() {
		defer wg.Done()
		docs := []RetrievedDoc{
			{Title: "Internal Protocol Alpha", Content: "Core sovereign logic for affective state modulation.", Source: SourceMemory, SemanticScore: 0.95},
		}
		mu.Lock()
		e.mergeDocs(&allDocs, docs, seenHashes, seenURLs)
		mu.Unlock()
	}()

	// Track 2: Lexical (Simulated Web Search)
	wg.Add(1)
	go func() {
		defer wg.Done()
		docs := []RetrievedDoc{
			{Title: "AI Industry Trends 2025", Content: "Latest advances in localized LLM orchestration.", Source: SourceWeb, LexicalScore: 0.88, URL: "https://example.com/trends"},
		}
		mu.Lock()
		e.mergeDocs(&allDocs, docs, seenHashes, seenURLs)
		mu.Unlock()
	}()

	wg.Wait()

	// 3. Final Ranking & Score Fusion
	for i := range allDocs {
		d := &allDocs[i]
		// Ported blend math: (Lexical * 0.4) + (Semantic * 0.6)
		d.RelevanceScore = (d.LexicalScore * 0.4) + (d.SemanticScore * 0.6)
	}

	sort.Slice(allDocs, func(i, j int) bool {
		return allDocs[i].RelevanceScore > allDocs[j].RelevanceScore
	})

	if len(allDocs) > e.MaxResults {
		allDocs = allDocs[:e.MaxResults]
	}

	topSource := SourceHybrid
	if len(allDocs) > 0 {
		topSource = allDocs[0].Source
	}

	return &HybridResult{
		Query:     query,
		Documents: allDocs,
		Latency:   time.Since(start),
		TopSource: topSource,
	}, nil
}

func (e *HybridEngine) mergeDocs(target *[]RetrievedDoc, source []RetrievedDoc, hashes map[string]bool, urls map[string]int) {
	for _, doc := range source {
		h := e.hashContent(doc.Content)
		if hashes[h] {
			continue
		}

		if doc.URL != "" {
			if existingIdx, ok := urls[doc.URL]; ok {
				// URL collision: Merge scores
				existing := &(*target)[existingIdx]
				if doc.LexicalScore > 0 {
					existing.LexicalScore = doc.LexicalScore
				}
				if doc.SemanticScore > 0 {
					existing.SemanticScore = doc.SemanticScore
				}
				existing.Source = SourceHybrid
				continue
			}
			urls[doc.URL] = len(*target)
		}

		hashes[h] = true
		*target = append(*target, doc)
	}
}

func (e *HybridEngine) hashContent(content string) string {
	clean := strings.ToLower(strings.TrimSpace(content))
	if len(clean) > 500 {
		clean = clean[:500]
	}
	return fmt.Sprintf("%x", md5.Sum([]byte(clean)))
}
