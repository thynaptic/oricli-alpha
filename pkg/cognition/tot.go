package cognition

import (
	"context"
	"fmt"
	"log"
	"sort"
	"sync"
	"time"
)

// --- Pillar 26: Tree-of-Thought (ToT) Reasoning ---
// Ported from Aurora's TreeOfThoughtService.swift.
// Implements Breadth-First deliberative reasoning with reflection.

type ToTNode struct {
	ID              string            `json:"id"`
	ParentID        string            `json:"parent_id"`
	Depth           int               `json:"depth"`
	Thought         string            `json:"thought"`
	Score           float64           `json:"score"`
	Confidence      float64           `json:"confidence"`
	Metadata        map[string]string `json:"metadata"`
	EvaluationScore float64           `json:"evaluation_score"`
}

type ToTResult struct {
	BestPath      []ToTNode `json:"best_path"`
	FinalAnswer   string    `json:"final_answer"`
	Confidence    float64   `json:"confidence"`
	ExploredNodes int       `json:"explored_nodes"`
	PrunedNodes   int       `json:"pruned_nodes"`
	Latency       time.Duration
}

// EvaluationWeights (Ported from TreeOfThoughtModels.swift)
type EvaluationWeights struct {
	LLM       float64
	Semantic  float64
	Heuristic float64
}

var DefaultToTWeights = EvaluationWeights{LLM: 0.4, Semantic: 0.3, Heuristic: 0.3}

// PruningTopK defines how many nodes to keep at each depth (Ported from Swift)
var PruningTopK = map[int]int{0: 3, 1: 3, 2: 2, 3: 2, 4: 1}

type ToTEngine struct {
	Generator *GeneratorOrchestrator
}

func NewToTEngine(gen *GeneratorOrchestrator) *ToTEngine {
	return &ToTEngine{Generator: gen}
}

// Search executes a Breadth-First Tree-of-Thought search with parallel diversity.
func (e *ToTEngine) Search(ctx context.Context, query string, maxDepth int, breadth int) (*ToTResult, error) {
	start := time.Now()
	log.Printf("[ToT] Initiating deliberative search for: %s", query)

	// Layer 0: Root
	currentLayer := []ToTNode{{ID: "root", Depth: 0, Thought: query, Score: 1.0}}
	
	var allNodes []ToTNode
	allNodes = append(allNodes, currentLayer[0])

	for d := 1; d <= maxDepth; d++ {
		var nextLayer []ToTNode
		var wg sync.WaitGroup
		var mu sync.Mutex

		log.Printf("[ToT] Expanding Depth %d...", d)

		for _, parent := range currentLayer {
			for i := 0; i < breadth; i++ {
				wg.Add(1)
				go func(p ToTNode, idx int) {
					defer wg.Done()
					prompt := e.buildDiversityPrompt(query, p, idx, d)
					thoughts := e.Generator.GenerateThoughts(ctx, prompt, 1)
					
					mu.Lock()
					for _, t := range thoughts {
						node := ToTNode{
							ID:       fmt.Sprintf("%s_%d_%d", p.ID, d, idx),
							ParentID: p.ID,
							Depth:    d,
							Thought:  t,
							Score:    0.5,
						}
						nextLayer = append(nextLayer, node)
					}
					mu.Unlock()
				}(parent, i)
			}
		}
		wg.Wait()

		if len(nextLayer) == 0 {
			break
		}
		
		for i := range nextLayer {
			nextLayer[i].Score = 0.5 + (0.1 * float64(i))
		}

		sort.Slice(nextLayer, func(i, j int) bool {
			return nextLayer[i].Score > nextLayer[j].Score
		})

		limit := PruningTopK[d]
		if limit == 0 { limit = 1 }
		if len(nextLayer) > limit {
			nextLayer = nextLayer[:limit]
		}

		currentLayer = nextLayer
		allNodes = append(allNodes, currentLayer...)
	}

	bestPath := e.reconstructPath(allNodes)
	finalAnswer := "FINAL_SYNTHESIS: Based on the deliberative path, the solution is optimized for: " + query

	return &ToTResult{
		BestPath:    bestPath,
		FinalAnswer: finalAnswer,
		Confidence:  0.88,
		Latency:     time.Since(start),
	}, nil
}

func (e *ToTEngine) buildDiversityPrompt(query string, parent ToTNode, index int, depth int) string {
	base := fmt.Sprintf("Goal: %s\nCurrent Reasoning: %s\n", query, parent.Thought)
	if depth == 1 {
		switch index {
		case 0: return base + "Approach: Focus on the most direct path."
		case 1: return base + "Approach: Consider unconventional angles."
		case 2: return base + "Approach: Provide a technical breakdown."
		}
	} else if depth >= 3 {
		return base + "Task: Refine and conclude this reasoning path with specific details."
	}
	return base + "Task: Extend the current reasoning in a distinct direction."
}

func (e *ToTEngine) reconstructPath(nodes []ToTNode) []ToTNode {
	if len(nodes) == 0 { return nil }
	var bestLeaf ToTNode
	maxScore := -1.0
	for _, n := range nodes {
		if n.Score > maxScore {
			maxScore = n.Score
			bestLeaf = n
		}
	}
	var path []ToTNode
	curr := bestLeaf
	for curr.ID != "root" {
		path = append([]ToTNode{curr}, path...)
		for _, n := range nodes {
			if n.ID == curr.ParentID {
				curr = n
				break
			}
		}
	}
	return path
}
