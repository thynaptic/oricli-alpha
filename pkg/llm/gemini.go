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
	haikusModel   = "gpt-5.4-mini"
	sonnetModel   = "gpt-5.5"
	haikusBaseURL = "https://api.openai.com/v1/responses"
	haikusTimeout = 20 * time.Second
)

// Exported model name constants for callers that need to specify a model.
const (
	HaikuModel  = haikusModel
	SonnetModel = sonnetModel
)

var haikusClient = &http.Client{Timeout: haikusTimeout}

// Available reports whether an OpenAI API key is configured.
func Available() bool {
	return strings.TrimSpace(os.Getenv("OPENAI_API_KEY")) != ""
}

type haikusMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type haikusRequest struct {
	Model           string          `json:"model"`
	MaxOutputTokens int             `json:"max_output_tokens"`
	Reasoning       map[string]any  `json:"reasoning,omitempty"`
	Instructions    string          `json:"instructions,omitempty"`
	Input           []haikusMessage `json:"input"`
	Store           bool            `json:"store"`
}

type haikusResponse struct {
	OutputText string `json:"output_text"`
	Output     []struct {
		Type    string `json:"type"`
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content,omitempty"`
	} `json:"output"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

// Chat sends a prompt to the light OpenAI model.
// system may be empty. Falls back gracefully on any error — callers have heuristic fallbacks.
func Chat(ctx context.Context, system, prompt string) (string, error) {
	return ChatModel(ctx, haikusModel, system, prompt, 512)
}

// ChatModel is Chat with a configurable model and max_tokens.
// Use llm.HaikuModel or llm.SonnetModel as the model argument.
func ChatModel(ctx context.Context, model, system, prompt string, maxTokens int) (string, error) {
	key := strings.TrimSpace(os.Getenv("OPENAI_API_KEY"))
	if key == "" {
		return "", fmt.Errorf("OPENAI_API_KEY not set")
	}

	req := haikusRequest{
		Model:           model,
		MaxOutputTokens: maxTokens,
		Reasoning:       map[string]any{"effort": "low"},
		Instructions:    strings.TrimSpace(system),
		Input:           []haikusMessage{{Role: "user", Content: prompt}},
		Store:           false,
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
	httpReq.Header.Set("Authorization", "Bearer "+key)

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
		return "", fmt.Errorf("llm %s %d: %s", model, resp.StatusCode, truncate(string(raw), 200))
	}

	var hr haikusResponse
	if err := json.Unmarshal(raw, &hr); err != nil {
		return "", err
	}
	if hr.Error != nil {
		return "", fmt.Errorf("llm %s error: %s", model, hr.Error.Message)
	}
	if text := strings.TrimSpace(hr.OutputText); text != "" {
		return text, nil
	}
	for _, item := range hr.Output {
		if item.Type != "message" {
			continue
		}
		var sb strings.Builder
		for _, part := range item.Content {
			if part.Type == "output_text" || part.Type == "text" {
				sb.WriteString(part.Text)
			}
		}
		if text := strings.TrimSpace(sb.String()); text != "" {
			return text, nil
		}
	}
	return "", fmt.Errorf("llm %s: empty response", model)
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
