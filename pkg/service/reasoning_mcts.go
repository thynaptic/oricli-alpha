package service

import (
	"fmt"
	"log"
	"math"
	"sync"
	"time"
)

type MCTSNode struct {
	Thought  string
	Children []*MCTSNode
	Parent   *MCTSNode
	Visits   int
	Value    float64
	Depth    int
	Mu       sync.Mutex
}

type MCTSResult struct {
	Success  bool    `json:"success"`
	Answer   string  `json:"answer"`
	Duration float64 `json:"duration"`
}

type MCTSReasoningService struct {
	GenService *GenerationService
	IterCount  int
}

func NewMCTSReasoningService(gen *GenerationService) *MCTSReasoningService {
	return &MCTSReasoningService{
		GenService: gen,
		IterCount:  5, // Sane default for VPS
	}
}

func (s *MCTSReasoningService) Reason(query string) (MCTSResult, error) {
	start := time.Now()
	root := &MCTSNode{Thought: "Root", Depth: 0}

	log.Printf("[MCTS] Starting search for: %s", query)

	for i := 0; i < s.IterCount; i++ {
		log.Printf("[MCTS] Iteration %d", i+1)
		
		// 1. Selection
		node := s.selectNode(root)

		// 2. Expansion & Simulation (Rollout)
		reward := s.simulate(query, node)

		// 3. Backpropagation
		s.backpropagate(node, reward)
	}

	// 4. Synthesize final answer from best path
	bestPath := s.getBestPath(root)
	finalPrompt := fmt.Sprintf("Synthesize the final answer based on these reasoning rollouts.\nQuery: %s\nPath: %s\nFinal Answer:", query, bestPath)
	resp, err := s.GenService.Generate(finalPrompt, nil)
	if err != nil {
		return MCTSResult{Success: false}, err
	}

	answer, _ := resp["text"].(string)

	return MCTSResult{
		Success:  true,
		Answer:   answer,
		Duration: time.Since(start).Seconds(),
	}, nil
}

func (s *MCTSReasoningService) selectNode(n *MCTSNode) *MCTSNode {
	n.Mu.Lock()
	defer n.Mu.Unlock()

	if len(n.Children) == 0 {
		return n
	}

	// UCB1 Selection
	var bestChild *MCTSNode
	maxUCB := -1.0
	
	for _, child := range n.Children {
		ucb := s.calculateUCB(child)
		if ucb > maxUCB {
			maxUCB = ucb
			bestChild = child
		}
	}

	return s.selectNode(bestChild)
}

func (s *MCTSReasoningService) calculateUCB(n *MCTSNode) float64 {
	if n.Visits == 0 {
		return math.MaxFloat64
	}
	exploitation := n.Value / float64(n.Visits)
	exploration := math.Sqrt(2 * math.Log(float64(n.Parent.Visits)) / float64(n.Visits))
	return exploitation + exploration
}

func (s *MCTSReasoningService) simulate(query string, n *MCTSNode) float64 {
	// Simple rollout: generate a thought and rate it
	prompt := fmt.Sprintf("Perform a reasoning rollout for this query: %s\nCurrent thought: %s\nProvide a continuation and a quality score (0-1).", query, n.Thought)
	resp, _ := s.GenService.Generate(prompt, map[string]interface{}{"temperature": 0.7})
	
	text, _ := resp["text"].(string)
	
	// Create child
	n.Mu.Lock()
	child := &MCTSNode{Thought: text, Parent: n, Depth: n.Depth + 1}
	n.Children = append(n.Children, child)
	n.Mu.Unlock()

	// Rate result (simplified for now)
	var score float64 = 0.5
	fmt.Sscanf(text, "%f", &score)
	return score
}

func (s *MCTSReasoningService) backpropagate(n *MCTSNode, reward float64) {
	for n != nil {
		n.Mu.Lock()
		n.Visits++
		n.Value += reward
		n.Mu.Unlock()
		n = n.Parent
	}
}

func (s *MCTSReasoningService) getBestPath(root *MCTSNode) string {
	path := ""
	curr := root
	for len(curr.Children) > 0 {
		best := curr.Children[0]
		for _, child := range curr.Children {
			if child.Visits > best.Visits {
				best = child
			}
		}
		path += "\n- " + best.Thought
		curr = best
	}
	return path
}
