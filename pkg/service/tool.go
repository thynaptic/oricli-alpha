package service

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"regexp"
	"strings"
	"sync"
	"time"
)

// ToolResult represents the outcome of a tool execution
type ToolResult struct {
	Success   bool                   `json:"success"`
	Content   string                 `json:"content"`
	Error     string                 `json:"error,omitempty"`
	Metadata  map[string]interface{} `json:"metadata"`
}

// ToolCall represents a specific request to call a tool
type ToolCall struct {
	Index    int                    `json:"index,omitempty"`
	ID       string                 `json:"id,omitempty"`
	Type     string                 `json:"type,omitempty"`
	Function ToolCallFunction       `json:"function"`
}

// ToolCallFunction represents the function name and arguments for a tool call
type ToolCallFunction struct {
	Name      string                 `json:"name"`
	Arguments map[string]interface{} `json:"arguments"`
}

// Tool represents a registered tool definition
type Tool struct {
	Name        string                 `json:"name"`
	Description string                 `json:"description"`
	Parameters  map[string]interface{} `json:"parameters"`
	ModuleName  string                 `json:"module_name"`
	Operation   string                 `json:"operation"`
}

// ToolService manages the registration, discovery, parsing, and execution of tools
type ToolService struct {
	Tools        map[string]Tool
	Orchestrator *GoOrchestrator
	mu           sync.RWMutex
}

// NewToolService creates a new tool service
func NewToolService(orch *GoOrchestrator) *ToolService {
	return &ToolService{
		Tools:        make(map[string]Tool),
		Orchestrator: orch,
	}
}

// RegisterTool adds a tool to the registry
func (s *ToolService) RegisterTool(t Tool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.Tools[t.Name] = t
	log.Printf("[ToolService] Registered tool: %s (routes to %s.%s)", t.Name, t.ModuleName, t.Operation)
}

// ExecuteTool runs a single tool with given arguments
func (s *ToolService) ExecuteTool(ctx context.Context, name string, arguments map[string]interface{}) (ToolResult, error) {
	s.mu.RLock()
	tool, ok := s.Tools[name]
	s.mu.RUnlock()

	if !ok {
		log.Printf("[ToolService] Tool %s not in registry, attempting direct module call...", name)
		result, err := s.Orchestrator.Execute(name, arguments, 60*time.Second)
		if err != nil {
			return ToolResult{Success: false, Error: err.Error()}, err
		}
		return s.formatResult(name, result), nil
	}

	log.Printf("[ToolService] Routing tool %s to %s.%s", name, tool.ModuleName, tool.Operation)
	result, err := s.Orchestrator.Execute(fmt.Sprintf("%s.%s", tool.ModuleName, tool.Operation), arguments, 60*time.Second)
	if err != nil {
		return ToolResult{Success: false, Error: err.Error()}, err
	}

	return s.formatResult(name, result), nil
}

func (s *ToolService) formatResult(name string, result interface{}) ToolResult {
	content := ""
	if m, ok := result.(map[string]interface{}); ok {
		if c, ok := m["content"].(string); ok { content = c }
		if c, ok := m["text"].(string); ok { content = c }
		if c, ok := m["prediction"].(string); ok { content = c }
	}
	if content == "" {
		data, _ := json.Marshal(result)
		content = string(data)
	}

	return ToolResult{
		Success: true,
		Content: content,
		Metadata: map[string]interface{}{
			"tool": name,
			"ts":   time.Now().Unix(),
		},
	}
}

// ExecuteToolsParallel runs multiple tool calls in parallel
func (s *ToolService) ExecuteToolsParallel(ctx context.Context, calls []ToolCall) []ToolResult {
	results := make([]ToolResult, len(calls))
	var wg sync.WaitGroup

	for i, call := range calls {
		wg.Add(1)
		go func(idx int, c ToolCall) {
			defer wg.Done()
			res, err := s.ExecuteTool(ctx, c.Function.Name, c.Function.Arguments)
			if err != nil {
				results[idx] = ToolResult{Success: false, Error: err.Error()}
			} else {
				results[idx] = res
			}
		}(i, call)
	}

	wg.Wait()
	return results
}

// ParseToolCalls extracts tool calls from an LLM response string
func (s *ToolService) ParseToolCalls(response string) []ToolCall {
	// 1. Try JSON block parsing
	jsonPattern := regexp.MustCompile("(?s)```json\\s*(\\{.*?\\}|\\[.*?\\])\\s*```")
	if match := jsonPattern.FindStringSubmatch(response); len(match) > 1 {
		return s.parseJSONCalls(match[1])
	}

	// 2. Try raw JSON parsing
	startIdx := strings.Index(response, "{")
	endIdx := strings.LastIndex(response, "}")
	if startIdx != -1 && endIdx > startIdx {
		return s.parseJSONCalls(response[startIdx : endIdx+1])
	}

	// 3. Try regex text pattern parsing: tool_call: name(arg="val")
	return s.parseTextPatternCalls(response)
}

func (s *ToolService) parseJSONCalls(jsonStr string) []ToolCall {
	var calls []ToolCall
	
	// Try standard tool_calls format
	var wrapped struct {
		ToolCalls []ToolCall `json:"tool_calls"`
	}
	if err := json.Unmarshal([]byte(jsonStr), &wrapped); err == nil && len(wrapped.ToolCalls) > 0 {
		return wrapped.ToolCalls
	}

	// Try list format
	var list []ToolCall
	if err := json.Unmarshal([]byte(jsonStr), &list); err == nil {
		return list
	}

	return calls
}

func (s *ToolService) parseTextPatternCalls(text string) []ToolCall {
	var calls []ToolCall
	pattern := regexp.MustCompile(`tool_call:\s*(\w+)\s*\(([^)]+)\)`)
	matches := pattern.FindAllStringSubmatch(text, -1)

	for _, m := range matches {
		if len(m) < 3 { continue }
		name := m[1]
		argsStr := m[2]
		
		args := make(map[string]interface{})
		argPattern := regexp.MustCompile(`(\w+)\s*=\s*["']([^"']+)["']`)
		argMatches := argPattern.FindAllStringSubmatch(argsStr, -1)
		
		for _, am := range argMatches {
			if len(am) < 3 { continue }
			args[am[1]] = am[2]
		}

		calls = append(calls, ToolCall{
			Function: ToolCallFunction{
				Name:      name,
				Arguments: args,
			},
		})
	}
	return calls
}

// GenerateSchema creates a JSON schema for a tool (simplified)
func (s *ToolService) GenerateSchema(name string) map[string]interface{} {
	s.mu.RLock()
	tool, ok := s.Tools[name]
	s.mu.RUnlock()

	if !ok { return nil }

	return map[string]interface{}{
		"type": "function",
		"function": map[string]interface{}{
			"name":        tool.Name,
			"description": tool.Description,
			"parameters":  tool.Parameters,
		},
	}
}

func (s *ToolService) ListTools() []Tool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	var list []Tool
	for _, t := range s.Tools {
		list = append(list, t)
	}
	return list
}
