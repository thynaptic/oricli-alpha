package byok

import (
	"encoding/json"
	"fmt"
	"strings"
)

// anthropic content can be a string or a list of blocks.
type anthropicContentBlock struct {
	Type      string         `json:"type"`
	Text      string         `json:"text,omitempty"`
	ID        string         `json:"id,omitempty"`
	Name      string         `json:"name,omitempty"`
	Input     map[string]any `json:"input,omitempty"`
	ToolUseID string         `json:"tool_use_id,omitempty"`
	Content   string         `json:"content,omitempty"`
}

type anthropicMsg struct {
	Role    string `json:"role"`
	Content any    `json:"content"`
}

type anthropicToolDef struct {
	Name        string `json:"name"`
	Description string `json:"description,omitempty"`
	InputSchema any    `json:"input_schema"`
}

func oaiToolsToAnthropic(tools []ToolDefinition) []anthropicToolDef {
	out := make([]anthropicToolDef, 0, len(tools))
	for _, t := range tools {
		schema := t.Function.Parameters
		if schema == nil {
			schema = map[string]any{"type": "object", "properties": map[string]any{}}
		}
		out = append(out, anthropicToolDef{
			Name:        t.Function.Name,
			Description: t.Function.Description,
			InputSchema: schema,
		})
	}
	return out
}

func oaiToolChoiceToAnthropic(choice any) any {
	switch v := choice.(type) {
	case nil:
		return nil
	case string:
		switch strings.ToLower(v) {
		case "auto":
			return map[string]any{"type": "auto"}
		case "none":
			return map[string]any{"type": "none"}
		case "required":
			return map[string]any{"type": "any"}
		default:
			return map[string]any{"type": "auto"}
		}
	case map[string]any:
		// {"type":"function","function":{"name":"x"}}
		if fn, ok := v["function"].(map[string]any); ok {
			if name, _ := fn["name"].(string); name != "" {
				return map[string]any{"type": "tool", "name": name}
			}
		}
	}
	return map[string]any{"type": "auto"}
}

func msgsToAnthropic(msgs []Message) (system string, rest []anthropicMsg) {
	for _, m := range msgs {
		switch m.Role {
		case "system":
			if system != "" {
				system += "\n"
			}
			system += m.Content
		case "assistant":
			if len(m.ToolCalls) == 0 {
				rest = append(rest, anthropicMsg{Role: "assistant", Content: m.Content})
				continue
			}
			blocks := make([]anthropicContentBlock, 0, len(m.ToolCalls)+1)
			if strings.TrimSpace(m.Content) != "" {
				blocks = append(blocks, anthropicContentBlock{Type: "text", Text: m.Content})
			}
			for _, tc := range m.ToolCalls {
				input, _ := ParseToolArguments(tc.Function.Arguments)
				blocks = append(blocks, anthropicContentBlock{
					Type:  "tool_use",
					ID:    tc.ID,
					Name:  tc.Function.Name,
					Input: input,
				})
			}
			rest = append(rest, anthropicMsg{Role: "assistant", Content: blocks})
		case "tool":
			blocks := []anthropicContentBlock{{
				Type:      "tool_result",
				ToolUseID: m.ToolCallID,
				Content:   m.Content,
			}}
			// Anthropic requires tool_result inside a user message.
			if len(rest) > 0 && rest[len(rest)-1].Role == "user" {
				if prev, ok := rest[len(rest)-1].Content.([]anthropicContentBlock); ok {
					rest[len(rest)-1].Content = append(prev, blocks...)
					continue
				}
			}
			rest = append(rest, anthropicMsg{Role: "user", Content: blocks})
		case "user":
			rest = append(rest, anthropicMsg{Role: "user", Content: m.Content})
		default:
			rest = append(rest, anthropicMsg{Role: "user", Content: m.Content})
		}
	}
	return system, rest
}

func parseAnthropicContent(raw []byte) (text string, calls []ToolCall, stopReason string, err error) {
	var ar struct {
		StopReason string `json:"stop_reason"`
		Content    []struct {
			Type  string          `json:"type"`
			Text  string          `json:"text"`
			ID    string          `json:"id"`
			Name  string          `json:"name"`
			Input json.RawMessage `json:"input"`
		} `json:"content"`
	}
	if err := json.Unmarshal(raw, &ar); err != nil {
		return "", nil, "", err
	}
	var sb strings.Builder
	for _, c := range ar.Content {
		switch c.Type {
		case "text":
			sb.WriteString(c.Text)
		case "tool_use":
			args := "{}"
			if len(c.Input) > 0 {
				args = string(c.Input)
			}
			calls = append(calls, ToolCall{
				ID:   c.ID,
				Type: "function",
				Function: ToolFunctionCall{
					Name:      c.Name,
					Arguments: args,
				},
			})
		}
	}
	return sb.String(), calls, ar.StopReason, nil
}

func mapAnthropicStopReason(s string) string {
	switch s {
	case "end_turn", "stop_sequence":
		return "stop"
	case "max_tokens":
		return "length"
	case "tool_use":
		return "tool_calls"
	default:
		if s == "" {
			return "stop"
		}
		return s
	}
}

func maxTokensOr(req ChatRequest, def int) int {
	if req.MaxTokens != nil && *req.MaxTokens > 0 {
		return *req.MaxTokens
	}
	return def
}

func ensureToolCallIDs(calls []ToolCall) []ToolCall {
	for i := range calls {
		if calls[i].ID == "" {
			calls[i].ID = fmt.Sprintf("call_%d", i+1)
		}
		if calls[i].Type == "" {
			calls[i].Type = "function"
		}
	}
	return calls
}
