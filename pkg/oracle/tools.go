package oracle

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
)

// ToolDef is an Anthropic-native tool definition.
type ToolDef struct {
	Name        string         `json:"name"`
	Description string         `json:"description,omitempty"`
	InputSchema map[string]any `json:"input_schema"`
}

// ToolCall is a tool invocation returned by the model.
type ToolCall struct {
	ID    string         `json:"id"`
	Name  string         `json:"name"`
	Input map[string]any `json:"input"`
}

// ToolResult is the caller's response to a ToolCall.
type ToolResult struct {
	ToolUseID string `json:"tool_use_id"`
	Content   string `json:"content"`
}

// ChatRound is the result of one conversation turn with tools enabled.
// Exactly one of Text or Calls will be populated.
type ChatRound struct {
	Text  string     // populated when the model produced a final text response
	Calls []ToolCall // populated when the model wants to invoke tools
}

// ChatWithTools performs one non-streaming turn against the Anthropic API with
// tool use enabled. The caller is responsible for executing any returned tool
// calls and looping back with results as new messages.
func ChatWithTools(ctx context.Context, messages []Message, tools []ToolDef, decision Decision) (*ChatRound, error) {
	if !Available() {
		return nil, fmt.Errorf("oracle: ANTHROPIC_API_KEY not configured")
	}

	apiMsgs, err := convertMessagesForTools(messages)
	if err != nil {
		return nil, fmt.Errorf("oracle: convert messages: %w", err)
	}

	outputTokens := maxTokens
	payload := map[string]any{
		"model":    decision.Model,
		"messages": apiMsgs,
	}

	// System prompt with cache_control.
	systemPrompt := ""
	for _, m := range messages {
		if m.Role == "system" {
			systemPrompt = m.Content
			break
		}
	}
	if systemPrompt == "" {
		systemPrompt = getAgentPrompt(decision.Agent)
	}
	if systemPrompt != "" {
		payload["system"] = []map[string]any{{
			"type":          "text",
			"text":          systemPrompt,
			"cache_control": map[string]any{"type": "ephemeral"},
		}}
	}

	// Tool definitions — converted to Anthropic format.
	if len(tools) > 0 {
		payload["tools"] = tools
	}

	// Extended thinking is incompatible with tool use in the same turn.
	payload["max_tokens"] = outputTokens

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("oracle: marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		anthropicBase+"/messages", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("oracle: build request: %w", err)
	}
	req.Header.Set("content-type", "application/json")
	req.Header.Set("x-api-key", os.Getenv("ANTHROPIC_API_KEY"))
	req.Header.Set("anthropic-version", anthropicVersion)
	req.Header.Set("anthropic-beta", "prompt-caching-2024-07-31")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("oracle: anthropic request: %w", err)
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("oracle: anthropic status %d: %s", resp.StatusCode, string(raw))
	}

	return parseToolResponse(raw)
}

// parseToolResponse decodes an Anthropic messages response into a ChatRound.
func parseToolResponse(raw []byte) (*ChatRound, error) {
	var result struct {
		StopReason string `json:"stop_reason"`
		Content    []struct {
			Type  string         `json:"type"`
			Text  string         `json:"text,omitempty"`
			ID    string         `json:"id,omitempty"`
			Name  string         `json:"name,omitempty"`
			Input map[string]any `json:"input,omitempty"`
		} `json:"content"`
		Error *struct {
			Message string `json:"message"`
		} `json:"error,omitempty"`
	}
	if err := json.Unmarshal(raw, &result); err != nil {
		return nil, fmt.Errorf("oracle: decode response: %w", err)
	}
	if result.Error != nil {
		return nil, fmt.Errorf("oracle: anthropic error: %s", result.Error.Message)
	}

	round := &ChatRound{}

	if result.StopReason == "tool_use" {
		for _, block := range result.Content {
			if block.Type == "tool_use" {
				round.Calls = append(round.Calls, ToolCall{
					ID:    block.ID,
					Name:  block.Name,
					Input: block.Input,
				})
			}
		}
		log.Printf("[Oracle:Tools] tool_use — %d call(s): %s",
			len(round.Calls), toolNames(round.Calls))
		return round, nil
	}

	// Final text response — collect all text blocks.
	var sb strings.Builder
	for _, block := range result.Content {
		if block.Type == "text" {
			sb.WriteString(block.Text)
		}
	}
	round.Text = strings.TrimSpace(sb.String())
	return round, nil
}

// convertMessagesForTools converts Oracle Messages to the Anthropic API format,
// handling the OpenAI→Anthropic translation for tool-related message types:
//
//   - role "tool" (OpenAI) → role "user" with tool_result content block (Anthropic)
//   - role "assistant" with ToolCalls → role "assistant" with tool_use content blocks
//   - system messages are extracted separately (handled by the caller)
//   - all other messages pass through as plain {role, content} objects
//
// The returned slice uses map[string]any so content can be either a string or
// an array of content blocks depending on the message type.
func convertMessagesForTools(messages []Message) ([]map[string]any, error) {
	var out []map[string]any

	for _, m := range messages {
		if m.Role == "system" {
			continue // handled separately as system prompt
		}

		switch m.Role {
		case "tool":
			// OpenAI tool result → Anthropic tool_result content block.
			// ToolCallID on the Message carries the tool_use_id to match back.
			out = append(out, map[string]any{
				"role": "user",
				"content": []map[string]any{{
					"type":        "tool_result",
					"tool_use_id": m.ToolCallID,
					"content":     m.Content,
				}},
			})

		default:
			// Assistant messages that contain tool_calls need content block format.
			if m.Role == "assistant" && len(m.ToolCalls) > 0 {
				var blocks []map[string]any
				if m.Content != "" {
					blocks = append(blocks, map[string]any{
						"type": "text",
						"text": m.Content,
					})
				}
				for _, tc := range m.ToolCalls {
					var input map[string]any
					_ = json.Unmarshal([]byte(tc.Function.Arguments), &input)
					blocks = append(blocks, map[string]any{
						"type":  "tool_use",
						"id":    tc.ID,
						"name":  tc.Function.Name,
						"input": input,
					})
				}
				out = append(out, map[string]any{
					"role":    "assistant",
					"content": blocks,
				})
			} else {
				out = append(out, map[string]any{
					"role":    m.Role,
					"content": m.Content,
				})
			}
		}
	}
	return out, nil
}

// OAIToolDefsToOracle converts OpenAI-format ToolDefinitions to Anthropic-native ToolDefs.
// OpenAI wraps function schemas under a "function" key with "parameters";
// Anthropic uses a flat structure with "input_schema".
func OAIToolDefsToOracle(oaiTools []OAIToolDefinition) []ToolDef {
	out := make([]ToolDef, 0, len(oaiTools))
	for _, t := range oaiTools {
		schema, _ := toStringMap(t.Function.Parameters)
		out = append(out, ToolDef{
			Name:        t.Function.Name,
			Description: t.Function.Description,
			InputSchema: schema,
		})
	}
	return out
}

// OAIToolDefinition is the OpenAI-format tool definition sent by API callers.
type OAIToolDefinition struct {
	Type     string `json:"type"`
	Function struct {
		Name        string `json:"name"`
		Description string `json:"description,omitempty"`
		Parameters  any    `json:"parameters,omitempty"`
	} `json:"function"`
}

// ToolCallsToOAI converts Anthropic ToolCalls to OpenAI tool_calls format.
func ToolCallsToOAI(calls []ToolCall) []map[string]any {
	out := make([]map[string]any, 0, len(calls))
	for _, c := range calls {
		args, _ := json.Marshal(c.Input)
		out = append(out, map[string]any{
			"id":   c.ID,
			"type": "function",
			"function": map[string]any{
				"name":      c.Name,
				"arguments": string(args),
			},
		})
	}
	return out
}

func toolNames(calls []ToolCall) string {
	names := make([]string, len(calls))
	for i, c := range calls {
		names[i] = c.Name
	}
	return strings.Join(names, ", ")
}

func toStringMap(v any) (map[string]any, error) {
	if v == nil {
		return map[string]any{"type": "object"}, nil
	}
	b, err := json.Marshal(v)
	if err != nil {
		return nil, err
	}
	var m map[string]any
	if err := json.Unmarshal(b, &m); err != nil {
		return nil, err
	}
	return m, nil
}
