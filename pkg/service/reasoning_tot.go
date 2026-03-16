package service

import (
	"fmt"
	"log"
	"sort"
	"sync"
	"time"
)

type ToTNode struct {
	Thought string  `json:"thought"`
	Score   float64 `json:"score"`
}

type ToTResult struct {
	Success  bool      `json:"success"`
	Answer   string    `json:"answer"`
	Path     []ToTNode `json:"path"`
	Duration float64   `json:"duration"`
}

type ToTReasoningService struct {
	GenService *GenerationService
	Breadth    int
	MaxDepth   int
}

func NewToTReasoningService(gen *GenerationService) *ToTReasoningService {
	return &ToTReasoningService{
		GenService: gen,
		Breadth:    3,
		MaxDepth:   3,
	}
}

func (s *ToTReasoningService) Reason(query string) (ToTResult, error) {
	start := time.Now()
	var path []ToTNode
	context := ""

	log.Printf("[ToT] Starting tree exploration for: %s", query)

	for depth := 1; depth <= s.MaxDepth; depth++ {
		log.Printf("[ToT] Level %d: Generating %d candidates in parallel", depth, s.Breadth)
		
		// 1. Generate candidates in parallel
		candidates := make([]ToTNode, s.Breadth)
		var wg sync.WaitGroup
		for i := 0; i < s.Breadth; i++ {
			wg.Add(1)
			go func(idx int) {
				defer wg.Done()
				prompt := fmt.Sprintf(`Provide one potential thought for step %d of solving this query.
Query: %s
Current Context: %s
Thought:`, depth, query, context)
				
				resp, err := s.GenService.Generate(prompt, map[string]interface{}{"temperature": 0.8})
				if err == nil {
					thought, _ := resp["text"].(string)
					candidates[idx] = ToTNode{Thought: thought}
				}
			}(i)
		}
		wg.Wait()

		// 2. Evaluate candidates in parallel
		for i := range candidates {
			if candidates[i].Thought == "" { continue }
			wg.Add(1)
			go func(idx int) {
				defer wg.Done()
				prompt := fmt.Sprintf(`Rate this thought from 0.0 to 1.0 based on its utility for solving the query.
Query: %s
Thought: %s
Rating (number only):`, query, candidates[idx].Thought)
				
				resp, err := s.GenService.Generate(prompt, map[string]interface{}{"temperature": 0.0})
				if err == nil {
					text, _ := resp["text"].(string)
					var score float64
					fmt.Sscanf(text, "%f", &score)
					candidates[idx].Score = score
				}
			}(i)
		}
		wg.Wait()

		// 3. Select best candidate
		sort.Slice(candidates, func(i, j int) bool {
			return candidates[i].Score > candidates[j].Score
		})

		best := candidates[0]
		if best.Thought == "" {
			return ToTResult{Success: false}, fmt.Errorf("failed to generate valid thoughts at depth %d", depth)
		}

		log.Printf("[ToT] Selected best thought (Score: %.2f): %s", best.Score, best.Thought)
		path = append(path, best)
		context += "\n" + best.Thought

		if best.Score > 0.9 { // Heuristic for early termination
			break
		}
	}

	// Final Synthesis
	finalPrompt := fmt.Sprintf("Finalize the answer based on the best path discovered.\nQuery: %s\nPath: %s\nFinal Answer:", query, context)
	finalResp, err := s.GenService.Generate(finalPrompt, nil)
	if err != nil {
		return ToTResult{Success: false}, err
	}

	answer, _ := finalResp["text"].(string)

	return ToTResult{
		Success:  true,
		Answer:   answer,
		Path:     path,
		Duration: time.Since(start).Seconds(),
	}, nil
}
