// Package byok implements Bring-Your-Own-Key LLM providers for ori-capsule.
// Supported: openai, anthropic, opencode (OpenAI-compatible base URL).
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

// ChatStream writes OpenAI SSE chunks to w (data: {...}\n\n) and ends with data: [DONE].
func ChatStream(ctx context.Context, cred Credentials, req ChatRequest, w io.Writer) error {
	req.Stream = true
	switch cred.Provider {
	case ProviderAnthropic:
		return anthropicStream(ctx, cred, req, w)
	case ProviderOpenAI, ProviderOpenCode:
		return openAICompatStream(ctx, cred, req, w)
	default:
		return fmt.Errorf("unsupported provider %q", cred.Provider)
	}
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

func openAICompatStream(ctx context.Context, cred Credentials, req ChatRequest, w io.Writer) error {
	body, err := json.Marshal(req)
	if err != nil {
		return err
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, openAIBase(cred)+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return err
	}
	httpReq.Header.Set("Authorization", "Bearer "+cred.APIKey)
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "text/event-stream")

	resp, err := httpClient.Do(httpReq)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		raw, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
		return fmt.Errorf("upstream %s: %s", resp.Status, truncate(string(raw), 500))
	}
	_, err = io.Copy(w, resp.Body)
	return err
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
			// tool / other → treat as user context for MVP
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

func anthropicStream(ctx context.Context, cred Credentials, req ChatRequest, w io.Writer) error {
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
		return err
	}
	base := strings.TrimRight(cred.BaseURL, "/")
	if base == "" {
		base = "https://api.anthropic.com"
	}
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, base+"/v1/messages", bytes.NewReader(body))
	if err != nil {
		return err
	}
	httpReq.Header.Set("x-api-key", cred.APIKey)
	httpReq.Header.Set("anthropic-version", "2023-06-01")
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "text/event-stream")

	resp, err := httpClient.Do(httpReq)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		raw, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
		return fmt.Errorf("upstream %s: %s", resp.Status, truncate(string(raw), 500))
	}

	id := fmt.Sprintf("chatcmpl-%d", time.Now().UnixNano())
	flusher, _ := w.(http.Flusher)
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
		}
		if err := json.Unmarshal([]byte(payload), &ev); err != nil {
			continue
		}
		if ev.Type != "content_block_delta" || ev.Delta.Text == "" {
			continue
		}
		chunk := map[string]any{
			"id":      id,
			"object":  "chat.completion.chunk",
			"created": time.Now().Unix(),
			"model":   req.Model,
			"choices": []map[string]any{{
				"index": 0,
				"delta": map[string]string{"content": ev.Delta.Text},
			}},
		}
		b, _ := json.Marshal(chunk)
		fmt.Fprintf(w, "data: %s\n\n", b)
		if flusher != nil {
			flusher.Flush()
		}
	}
	fmt.Fprintf(w, "data: [DONE]\n\n")
	if flusher != nil {
		flusher.Flush()
	}
	return scanner.Err()
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
