package tools

import (
	"encoding/json"
	"fmt"
	"sync"
)

// --- Pillar 23: Dynamic Tool Registry ---
// Ported from Aurora's ToolRegistrationService.swift.
// Implements self-documenting, schema-driven capability management.

type ToolType string

const (
	TypeInference ToolType = "inference"
	TypeSystem    ToolType = "system"
	TypeMemory    ToolType = "memory"
	TypeWeb       ToolType = "web"
)

type ToolProperty struct {
	Type        string   `json:"type"`
	Description string   `json:"description"`
	Enum        []string `json:"enum,omitempty"`
}

type ToolParameters struct {
	Type       string                  `json:"type"`
	Properties map[string]ToolProperty `json:"properties"`
	Required   []string                `json:"required"`
}

type ToolDefinition struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	Parameters  ToolParameters `json:"parameters"`
}

type Tool struct {
	Definition ToolDefinition
	Handler    func(args map[string]interface{}) (string, error)
	Category   ToolType
}

type Registry struct {
	Tools map[string]*Tool
	mu    sync.RWMutex
}

func NewRegistry() *Registry {
	return &Registry{
		Tools: make(map[string]*Tool),
	}
}

// Register adds a new capability to the sovereign toolbox.
func (r *Registry) Register(tool *Tool) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.Tools[tool.Definition.Name] = tool
}

// GetOpenAISchema generates the tool definitions for LLM injection.
func (r *Registry) GetOpenAISchema() []ToolDefinition {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var schema []ToolDefinition
	for _, t := range r.Tools {
		schema = append(schema, t.Definition)
	}
	return schema
}

// Execute looks up a tool and runs its handler with the provided arguments.
func (r *Registry) Execute(name string, args map[string]interface{}) (string, error) {
	r.mu.RLock()
	t, ok := r.Tools[name]
	r.mu.RUnlock()

	if !ok {
		return "", fmt.Errorf("tool not found: %s", name)
	}

	return t.Handler(args)
}

// ToJSON helper for prompt injection.
func (r *Registry) ToJSON() string {
	schema := r.GetOpenAISchema()
	data, _ := json.MarshalIndent(schema, "", "  ")
	return string(data)
}
