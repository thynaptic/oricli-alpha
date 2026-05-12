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

// ToolDef is ORI's internal tool definition.
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

type openAIResponseOutputItem struct {
	ID        string `json:"id,omitempty"`
	Type      string `json:"type"`
	CallID    string `json:"call_id,omitempty"`
	Name      string `json:"name,omitempty"`
	Arguments string `json:"arguments,omitempty"`
	Content   []struct {
		Type string `json:"type"`
		Text string `json:"text"`
	} `json:"content,omitempty"`
}

// ChatWithTools performs one non-streaming turn against the OpenAI API with
// tool use enabled. The caller is responsible for executing any returned tool
// calls and looping back with results as new messages.
func ChatWithTools(ctx context.Context, messages []Message, tools []ToolDef, decision Decision) (*ChatRound, error) {
	if !Available() {
		return nil, fmt.Errorf("oracle: OPENAI_API_KEY not configured")
	}

	apiMsgs, err := convertMessagesForTools(messages)
	if err != nil {
		return nil, fmt.Errorf("oracle: convert messages: %w", err)
	}
	systemPrompt := ""
	for _, m := range messages {
		if m.Role == "system" {
			systemPrompt = m.Content
			break
		}
	}
	if !hasSystemMessage(messages) {
		systemPrompt = getAgentPrompt(decision.Agent)
	}

	payload := map[string]any{
		"model":             decision.Model,
		"input":             apiMsgs,
		"store":             false,
		"max_output_tokens": maxTokens,
	}
	if strings.TrimSpace(systemPrompt) != "" {
		payload["instructions"] = systemPrompt
	}

	if len(tools) > 0 {
		payload["tools"] = toolDefsToOpenAIResponses(tools)
		payload["tool_choice"] = "auto"
		payload["parallel_tool_calls"] = true
	}
	if effort := reasoningEffortForRoute(decision.Route); effort != "" {
		payload["reasoning"] = map[string]any{"effort": effort}
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("oracle: marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		openAIBase+"/responses", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("oracle: build request: %w", err)
	}
	req.Header.Set("content-type", "application/json")
	req.Header.Set("authorization", "Bearer "+os.Getenv("OPENAI_API_KEY"))

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("oracle: openai responses request: %w", err)
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("oracle: openai responses status %d: %s", resp.StatusCode, string(raw))
	}

	return parseToolResponse(raw)
}

func hasSystemMessage(messages []Message) bool {
	for _, m := range messages {
		if m.Role == "system" {
			return true
		}
	}
	return false
}

// parseToolResponse decodes an OpenAI Responses API response into a ChatRound.
func parseToolResponse(raw []byte) (*ChatRound, error) {
	var result struct {
		OutputText string                     `json:"output_text"`
		Output     []openAIResponseOutputItem `json:"output"`
		Error      *struct {
			Message string `json:"message"`
		} `json:"error,omitempty"`
	}
	if err := json.Unmarshal(raw, &result); err != nil {
		return nil, fmt.Errorf("oracle: decode response: %w", err)
	}
	if result.Error != nil {
		return nil, fmt.Errorf("oracle: openai error: %s", result.Error.Message)
	}

	round := &ChatRound{}
	for _, item := range result.Output {
		if item.Type == "function_call" || item.Type == "custom_tool_call" {
			var input map[string]any
			if strings.TrimSpace(item.Arguments) != "" {
				_ = json.Unmarshal([]byte(item.Arguments), &input)
			}
			id := item.CallID
			if id == "" {
				id = item.ID
			}
			round.Calls = append(round.Calls, ToolCall{
				ID:    id,
				Name:  item.Name,
				Input: input,
			})
		}
	}
	if len(round.Calls) > 0 {
		log.Printf("[Oracle:Tools] tool_use — %d call(s): %s",
			len(round.Calls), toolNames(round.Calls))
		return round, nil
	}

	round.Text = strings.TrimSpace(result.OutputText)
	if round.Text == "" {
		round.Text = strings.TrimSpace(openAIResponseOutputText(result.Output))
	}
	return round, nil
}

// convertMessagesForTools converts Oracle Messages to OpenAI Responses input.
func convertMessagesForTools(messages []Message) ([]map[string]any, error) {
	return openAIResponseInputFromMessages(messages)
}

func openAIResponseInputFromMessages(messages []Message) ([]map[string]any, error) {
	var out []map[string]any

	for _, m := range messages {
		if m.Role == "system" {
			continue
		}
		if m.Role == "tool" {
			out = append(out, map[string]any{
				"type":    "function_call_output",
				"call_id": m.ToolCallID,
				"output":  m.Content,
			})
			continue
		}
		if m.Role == "assistant" && len(m.ToolCalls) > 0 {
			if strings.TrimSpace(m.Content) != "" {
				out = append(out, map[string]any{
					"role":    "assistant",
					"content": m.Content,
				})
			}
			for _, tc := range m.ToolCalls {
				out = append(out, map[string]any{
					"type":      "function_call",
					"call_id":   tc.ID,
					"name":      tc.Function.Name,
					"arguments": tc.Function.Arguments,
				})
			}
			continue
		}
		out = append(out, map[string]any{
			"role":    m.Role,
			"content": m.Content,
		})
	}
	return out, nil
}

// OAIToolDefsToOracle converts OpenAI-format ToolDefinitions to ORI ToolDefs.
// OpenAI wraps function schemas under a "function" key with "parameters";
// ORI stores a flat structure with "input_schema".
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

// ToolCallsToOAI converts ORI ToolCalls to OpenAI tool_calls format.
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

func toolDefsToOpenAIResponses(tools []ToolDef) []map[string]any {
	out := make([]map[string]any, 0, len(tools))
	for _, t := range tools {
		out = append(out, map[string]any{
			"type":        "function",
			"name":        t.Name,
			"description": t.Description,
			"parameters":  t.InputSchema,
		})
	}
	return out
}

func openAIResponseOutputText(output []openAIResponseOutputItem) string {
	var sb strings.Builder
	for _, item := range output {
		if item.Type != "message" {
			continue
		}
		for _, part := range item.Content {
			if part.Type == "output_text" || part.Type == "text" {
				sb.WriteString(part.Text)
			}
		}
	}
	return sb.String()
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
