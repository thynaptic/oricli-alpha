package llm

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

const (
	haikusModel   = "claude-haiku-4-5-20251001"
	haikusBaseURL = "https://api.anthropic.com/v1/messages"
	haikusTimeout = 20 * time.Second
)

var haikusClient = &http.Client{Timeout: haikusTimeout}

// Available reports whether an Anthropic API key is configured.
func Available() bool {
	return strings.TrimSpace(os.Getenv("ANTHROPIC_API_KEY")) != ""
}

type haikusContentBlock struct {
	Type         string            `json:"type"`
	Text         string            `json:"text"`
	CacheControl *haikusCacheCtrl  `json:"cache_control,omitempty"`
}

type haikusCacheCtrl struct {
	Type string `json:"type"`
}

type haikusMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type haikusRequest struct {
	Model     string               `json:"model"`
	MaxTokens int                  `json:"max_tokens"`
	System    []haikusContentBlock `json:"system,omitempty"`
	Messages  []haikusMessage      `json:"messages"`
}

type haikusResponse struct {
	Content []struct {
		Type string `json:"type"`
		Text string `json:"text"`
	} `json:"content"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

// Chat sends a prompt to Haiku with prompt caching on the system block.
// system may be empty. Falls back gracefully on any error — callers have heuristic fallbacks.
func Chat(ctx context.Context, system, prompt string) (string, error) {
	key := strings.TrimSpace(os.Getenv("ANTHROPIC_API_KEY"))
	if key == "" {
		return "", fmt.Errorf("ANTHROPIC_API_KEY not set")
	}

	req := haikusRequest{
		Model:     haikusModel,
		MaxTokens: 512,
		Messages:  []haikusMessage{{Role: "user", Content: prompt}},
	}

	if strings.TrimSpace(system) != "" {
		req.System = []haikusContentBlock{
			{
				Type:         "text",
				Text:         system,
				CacheControl: &haikusCacheCtrl{Type: "ephemeral"},
			},
		}
	}

	body, err := json.Marshal(req)
	if err != nil {
		return "", err
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", haikusBaseURL, bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("x-api-key", key)
	httpReq.Header.Set("anthropic-version", "2023-06-01")
	httpReq.Header.Set("anthropic-beta", "prompt-caching-2024-07-31")

	resp, err := haikusClient.Do(httpReq)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("haiku %d: %s", resp.StatusCode, truncate(string(raw), 200))
	}

	var hr haikusResponse
	if err := json.Unmarshal(raw, &hr); err != nil {
		return "", err
	}
	if hr.Error != nil {
		return "", fmt.Errorf("haiku error: %s", hr.Error.Message)
	}
	for _, block := range hr.Content {
		if block.Type == "text" && strings.TrimSpace(block.Text) != "" {
			return strings.TrimSpace(block.Text), nil
		}
	}
	return "", fmt.Errorf("haiku: empty response")
}

// ChatWithTimeout is Chat with an explicit deadline instead of the default 20s.
func ChatWithTimeout(timeout time.Duration, system, prompt string) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	return Chat(ctx, system, prompt)
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}
