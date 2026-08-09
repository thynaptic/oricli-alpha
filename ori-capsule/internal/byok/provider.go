package byok

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

type Provider string

const (
	ProviderOpenAI    Provider = "openai"
	ProviderAnthropic Provider = "anthropic"
	ProviderOpenCode  Provider = "opencode"
)

type Credentials struct {
	Provider Provider
	APIKey   string
	BaseURL  string // required for opencode; optional override for openai
}

type Message struct {
	Role       string     `json:"role"`
	Content    string     `json:"content,omitempty"`
	Name       string     `json:"name,omitempty"`
	ToolCallID string     `json:"tool_call_id,omitempty"`
	ToolCalls  []ToolCall `json:"tool_calls,omitempty"`
}

type ChatRequest struct {
	Model       string           `json:"model"`
	Messages    []Message        `json:"messages"`
	Tools       []ToolDefinition `json:"tools,omitempty"`
	ToolChoice  any              `json:"tool_choice,omitempty"`
	Stream      bool             `json:"stream,omitempty"`
	MaxTokens   *int             `json:"max_tokens,omitempty"`
	Temperature *float64         `json:"temperature,omitempty"`
}

type ChatResponse struct {
	ID      string `json:"id"`
	Object  string `json:"object"`
	Created int64  `json:"created"`
	Model   string `json:"model"`
	Choices []struct {
		Index        int     `json:"index"`
		Message      Message `json:"message"`
		FinishReason string  `json:"finish_reason"`
	} `json:"choices"`
	Usage map[string]int `json:"usage,omitempty"`
}

// StreamResult is the fully collected assistant text from an upstream stream.
type StreamResult struct {
	ID           string
	Model        string
	Content      string
	FinishReason string
	ToolCalls    []ToolCall
}

var httpClient = &http.Client{Timeout: 120 * time.Second}

func ParseProvider(s string) (Provider, error) {
	switch Provider(strings.ToLower(strings.TrimSpace(s))) {
	case ProviderOpenAI, "":
		return ProviderOpenAI, nil
	case ProviderAnthropic:
		return ProviderAnthropic, nil
	case ProviderOpenCode:
		return ProviderOpenCode, nil
	default:
		return "", fmt.Errorf("unsupported provider %q (want openai|anthropic|opencode)", s)
	}
}

// ChatNonStream returns a full OpenAI-shaped chat.completion response.
func ChatNonStream(ctx context.Context, cred Credentials, req ChatRequest) (*ChatResponse, error) {
	switch cred.Provider {
	case ProviderAnthropic:
		return anthropicChat(ctx, cred, req)
	case ProviderOpenAI, ProviderOpenCode:
		return openAICompatChat(ctx, cred, req)
	default:
		return nil, fmt.Errorf("unsupported provider %q", cred.Provider)
	}
}

// CollectStream reads the upstream SSE (or Anthropic stream), accumulates the
// full assistant text, and returns it for post-inference safety sanitization.
func CollectStream(ctx context.Context, cred Credentials, req ChatRequest) (*StreamResult, error) {
	req.Stream = true
	switch cred.Provider {
	case ProviderAnthropic:
		return collectAnthropicStream(ctx, cred, req)
	case ProviderOpenAI, ProviderOpenCode:
		return collectOpenAICompatStream(ctx, cred, req)
	default:
		return nil, fmt.Errorf("unsupported provider %q", cred.Provider)
	}
}

// WriteChatSSE emits an OpenAI-compatible chat.completion.chunk SSE sequence
// for already-sanitized content, then data: [DONE].
func WriteChatSSE(w io.Writer, id, model, content, finishReason string) error {
	return WriteChatSSEMessage(w, id, model, Message{Role: "assistant", Content: content}, finishReason)
}

// WriteChatSSEMessage emits SSE for an assistant message that may include tool_calls.
func WriteChatSSEMessage(w io.Writer, id, model string, msg Message, finishReason string) error {
	if id == "" {
		id = fmt.Sprintf("chatcmpl-%d", time.Now().UnixNano())
	}
	if model == "" {
		model = "passthrough"
	}
	if finishReason == "" {
		if len(msg.ToolCalls) > 0 {
			finishReason = "tool_calls"
		} else {
			finishReason = "stop"
		}
	}
	created := time.Now().Unix()
	flusher, _ := w.(http.Flusher)

	writeChunk := func(delta map[string]any, finish *string) error {
		choice := map[string]any{
			"index": 0,
			"delta": delta,
		}
		if finish != nil {
			choice["finish_reason"] = *finish
		} else {
			choice["finish_reason"] = nil
		}
		chunk := map[string]any{
			"id":      id,
			"object":  "chat.completion.chunk",
			"created": created,
			"model":   model,
			"choices": []map[string]any{choice},
		}
		b, err := json.Marshal(chunk)
		if err != nil {
			return err
		}
		if _, err := fmt.Fprintf(w, "data: %s\n\n", b); err != nil {
			return err
		}
		if flusher != nil {
			flusher.Flush()
		}
		return nil
	}

	if err := writeChunk(map[string]any{"role": "assistant"}, nil); err != nil {
		return err
	}
	content := msg.Content
	const chunkSize = 48
	for i := 0; i < len(content); {
		j := i + chunkSize
		if j > len(content) {
			j = len(content)
		}
		for j < len(content) && j > i && !utf8Start(content[j]) {
			j--
		}
		if j == i {
			j = i + 1
			for j < len(content) && !utf8Start(content[j]) {
				j++
			}
		}
		if err := writeChunk(map[string]any{"content": content[i:j]}, nil); err != nil {
			return err
		}
		i = j
	}
	for i, tc := range msg.ToolCalls {
		delta := map[string]any{
			"tool_calls": []map[string]any{{
				"index": i,
				"id":    tc.ID,
				"type":  tc.Type,
				"function": map[string]any{
					"name":      tc.Function.Name,
					"arguments": tc.Function.Arguments,
				},
			}},
		}
		if err := writeChunk(delta, nil); err != nil {
			return err
		}
	}
	fr := finishReason
	if err := writeChunk(map[string]any{}, &fr); err != nil {
		return err
	}
	if _, err := fmt.Fprintf(w, "data: [DONE]\n\n"); err != nil {
		return err
	}
	if flusher != nil {
		flusher.Flush()
	}
	return nil
}

func utf8Start(b byte) bool {
	return b&0xC0 != 0x80
}

func openAIBase(cred Credentials) string {
	base := strings.TrimRight(cred.BaseURL, "/")
	if base == "" {
		base = "https://api.openai.com/v1"
	}
	return base
}

func openAICompatChat(ctx context.Context, cred Credentials, req ChatRequest) (*ChatResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, openAIBase(cred)+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Authorization", "Bearer "+cred.APIKey)
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := httpClient.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(io.LimitReader(resp.Body, 8<<20))
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("upstream %s: %s", resp.Status, truncate(string(raw), 500))
	}
	var out ChatResponse
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, fmt.Errorf("decode upstream: %w", err)
	}
	return &out, nil
}

func collectOpenAICompatStream(ctx context.Context, cred Credentials, req ChatRequest) (*StreamResult, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, openAIBase(cred)+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Authorization", "Bearer "+cred.APIKey)
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "text/event-stream")

	resp, err := httpClient.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		raw, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
		return nil, fmt.Errorf("upstream %s: %s", resp.Status, truncate(string(raw), 500))
	}

	result := &StreamResult{
		ID:           fmt.Sprintf("chatcmpl-%d", time.Now().UnixNano()),
		Model:        req.Model,
		FinishReason: "stop",
	}
	var content strings.Builder
	toolAcc := map[int]*ToolCall{}
	scanner := bufio.NewScanner(resp.Body)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, "data: ") {
			continue
		}
		payload := strings.TrimPrefix(line, "data: ")
		if payload == "[DONE]" {
			break
		}
		var ev struct {
			ID      string `json:"id"`
			Model   string `json:"model"`
			Choices []struct {
				Delta struct {
					Content   string `json:"content"`
					ToolCalls []struct {
						Index    int    `json:"index"`
						ID       string `json:"id"`
						Type     string `json:"type"`
						Function struct {
							Name      string `json:"name"`
							Arguments string `json:"arguments"`
						} `json:"function"`
					} `json:"tool_calls"`
				} `json:"delta"`
				FinishReason *string `json:"finish_reason"`
			} `json:"choices"`
		}
		if err := json.Unmarshal([]byte(payload), &ev); err != nil {
			continue
		}
		if ev.ID != "" {
			result.ID = ev.ID
		}
		if ev.Model != "" {
			result.Model = ev.Model
		}
		if len(ev.Choices) > 0 {
			content.WriteString(ev.Choices[0].Delta.Content)
			for _, tc := range ev.Choices[0].Delta.ToolCalls {
				cur, ok := toolAcc[tc.Index]
				if !ok {
					cur = &ToolCall{Type: "function"}
					toolAcc[tc.Index] = cur
				}
				if tc.ID != "" {
					cur.ID = tc.ID
				}
				if tc.Type != "" {
					cur.Type = tc.Type
				}
				if tc.Function.Name != "" {
					cur.Function.Name = tc.Function.Name
				}
				cur.Function.Arguments += tc.Function.Arguments
			}
			if ev.Choices[0].FinishReason != nil && *ev.Choices[0].FinishReason != "" {
				result.FinishReason = *ev.Choices[0].FinishReason
			}
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	result.Content = content.String()
	if len(toolAcc) > 0 {
		idxs := make([]int, 0, len(toolAcc))
		for i := range toolAcc {
			idxs = append(idxs, i)
		}
		// insertion order not guaranteed — sort by index
		for i := 0; i < len(idxs); i++ {
			for j := i + 1; j < len(idxs); j++ {
				if idxs[j] < idxs[i] {
					idxs[i], idxs[j] = idxs[j], idxs[i]
				}
			}
		}
		for _, i := range idxs {
			result.ToolCalls = append(result.ToolCalls, *toolAcc[i])
		}
		result.ToolCalls = ensureToolCallIDs(result.ToolCalls)
		if result.FinishReason == "stop" && len(result.ToolCalls) > 0 {
			result.FinishReason = "tool_calls"
		}
	}
	return result, nil
}

// --- Anthropic Messages API → OpenAI-shaped response ---

type anthropicReq struct {
	Model      string             `json:"model"`
	MaxTokens  int                `json:"max_tokens"`
	System     string             `json:"system,omitempty"`
	Messages   []anthropicMsg     `json:"messages"`
	Tools      []anthropicToolDef `json:"tools,omitempty"`
	ToolChoice any                `json:"tool_choice,omitempty"`
	Stream     bool               `json:"stream,omitempty"`
}

func anthropicChat(ctx context.Context, cred Credentials, req ChatRequest) (*ChatResponse, error) {
	sys, msgs := msgsToAnthropic(req.Messages)
	payload := anthropicReq{
		Model:     req.Model,
		MaxTokens: maxTokensOr(req, 4096),
		System:    sys,
		Messages:  msgs,
	}
	if len(req.Tools) > 0 {
		payload.Tools = oaiToolsToAnthropic(req.Tools)
		payload.ToolChoice = oaiToolChoiceToAnthropic(req.ToolChoice)
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}
	base := strings.TrimRight(cred.BaseURL, "/")
	if base == "" {
		base = "https://api.anthropic.com"
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, base+"/v1/messages", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("x-api-key", cred.APIKey)
	httpReq.Header.Set("anthropic-version", "2023-06-01")
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := httpClient.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(io.LimitReader(resp.Body, 8<<20))
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("upstream %s: %s", resp.Status, truncate(string(raw), 500))
	}
	var meta struct {
		ID    string `json:"id"`
		Model string `json:"model"`
		Usage struct {
			InputTokens  int `json:"input_tokens"`
			OutputTokens int `json:"output_tokens"`
		} `json:"usage"`
	}
	if err := json.Unmarshal(raw, &meta); err != nil {
		return nil, err
	}
	text, calls, stopReason, err := parseAnthropicContent(raw)
	if err != nil {
		return nil, err
	}
	calls = ensureToolCallIDs(calls)
	out := &ChatResponse{
		ID:      meta.ID,
		Object:  "chat.completion",
		Created: time.Now().Unix(),
		Model:   meta.Model,
		Usage: map[string]int{
			"prompt_tokens":     meta.Usage.InputTokens,
			"completion_tokens": meta.Usage.OutputTokens,
			"total_tokens":      meta.Usage.InputTokens + meta.Usage.OutputTokens,
		},
	}
	out.Choices = []struct {
		Index        int     `json:"index"`
		Message      Message `json:"message"`
		FinishReason string  `json:"finish_reason"`
	}{{
		Index: 0,
		Message: Message{
			Role:      "assistant",
			Content:   text,
			ToolCalls: calls,
		},
		FinishReason: mapAnthropicStopReason(stopReason),
	}}
	return out, nil
}

func collectAnthropicStream(ctx context.Context, cred Credentials, req ChatRequest) (*StreamResult, error) {
	sys, msgs := msgsToAnthropic(req.Messages)
	payload := anthropicReq{
		Model:     req.Model,
		MaxTokens: maxTokensOr(req, 4096),
		System:    sys,
		Messages:  msgs,
		Stream:    true,
	}
	if len(req.Tools) > 0 {
		payload.Tools = oaiToolsToAnthropic(req.Tools)
		payload.ToolChoice = oaiToolChoiceToAnthropic(req.ToolChoice)
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}
	base := strings.TrimRight(cred.BaseURL, "/")
	if base == "" {
		base = "https://api.anthropic.com"
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, base+"/v1/messages", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("x-api-key", cred.APIKey)
	httpReq.Header.Set("anthropic-version", "2023-06-01")
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "text/event-stream")

	resp, err := httpClient.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		raw, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
		return nil, fmt.Errorf("upstream %s: %s", resp.Status, truncate(string(raw), 500))
	}

	result := &StreamResult{
		ID:           fmt.Sprintf("chatcmpl-%d", time.Now().UnixNano()),
		Model:        req.Model,
		FinishReason: "stop",
	}
	var content strings.Builder
	type toolBlock struct {
		id, name, args string
	}
	blocks := map[int]*toolBlock{}
	scanner := bufio.NewScanner(resp.Body)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, "data: ") {
			continue
		}
		payload := strings.TrimPrefix(line, "data: ")
		if payload == "[DONE]" {
			break
		}
		var ev struct {
			Type         string `json:"type"`
			Index        int    `json:"index"`
			ContentBlock struct {
				Type string `json:"type"`
				ID   string `json:"id"`
				Name string `json:"name"`
			} `json:"content_block"`
			Delta struct {
				Type        string `json:"type"`
				Text        string `json:"text"`
				PartialJSON string `json:"partial_json"`
				StopReason  string `json:"stop_reason"`
			} `json:"delta"`
			Message struct {
				ID    string `json:"id"`
				Model string `json:"model"`
			} `json:"message"`
		}
		if err := json.Unmarshal([]byte(payload), &ev); err != nil {
			continue
		}
		switch ev.Type {
		case "message_start":
			if ev.Message.ID != "" {
				result.ID = "chatcmpl-" + ev.Message.ID
			}
			if ev.Message.Model != "" {
				result.Model = ev.Message.Model
			}
		case "content_block_start":
			if ev.ContentBlock.Type == "tool_use" {
				blocks[ev.Index] = &toolBlock{id: ev.ContentBlock.ID, name: ev.ContentBlock.Name}
			}
		case "content_block_delta":
			if ev.Delta.Text != "" {
				content.WriteString(ev.Delta.Text)
			}
			if ev.Delta.PartialJSON != "" {
				if b := blocks[ev.Index]; b != nil {
					b.args += ev.Delta.PartialJSON
				}
			}
		case "message_delta":
			if ev.Delta.StopReason != "" {
				result.FinishReason = mapAnthropicStopReason(ev.Delta.StopReason)
			}
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	result.Content = content.String()
	if len(blocks) > 0 {
		idxs := make([]int, 0, len(blocks))
		for i := range blocks {
			idxs = append(idxs, i)
		}
		for i := 0; i < len(idxs); i++ {
			for j := i + 1; j < len(idxs); j++ {
				if idxs[j] < idxs[i] {
					idxs[i], idxs[j] = idxs[j], idxs[i]
				}
			}
		}
		for _, i := range idxs {
			b := blocks[i]
			args := b.args
			if args == "" {
				args = "{}"
			}
			result.ToolCalls = append(result.ToolCalls, ToolCall{
				ID:   b.id,
				Type: "function",
				Function: ToolFunctionCall{
					Name:      b.name,
					Arguments: args,
				},
			})
		}
		result.ToolCalls = ensureToolCallIDs(result.ToolCalls)
		if result.FinishReason == "stop" {
			result.FinishReason = "tool_calls"
		}
	}
	return result, nil
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}
