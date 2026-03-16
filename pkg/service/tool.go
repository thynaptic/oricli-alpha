package service

import (
	"encoding/json"
	"log"
	"sync"
	"time"
)

type ToolResult struct {
	Success   bool                   `json:"success"`
	Content   string                 `json:"content"`
	Error     string                 `json:"error,omitempty"`
	Metadata  map[string]interface{} `json:"metadata"`
}

type Tool struct {
	Name        string                 `json:"name"`
	Description string                 `json:"description"`
	Parameters  map[string]interface{} `json:"parameters"`
	ModuleName  string                 `json:"module_name"`
	Operation   string                 `json:"operation"`
}

type ToolService struct {
	Tools        map[string]Tool
	Orchestrator *GoOrchestrator
	mu           sync.RWMutex
}

func NewToolService(orch *GoOrchestrator) *ToolService {
	return &ToolService{
		Tools:        make(map[string]Tool),
		Orchestrator: orch,
	}
}

func (s *ToolService) RegisterTool(t Tool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.Tools[t.Name] = t
	log.Printf("[ToolService] Registered tool: %s (routes to %s.%s)", t.Name, t.ModuleName, t.Operation)
}

func (s *ToolService) ExecuteTool(name string, arguments map[string]interface{}) (ToolResult, error) {
	s.mu.RLock()
	tool, ok := s.Tools[name]
	s.mu.RUnlock()

	if !ok {
		// Fallback: If tool not in registry, try executing it as a raw module operation
		log.Printf("[ToolService] Tool %s not in registry, attempting direct module call...", name)
		result, err := s.Orchestrator.Execute(name, arguments, 60*time.Second)
		if err != nil {
			return ToolResult{Success: false, Error: err.Error()}, err
		}
		
		content := ""
		if m, ok := result.(map[string]interface{}); ok {
			if c, ok := m["content"].(string); ok { content = c }
			if c, ok := m["text"].(string); ok { content = c }
		}
		if content == "" {
			data, _ := json.Marshal(result)
			content = string(data)
		}

		return ToolResult{Success: true, Content: content}, nil
	}

	// Route to the registered module/operation
	log.Printf("[ToolService] Routing tool %s to %s.%s", name, tool.ModuleName, tool.Operation)
	
	// Merge arguments if needed or pass directly
	result, err := s.Orchestrator.Execute(tool.Operation, arguments, 60*time.Second)
	if err != nil {
		return ToolResult{Success: false, Error: err.Error()}, err
	}

	// Format result
	content := ""
	if m, ok := result.(map[string]interface{}); ok {
		if c, ok := m["content"].(string); ok { content = c }
		if c, ok := m["text"].(string); ok { content = c }
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
	}, nil
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
