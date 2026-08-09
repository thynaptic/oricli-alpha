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
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ChatRequest struct {
	Model    string    `json:"model"`
	Messages []Message `json:"messages"`
	Stream   bool      `json:"stream,omitempty"`
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
	if id == "" {
		id = fmt.Sprintf("chatcmpl-%d", time.Now().UnixNano())
	}
	if model == "" {
		model = "passthrough"
	}
	if finishReason == "" {
		finishReason = "stop"
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
	// Emit content in reasonable chunks so clients still see progressive SSE,
	// after the full text has already been safety-sanitized.
	const chunkSize = 48
	for i := 0; i < len(content); {
		j := i + chunkSize
		if j > len(content) {
			j = len(content)
		}
		// Prefer breaking on rune boundaries for UTF-8 safety.
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
					Content string `json:"content"`
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
			if ev.Choices[0].FinishReason != nil && *ev.Choices[0].FinishReason != "" {
				result.FinishReason = *ev.Choices[0].FinishReason
			}
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	result.Content = content.String()
	return result, nil
}

// --- Anthropic Messages API → OpenAI-shaped response ---

type anthropicReq struct {
	Model     string             `json:"model"`
	MaxTokens int                `json:"max_tokens"`
	System    string             `json:"system,omitempty"`
	Messages  []anthropicMessage `json:"messages"`
	Stream    bool               `json:"stream,omitempty"`
}

type anthropicMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

func splitSystem(msgs []Message) (system string, rest []anthropicMessage) {
	for _, m := range msgs {
		switch m.Role {
		case "system":
			if system != "" {
				system += "\n"
			}
			system += m.Content
		case "assistant", "user":
			rest = append(rest, anthropicMessage{Role: m.Role, Content: m.Content})
		default:
			rest = append(rest, anthropicMessage{Role: "user", Content: m.Content})
		}
	}
	return system, rest
}

func anthropicChat(ctx context.Context, cred Credentials, req ChatRequest) (*ChatResponse, error) {
	sys, msgs := splitSystem(req.Messages)
	payload := anthropicReq{
		Model:     req.Model,
		MaxTokens: 4096,
		System:    sys,
		Messages:  msgs,
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
	var ar struct {
		ID         string `json:"id"`
		Model      string `json:"model"`
		StopReason string `json:"stop_reason"`
		Content    []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
		Usage struct {
			InputTokens  int `json:"input_tokens"`
			OutputTokens int `json:"output_tokens"`
		} `json:"usage"`
	}
	if err := json.Unmarshal(raw, &ar); err != nil {
		return nil, err
	}
	var text strings.Builder
	for _, c := range ar.Content {
		if c.Type == "text" {
			text.WriteString(c.Text)
		}
	}
	out := &ChatResponse{
		ID:      ar.ID,
		Object:  "chat.completion",
		Created: time.Now().Unix(),
		Model:   ar.Model,
		Usage: map[string]int{
			"prompt_tokens":     ar.Usage.InputTokens,
			"completion_tokens": ar.Usage.OutputTokens,
			"total_tokens":      ar.Usage.InputTokens + ar.Usage.OutputTokens,
		},
	}
	out.Choices = []struct {
		Index        int     `json:"index"`
		Message      Message `json:"message"`
		FinishReason string  `json:"finish_reason"`
	}{{
		Index:        0,
		Message:      Message{Role: "assistant", Content: text.String()},
		FinishReason: mapAnthropicStop(ar.StopReason),
	}}
	return out, nil
}

func collectAnthropicStream(ctx context.Context, cred Credentials, req ChatRequest) (*StreamResult, error) {
	sys, msgs := splitSystem(req.Messages)
	payload := anthropicReq{
		Model:     req.Model,
		MaxTokens: 4096,
		System:    sys,
		Messages:  msgs,
		Stream:    true,
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
			Type  string `json:"type"`
			Delta struct {
				Type string `json:"type"`
				Text string `json:"text"`
			} `json:"delta"`
			Message struct {
				ID    string `json:"id"`
				Model string `json:"model"`
			} `json:"message"`
			StopReason string `json:"stop_reason"`
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
		case "content_block_delta":
			if ev.Delta.Text != "" {
				content.WriteString(ev.Delta.Text)
			}
		case "message_delta":
			if ev.StopReason != "" {
				result.FinishReason = mapAnthropicStop(ev.StopReason)
			}
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	result.Content = content.String()
	return result, nil
}

func mapAnthropicStop(s string) string {
	switch s {
	case "end_turn", "stop_sequence":
		return "stop"
	case "max_tokens":
		return "length"
	default:
		if s == "" {
			return "stop"
		}
		return s
	}
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}
