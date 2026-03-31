package cli

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// Client is a thin HTTP client targeting the Oricli backbone API.
type Client struct {
	cfg    *Config
	http   *http.Client
}

// NewClient creates a Client from config.
func NewClient(cfg *Config) *Client {
	return &Client{
		cfg:  cfg,
		http: &http.Client{Timeout: 120 * time.Second},
	}
}

// SetTarget overrides the API target mid-session.
func (c *Client) SetTarget(target string) {
	c.cfg.Target = target
}

func (c *Client) url(path string) string {
	return strings.TrimRight(c.cfg.Target, "/") + path
}

func (c *Client) auth(req *http.Request) {
	if c.cfg.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.cfg.APIKey)
	}
}

// get performs an authenticated GET and decodes JSON into dst.
func (c *Client) get(path string, dst interface{}) error {
	req, err := http.NewRequest("GET", c.url(path), nil)
	if err != nil {
		return err
	}
	c.auth(req)
	req.Header.Set("Accept", "application/json")
	resp, err := c.http.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}
	return json.NewDecoder(resp.Body).Decode(dst)
}

// post sends JSON and decodes response.
func (c *Client) post(path string, payload, dst interface{}) error {
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	req, err := http.NewRequest("POST", c.url(path), bytes.NewReader(body))
	if err != nil {
		return err
	}
	c.auth(req)
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.http.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(b))
	}
	if dst != nil {
		return json.NewDecoder(resp.Body).Decode(dst)
	}
	return nil
}

// ── Endpoint wrappers ─────────────────────────────────────────────────────────

func (c *Client) GetHealth() (map[string]interface{}, error) {
	var out map[string]interface{}
	return out, c.get("/v1/health", &out)
}

func (c *Client) GetModels() (map[string]interface{}, error) {
	var out map[string]interface{}
	return out, c.get("/v1/curator/models", &out)
}

func (c *Client) GetModules() (map[string]interface{}, error) {
	var out map[string]interface{}
	return out, c.get("/v1/modules", &out)
}

func (c *Client) GetMetrics() (map[string]interface{}, error) {
	var out map[string]interface{}
	return out, c.get("/v1/metrics", &out)
}

func (c *Client) GetTherapyStats() (map[string]interface{}, error) {
	var out map[string]interface{}
	return out, c.get("/v1/therapy/stats", &out)
}

func (c *Client) GetFormulation() (map[string]interface{}, error) {
	var out map[string]interface{}
	return out, c.get("/v1/therapy/formulation", &out)
}

func (c *Client) GetMastery() (map[string]interface{}, error) {
	var out map[string]interface{}
	return out, c.get("/v1/therapy/mastery", &out)
}

func (c *Client) GetGoals() (map[string]interface{}, error) {
	var out map[string]interface{}
	return out, c.get("/v1/goals", &out)
}

func (c *Client) PostGoal(description string) (map[string]interface{}, error) {
	var out map[string]interface{}
	return out, c.post("/v1/goals", map[string]string{"description": description}, &out)
}

// ── Streaming chat ────────────────────────────────────────────────────────────

// StreamToken is a single token chunk from SSE.
type StreamToken struct {
	Content string
	Done    bool
	Error   error
}

// StreamChat sends a chat request and streams tokens into the returned channel.
// The channel is closed when the stream ends or errors.
func (c *Client) StreamChat(messages []map[string]string, model string) (<-chan StreamToken, error) {
	payload := map[string]interface{}{
		"model":    model,
		"messages": messages,
		"stream":   true,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequest("POST", c.url("/v1/chat/completions"), bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	c.auth(req)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "text/event-stream")

	// Use a client without timeout for streaming
	streamHTTP := &http.Client{}
	resp, err := streamHTTP.Do(req)
	if err != nil {
		return nil, fmt.Errorf("stream request failed: %w", err)
	}
	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(b))
	}

	ch := make(chan StreamToken, 64)
	go parseSSE(resp.Body, ch)
	return ch, nil
}

// BlockingChat sends a non-streaming chat and returns the full response text.
func (c *Client) BlockingChat(messages []map[string]string, model string) (string, error) {
	var out map[string]interface{}
	err := c.post("/v1/chat/completions", map[string]interface{}{
		"model":    model,
		"messages": messages,
		"stream":   false,
	}, &out)
	if err != nil {
		return "", err
	}
	// OpenAI-compatible response
	if choices, ok := out["choices"].([]interface{}); ok && len(choices) > 0 {
		if choice, ok := choices[0].(map[string]interface{}); ok {
			if msg, ok := choice["message"].(map[string]interface{}); ok {
				if content, ok := msg["content"].(string); ok {
					return content, nil
				}
			}
		}
	}
	// Fallback: direct text field
	if text, ok := out["text"].(string); ok {
		return text, nil
	}
	return fmt.Sprintf("%v", out), nil
}

// parseSSE reads an SSE stream and sends tokens to ch.
func parseSSE(body io.ReadCloser, ch chan<- StreamToken) {
	defer body.Close()
	defer close(ch)

	scanner := bufio.NewScanner(body)
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, "data: ") {
			continue
		}
		data := strings.TrimPrefix(line, "data: ")
		if data == "[DONE]" {
			ch <- StreamToken{Done: true}
			return
		}
		var chunk map[string]interface{}
		if err := json.Unmarshal([]byte(data), &chunk); err != nil {
			continue
		}
		// Extract token from OpenAI-compatible delta
		if choices, ok := chunk["choices"].([]interface{}); ok && len(choices) > 0 {
			if choice, ok := choices[0].(map[string]interface{}); ok {
				if delta, ok := choice["delta"].(map[string]interface{}); ok {
					if content, ok := delta["content"].(string); ok && content != "" {
						ch <- StreamToken{Content: content}
					}
				}
				// Check finish_reason
				if reason, ok := choice["finish_reason"].(string); ok && reason == "stop" {
					ch <- StreamToken{Done: true}
					return
				}
			}
		}
	}
	if err := scanner.Err(); err != nil {
		ch <- StreamToken{Error: err}
	}
}

// GetComputeBidStats fetches compute bidding statistics from the server.
func (c *Client) GetComputeBidStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/compute/bids/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetComputeGovernor fetches recent BidGovernor decisions from the server.
func (c *Client) GetComputeGovernor(n int) (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get(fmt.Sprintf("/v1/compute/governor?n=%d", n), &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetProcessStats fetches dual process mismatch stats from the server.
func (c *Client) GetProcessStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/process/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetCogLoadStats fetches cognitive load stats from the server.
func (c *Client) GetCogLoadStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/load/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetRuminationStats fetches rumination detector stats from the server.
func (c *Client) GetRuminationStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/rumination/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetMindsetStats fetches growth mindset stats from the server.
func (c *Client) GetMindsetStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/mindset/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetMindsetVectors fetches per-topic mindset vectors from the server.
func (c *Client) GetMindsetVectors() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/mindset/vectors", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetHopeStats fetches Hope Circuit (P21) stats from the server.
func (c *Client) GetHopeStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/hope/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetDefeatStats fetches Social Defeat (P22) stats from the server.
func (c *Client) GetDefeatStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/defeat/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetConformityStats returns Phase 23 agency shield statistics.
func (c *Client) GetConformityStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/conformity/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetIdeoCaptureStats returns Phase 24 ideological capture stats.
func (c *Client) GetIdeoCaptureStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/ideocapture/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetCoalitionStats returns Phase 25 coalition bias stats.
func (c *Client) GetCoalitionStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/coalition/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetStatusBiasStats returns Phase 26 status bias stats.
func (c *Client) GetStatusBiasStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/statusbias/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetArousalStats returns Phase 27 arousal optimizer stats.
func (c *Client) GetArousalStats() (map[string]interface{}, error) {
var result map[string]interface{}
if err := c.get("/v1/cognition/arousal/stats", &result); err != nil {
return nil, err
}
return result, nil
}

// GetInterferenceStats returns Phase 28 cognitive interference stats.
func (c *Client) GetInterferenceStats() (map[string]interface{}, error) {
var result map[string]interface{}
if err := c.get("/v1/cognition/interference/stats", &result); err != nil {
return nil, err
}
return result, nil
}

// GetMCTStats returns Phase 29 metacognitive therapy stats.
func (c *Client) GetMCTStats() (map[string]interface{}, error) {
var result map[string]interface{}
if err := c.get("/v1/cognition/mct/stats", &result); err != nil {
return nil, err
}
return result, nil
}

// GetMBTStats returns Phase 30 MBT stats.
func (c *Client) GetMBTStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/mbt/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetSchemaStats returns Phase 31 schema therapy stats.
func (c *Client) GetSchemaStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/schema/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetIPSRTStats returns Phase 32 IPSRT social rhythm stats.
func (c *Client) GetIPSRTStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/ipsrt/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetILMStats returns Phase 33 ILM safety behavior stats.
func (c *Client) GetILMStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/ilm/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetIUTStats returns Phase 34 IUT uncertainty intolerance stats.
func (c *Client) GetIUTStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/iut/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetUPStats returns Phase 35 Unified Protocol ARC cycle stats.
func (c *Client) GetUPStats() (map[string]interface{}, error) {
	var result map[string]interface{}
	if err := c.get("/v1/cognition/up/stats", &result); err != nil {
		return nil, err
	}
	return result, nil
}

// GetCBASPStats returns Phase 36 CBASP interpersonal disconnection stats.
func (c *Client) GetCBASPStats() (map[string]interface{}, error) {
var result map[string]interface{}
if err := c.get("/v1/cognition/cbasp/stats", &result); err != nil {
return nil, err
}
return result, nil
}

// GetMBCTStats returns Phase 37 MBCT decentering stats.
func (c *Client) GetMBCTStats() (map[string]interface{}, error) {
var result map[string]interface{}
if err := c.get("/v1/cognition/mbct/stats", &result); err != nil {
return nil, err
}
return result, nil
}

// GetPhaseOrientedStats returns Phase 38 Phase-Oriented Treatment stats.
func (c *Client) GetPhaseOrientedStats() (map[string]interface{}, error) {
var result map[string]interface{}
if err := c.get("/v1/cognition/phaseoriented/stats", &result); err != nil {
return nil, err
}
return result, nil
}
