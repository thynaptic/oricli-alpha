package tools

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"sync"

	"github.com/thynaptic/ori-capsule/internal/byok"
)

// Handler executes an allowlisted tool. Returns a string payload for role=tool.
type Handler func(args map[string]any) (string, error)

type entry struct {
	def     byok.ToolDefinition
	handler Handler
}

// Registry is an allowlist of callable tools for BYOK auto mode / schema inject.
type Registry struct {
	mu     sync.RWMutex
	byName map[string]entry
}

func NewRegistry() *Registry {
	return &Registry{byName: make(map[string]entry)}
}

// Register adds or replaces a tool. Name must be a non-empty function name.
func (r *Registry) Register(def byok.ToolDefinition, h Handler) error {
	if r == nil || h == nil {
		return fmt.Errorf("nil registry or handler")
	}
	if def.Type == "" {
		def.Type = "function"
	}
	name := strings.TrimSpace(def.Function.Name)
	if name == "" {
		return fmt.Errorf("tool name required")
	}
	def.Function.Name = name
	r.mu.Lock()
	r.byName[name] = entry{def: def, handler: h}
	r.mu.Unlock()
	return nil
}

// Schemas returns OpenAI tool definitions sorted by name.
func (r *Registry) Schemas() []byok.ToolDefinition {
	if r == nil {
		return nil
	}
	r.mu.RLock()
	defer r.mu.RUnlock()
	names := make([]string, 0, len(r.byName))
	for n := range r.byName {
		names = append(names, n)
	}
	sort.Strings(names)
	out := make([]byok.ToolDefinition, 0, len(names))
	for _, n := range names {
		out = append(out, r.byName[n].def)
	}
	return out
}

// Names returns sorted tool names.
func (r *Registry) Names() []string {
	schemas := r.Schemas()
	out := make([]string, len(schemas))
	for i, s := range schemas {
		out[i] = s.Function.Name
	}
	return out
}

// Has reports whether name is allowlisted.
func (r *Registry) Has(name string) bool {
	if r == nil {
		return false
	}
	r.mu.RLock()
	defer r.mu.RUnlock()
	_, ok := r.byName[strings.TrimSpace(name)]
	return ok
}

// Execute runs an allowlisted tool. Unknown names return a structured error string (not panic).
func (r *Registry) Execute(name string, argsJSON string) string {
	name = strings.TrimSpace(name)
	if r == nil || !r.Has(name) {
		return errJSON("unknown_tool", "tool %q is not in the capsule allowlist", name)
	}
	args, err := byok.ParseToolArguments(argsJSON)
	if err != nil {
		return errJSON("bad_arguments", "invalid JSON arguments: %v", err)
	}
	r.mu.RLock()
	ent := r.byName[name]
	r.mu.RUnlock()
	out, err := ent.handler(args)
	if err != nil {
		return errJSON("exec_error", "%v", err)
	}
	if strings.TrimSpace(out) == "" {
		return "{}"
	}
	return out
}

// ExecuteCalls runs each tool_call and returns role=tool messages in order.
func (r *Registry) ExecuteCalls(calls []byok.ToolCall) []byok.Message {
	out := make([]byok.Message, 0, len(calls))
	for _, c := range calls {
		name := c.Function.Name
		content := r.Execute(name, c.Function.Arguments)
		out = append(out, byok.ToolResultMessage(c.ID, name, content))
	}
	return out
}

func errJSON(code, format string, args ...any) string {
	b, _ := json.Marshal(map[string]any{
		"error":   code,
		"message": fmt.Sprintf(format, args...),
	})
	return string(b)
}

func objectSchema(props map[string]any, required ...string) map[string]any {
	schema := map[string]any{
		"type":       "object",
		"properties": props,
	}
	if len(required) > 0 {
		schema["required"] = required
	}
	return schema
}

func strProp(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}

func boolProp(desc string) map[string]any {
	return map[string]any{"type": "boolean", "description": desc}
}

func numProp(desc string) map[string]any {
	return map[string]any{"type": "number", "description": desc}
}
