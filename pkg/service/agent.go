package service

import (
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"
)

// ToolDefinition describes a tool the agent can use
type ToolDefinition struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Parameters  string `json:"parameters"`
}

// GoAgentService handles the multi-step reasoning loop in Go
type GoAgentService struct {
	Orchestrator   *GoOrchestrator
	GenService     *GenerationService
	PersonaService *PersonaService
	MaxSteps       int
}

func NewGoAgentService(orch *GoOrchestrator, gen *GenerationService, persona *PersonaService) *GoAgentService {
	return &GoAgentService{
		Orchestrator:   orch,
		GenService:     gen,
		PersonaService: persona,
		MaxSteps:       5,
	}
}

// Run executes the reasoning loop for a given query
func (s *GoAgentService) Run(query string, history []map[string]string) (string, error) {
	log.Printf("[Agent] Starting reasoning loop for: %s", query)

	context := ""
	for i := 0; i < s.MaxSteps; i++ {
		log.Printf("[Agent] Step %d/%d", i+1, s.MaxSteps)

		// 1. Ask the model what to do
		thought, toolCall, err := s.decideNextStep(query, context, history)
		if err != nil {
			return "", err
		}

		if thought != "" {
			log.Printf("[Agent] Thought: %s", thought)
		}

		// 2. If no tool call, we're done
		if toolCall == nil {
			return thought, nil
		}

		// 3. Execute the tool via the Orchestrator
		log.Printf("[Agent] Executing tool: %s with params: %v", toolCall.Name, toolCall.Params)
		result, err := s.Orchestrator.Execute(toolCall.Name, toolCall.Params, 60*time.Second)
		if err != nil {
			log.Printf("[Agent] Tool error: %v", err)
			context += fmt.Sprintf("\nTool %s failed: %v", toolCall.Name, err)
			continue
		}

		// 4. Feed the result back into context
		resultJSON, _ := json.Marshal(result)
		context += fmt.Sprintf("\nTool %s result: %s", toolCall.Name, string(resultJSON))
	}

	return "", fmt.Errorf("agent exceeded max steps (%d) without final answer", s.MaxSteps)
}

type toolCall struct {
	Name   string                 `json:"name"`
	Params map[string]interface{} `json:"params"`
}

func (s *GoAgentService) decideNextStep(query, context string, history []map[string]string) (string, *toolCall, error) {
	// Build personality-aware system prompt
	personalityID := "gen_z_cousin" // Default
	systemInstructions, temp := s.PersonaService.BuildSystemInstructions(personalityID)

	systemPrompt := fmt.Sprintf(`%s

TASK INSTRUCTIONS:
Your goal is to answer the user query accurately. You can use tools or answer directly.
If you use a tool, you MUST output ONLY valid JSON.

Available Tools:
1. memory_bridge (operations: "get", "vector_search")
   - Params: {"operation": "get", "category": "semantic", "id": "..."}
2. web_fetch_service (operations: "fetch_url")
   - Params: {"operation": "fetch_url", "url": "..."}
3. zebra_puzzle_solver (operations: "solve_zebra_puzzle")
   - Params: {"operation": "solve_zebra_puzzle", "input": "full puzzle text here"}
4. spatial_reasoning_solver (operations: "solve_spatial_problem")
   - Params: {"operation": "solve_spatial_problem", "input": "puzzle text here"}

Example Tool Call:
{
  "thought": "This is a logic puzzle, I should use the specialized solver.",
  "tool_call": { "name": "zebra_puzzle_solver", "params": { "operation": "solve_zebra_puzzle", "input": "..." } }
}

Example Final Answer:
{
  "thought": "Here is your joke: Why did the chicken cross the road? To get to the other side!",
  "tool_call": null
}

Output Format (JSON ONLY):`, systemInstructions)

	userPrompt := fmt.Sprintf("User Query: %s\n\nCurrent Context: %s", query, context)
	
	// Direct call to GenService
	resp, err := s.GenService.Chat([]map[string]string{
		{"role": "system", "content": systemPrompt},
		{"role": "user", "content": userPrompt},
	}, map[string]interface{}{"temperature": temp})

	if err != nil {
		return "", nil, err
	}

	text, _ := resp["text"].(string)
	
	// Try to parse JSON from the response
	var decision struct {
		Thought  string    `json:"thought"`
		ToolCall *toolCall `json:"tool_call"`
	}

	// Clean up markdown code blocks if present
	jsonStr := text
	if strings.Contains(text, "```json") {
		parts := strings.Split(text, "```json")
		if len(parts) > 1 {
			jsonStr = strings.Split(parts[1], "```")[0]
		}
	}

	if err := json.Unmarshal([]byte(jsonStr), &decision); err != nil {
		// If it's not valid JSON, treat it as a final thought/answer
		return text, nil, nil
	}

	return decision.Thought, decision.ToolCall, nil
}
