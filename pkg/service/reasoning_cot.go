package service

import (
	"fmt"
	"log"
	"strings"
	"time"
)

type CoTStep struct {
	Step      int    `json:"step"`
	Thought   string `json:"thought"`
	Action    string `json:"action,omitempty"`
	Result    string `json:"result,omitempty"`
}

type CoTResult struct {
	Success   bool      `json:"success"`
	Answer    string    `json:"answer"`
	Steps     []CoTStep `json:"steps"`
	Duration  float64   `json:"duration"`
}

type CoTReasoningService struct {
	GenService *GenerationService
	MaxSteps   int
}

func NewCoTReasoningService(gen *GenerationService) *CoTReasoningService {
	return &CoTReasoningService{
		GenService: gen,
		MaxSteps:   5,
	}
}

func (s *CoTReasoningService) Reason(query string) (CoTResult, error) {
	start := time.Now()
	var steps []CoTStep
	context := ""

	log.Printf("[CoT] Starting reasoning for: %s", query)

	for i := 1; i <= s.MaxSteps; i++ {
		log.Printf("[CoT] Step %d", i)
		
		prompt := fmt.Sprintf(`Analyze the user query and provide Step %d of your reasoning.
Original Query: %s
Previous Steps: %s

Current Step Thought:`, i, query, context)

		resp, err := s.GenService.Generate(prompt, nil)
		if err != nil {
			return CoTResult{Success: false}, err
		}

		thought, _ := resp["text"].(string)
		steps = append(steps, CoTStep{Step: i, Thought: thought})
		context += fmt.Sprintf("\nStep %d: %s", i, thought)

		// Check if the model thinks it's done
		if s.isFinalStep(thought) {
			break
		}
	}

	// Final Synthesis
	log.Printf("[CoT] Synthesizing final answer")
	finalPrompt := fmt.Sprintf(`Based on your reasoning steps, provide a final concise answer.
Query: %s
Reasoning: %s

Final Answer:`, query, context)

	finalResp, err := s.GenService.Generate(finalPrompt, nil)
	if err != nil {
		return CoTResult{Success: false}, err
	}

	answer, _ := finalResp["text"].(string)

	return CoTResult{
		Success:  true,
		Answer:   answer,
		Steps:    steps,
		Duration: time.Since(start).Seconds(),
	}, nil
}

func (s *CoTReasoningService) isFinalStep(thought string) bool {
	lower := strings.ToLower(thought)
	return strings.Contains(lower, "final answer") || 
		   strings.Contains(lower, "conclusion") || 
		   strings.Contains(lower, "therefore") ||
		   len(thought) < 20 // Heuristic for short terminating thoughts
}
