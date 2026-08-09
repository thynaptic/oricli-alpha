package byok

import (
	"encoding/json"
	"strings"
)

// ToolDefinition is an OpenAI-compatible function tool schema.
type ToolDefinition struct {
	Type     string       `json:"type"` // "function"
	Function ToolFunction `json:"function"`
}

type ToolFunction struct {
	Name        string `json:"name"`
	Description string `json:"description,omitempty"`
	Parameters  any    `json:"parameters,omitempty"`
}

// ToolCall is an assistant-requested function invocation.
type ToolCall struct {
	ID       string           `json:"id"`
	Type     string           `json:"type"` // "function"
	Function ToolFunctionCall `json:"function"`
}

type ToolFunctionCall struct {
	Name      string `json:"name"`
	Arguments string `json:"arguments"` // JSON object as string
}

// HasToolPayload reports whether the request carries tools or tool history.
func HasToolPayload(req ChatRequest) bool {
	if len(req.Tools) > 0 {
		return true
	}
	for _, m := range req.Messages {
		if len(m.ToolCalls) > 0 || m.Role == "tool" || m.ToolCallID != "" {
			return true
		}
	}
	return false
}

// TextContent returns message text for safety/memory (ignores tool_calls).
func (m Message) TextContent() string {
	return m.Content
}

// AssistantToolMessage builds an assistant message with tool_calls.
func AssistantToolMessage(content string, calls []ToolCall) Message {
	return Message{Role: "assistant", Content: content, ToolCalls: calls}
}

// ToolResultMessage builds a role=tool message for a prior tool_call_id.
func ToolResultMessage(toolCallID, name, content string) Message {
	return Message{
		Role:       "tool",
		Content:    content,
		Name:       name,
		ToolCallID: toolCallID,
	}
}

// ParseToolArguments unmarshals tool call arguments JSON into a map.
func ParseToolArguments(args string) (map[string]any, error) {
	args = strings.TrimSpace(args)
	if args == "" {
		return map[string]any{}, nil
	}
	var out map[string]any
	if err := json.Unmarshal([]byte(args), &out); err != nil {
		return nil, err
	}
	if out == nil {
		out = map[string]any{}
	}
	return out, nil
}
