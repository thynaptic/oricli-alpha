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
	"time"
)

// BatchRequest is one item in a batch submission.
type BatchRequest struct {
	CustomID string   // caller-assigned ID to correlate results (e.g. jobID)
	Messages []Message
	Tools    []ToolDef
	Decision Decision
}

// BatchStatus mirrors Anthropic's batch processing status.
type BatchStatus string

const (
	BatchStatusInProgress BatchStatus = "in_progress"
	BatchStatusEnded      BatchStatus = "ended"
)

// Batch represents a submitted Anthropic message batch.
type Batch struct {
	ID                string      `json:"id"`
	Status            BatchStatus `json:"processing_status"`
	RequestCounts     BatchCounts `json:"request_counts"`
	CreatedAt         time.Time   `json:"created_at"`
	ResultsExpiresAt  time.Time   `json:"results_expires_at"`
}

type BatchCounts struct {
	Processing int `json:"processing"`
	Succeeded  int `json:"succeeded"`
	Errored    int `json:"errored"`
	Canceled   int `json:"canceled"`
	Expired    int `json:"expired"`
}

// BatchResult is one completed result from a batch.
type BatchResult struct {
	CustomID string     // matches the BatchRequest.CustomID
	Text     string     // populated on success
	Calls    []ToolCall // populated when model invoked tools
	Err      string     // populated on error
}

// SubmitBatch sends a batch of requests to the Anthropic batch API.
// Returns the batch ID immediately — results are retrieved later via PollBatch or FetchResults.
func SubmitBatch(ctx context.Context, requests []BatchRequest) (string, error) {
	if !Available() {
		return "", fmt.Errorf("batch: ANTHROPIC_API_KEY not configured")
	}
	if len(requests) == 0 {
		return "", fmt.Errorf("batch: no requests provided")
	}

	type batchItem struct {
		CustomID string         `json:"custom_id"`
		Params   map[string]any `json:"params"`
	}

	items := make([]batchItem, 0, len(requests))
	for _, r := range requests {
		params, err := buildBatchParams(r)
		if err != nil {
			return "", fmt.Errorf("batch: build params for %q: %w", r.CustomID, err)
		}
		items = append(items, batchItem{CustomID: r.CustomID, Params: params})
	}

	payload := map[string]any{"requests": items}
	body, err := json.Marshal(payload)
	if err != nil {
		return "", fmt.Errorf("batch: marshal payload: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		anthropicBase+"/messages/batches", bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("batch: build request: %w", err)
	}
	setAnthropicHeaders(req)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("batch: submit: %w", err)
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("batch: anthropic status %d: %s", resp.StatusCode, string(raw))
	}

	var b Batch
	if err := json.Unmarshal(raw, &b); err != nil {
		return "", fmt.Errorf("batch: decode response: %w", err)
	}

	log.Printf("[Oracle:Batch] submitted %d request(s) → batch %s", len(requests), b.ID)
	return b.ID, nil
}

// GetBatch fetches the current status of a batch without retrieving results.
func GetBatch(ctx context.Context, batchID string) (*Batch, error) {
	if !Available() {
		return nil, fmt.Errorf("batch: ANTHROPIC_API_KEY not configured")
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet,
		anthropicBase+"/messages/batches/"+batchID, nil)
	if err != nil {
		return nil, fmt.Errorf("batch: build request: %w", err)
	}
	setAnthropicHeaders(req)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("batch: get status: %w", err)
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("batch: anthropic status %d: %s", resp.StatusCode, string(raw))
	}

	var b Batch
	if err := json.Unmarshal(raw, &b); err != nil {
		return nil, fmt.Errorf("batch: decode status: %w", err)
	}
	return &b, nil
}

// FetchResults retrieves completed results for a batch.
// Only call this after GetBatch returns BatchStatusEnded.
// Results are returned as a map of CustomID → BatchResult.
func FetchResults(ctx context.Context, batchID string) (map[string]BatchResult, error) {
	if !Available() {
		return nil, fmt.Errorf("batch: ANTHROPIC_API_KEY not configured")
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet,
		anthropicBase+"/messages/batches/"+batchID+"/results", nil)
	if err != nil {
		return nil, fmt.Errorf("batch: build results request: %w", err)
	}
	setAnthropicHeaders(req)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("batch: fetch results: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		raw, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("batch: anthropic status %d: %s", resp.StatusCode, string(raw))
	}

	// Results arrive as JSONL — one JSON object per line.
	results := make(map[string]BatchResult)
	dec := json.NewDecoder(resp.Body)
	for dec.More() {
		var line struct {
			CustomID string `json:"custom_id"`
			Result   struct {
				Type    string `json:"type"` // "succeeded" | "errored" | "canceled" | "expired"
				Message struct {
					Content []struct {
						Type  string         `json:"type"`
						Text  string         `json:"text,omitempty"`
						ID    string         `json:"id,omitempty"`
						Name  string         `json:"name,omitempty"`
						Input map[string]any `json:"input,omitempty"`
					} `json:"content"`
					StopReason string `json:"stop_reason"`
				} `json:"message"`
				Error *struct {
					Type    string `json:"type"`
					Message string `json:"message"`
				} `json:"error"`
			} `json:"result"`
		}
		if err := dec.Decode(&line); err != nil {
			break
		}

		br := BatchResult{CustomID: line.CustomID}

		switch line.Result.Type {
		case "succeeded":
			if line.Result.Message.StopReason == "tool_use" {
				for _, block := range line.Result.Message.Content {
					if block.Type == "tool_use" {
						br.Calls = append(br.Calls, ToolCall{
							ID:    block.ID,
							Name:  block.Name,
							Input: block.Input,
						})
					}
				}
			} else {
				var sb strings.Builder
				for _, block := range line.Result.Message.Content {
					if block.Type == "text" {
						sb.WriteString(block.Text)
					}
				}
				br.Text = strings.TrimSpace(sb.String())
			}
		case "errored":
			if line.Result.Error != nil {
				br.Err = line.Result.Error.Message
			} else {
				br.Err = "unknown error"
			}
		case "canceled":
			br.Err = "canceled"
		case "expired":
			br.Err = "expired"
		}

		results[line.CustomID] = br
	}

	log.Printf("[Oracle:Batch] fetched %d result(s) for batch %s", len(results), batchID)
	return results, nil
}

// PollUntilDone polls a batch at the given interval until it ends or ctx is cancelled.
// Calls onDone with the final results when complete.
// Designed for use in a background goroutine — does not block the caller.
func PollUntilDone(ctx context.Context, batchID string, interval time.Duration, onDone func(map[string]BatchResult, error)) {
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				onDone(nil, ctx.Err())
				return
			case <-ticker.C:
				b, err := GetBatch(ctx, batchID)
				if err != nil {
					log.Printf("[Oracle:Batch] poll error for %s: %v", batchID, err)
					continue
				}
				log.Printf("[Oracle:Batch] %s — status=%s processing=%d succeeded=%d errored=%d",
					batchID, b.Status, b.RequestCounts.Processing,
					b.RequestCounts.Succeeded, b.RequestCounts.Errored)
				if b.Status == BatchStatusEnded {
					results, err := FetchResults(ctx, batchID)
					onDone(results, err)
					return
				}
			}
		}
	}()
}

// buildBatchParams constructs the Anthropic params object for one batch item.
func buildBatchParams(r BatchRequest) (map[string]any, error) {
	apiMsgs, err := convertMessagesForTools(r.Messages)
	if err != nil {
		return nil, err
	}

	outputTokens := maxTokens
	params := map[string]any{
		"model":    r.Decision.Model,
		"messages": apiMsgs,
	}

	// System prompt with cache_control.
	systemPrompt := ""
	for _, m := range r.Messages {
		if m.Role == "system" {
			systemPrompt = m.Content
			break
		}
	}
	if systemPrompt == "" {
		systemPrompt = getAgentPrompt(r.Decision.Agent)
	}
	if systemPrompt != "" {
		params["system"] = []map[string]any{{
			"type":          "text",
			"text":          systemPrompt,
			"cache_control": map[string]any{"type": "ephemeral"},
		}}
	}

	if len(r.Tools) > 0 {
		params["tools"] = r.Tools
	}

	params["max_tokens"] = outputTokens
	return params, nil
}

// setAnthropicHeaders applies auth and version headers to a request.
func setAnthropicHeaders(req *http.Request) {
	req.Header.Set("content-type", "application/json")
	req.Header.Set("x-api-key", os.Getenv("ANTHROPIC_API_KEY"))
	req.Header.Set("anthropic-version", anthropicVersion)
	req.Header.Set("anthropic-beta", "message-batches-2024-09-24,prompt-caching-2024-07-31")
}
