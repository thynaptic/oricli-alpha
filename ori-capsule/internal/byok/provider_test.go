package byok_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/thynaptic/ori-capsule/internal/byok"
)

func TestParseProvider(t *testing.T) {
	cases := map[string]byok.Provider{
		"openai":    byok.ProviderOpenAI,
		"OpenAI":    byok.ProviderOpenAI,
		"anthropic": byok.ProviderAnthropic,
		"opencode":  byok.ProviderOpenCode,
		"":          byok.ProviderOpenAI,
	}
	for in, want := range cases {
		got, err := byok.ParseProvider(in)
		if err != nil {
			t.Fatalf("ParseProvider(%q): %v", in, err)
		}
		if got != want {
			t.Fatalf("ParseProvider(%q)=%q want %q", in, got, want)
		}
	}
	if _, err := byok.ParseProvider("nope"); err == nil {
		t.Fatal("expected error for unknown provider")
	}
}

func TestWriteChatSSE_FormatAndContent(t *testing.T) {
	var buf strings.Builder
	content := "Hello 世界 streaming"
	if err := byok.WriteChatSSE(&buf, "chatcmpl-test", "gpt-test", content, "stop"); err != nil {
		t.Fatal(err)
	}
	raw := buf.String()
	if !strings.Contains(raw, "data: [DONE]") {
		t.Fatalf("missing DONE:\n%s", raw)
	}
	var assembled strings.Builder
	sawRole := false
	sawFinish := false
	for _, line := range strings.Split(raw, "\n") {
		if !strings.HasPrefix(line, "data: ") {
			continue
		}
		payload := strings.TrimPrefix(line, "data: ")
		if payload == "[DONE]" {
			continue
		}
		var chunk struct {
			Choices []struct {
				Delta struct {
					Role    string `json:"role"`
					Content string `json:"content"`
				} `json:"delta"`
				FinishReason *string `json:"finish_reason"`
			} `json:"choices"`
		}
		if err := json.Unmarshal([]byte(payload), &chunk); err != nil {
			t.Fatalf("bad chunk %q: %v", payload, err)
		}
		if len(chunk.Choices) == 0 {
			t.Fatal("empty choices")
		}
		if chunk.Choices[0].Delta.Role == "assistant" {
			sawRole = true
		}
		assembled.WriteString(chunk.Choices[0].Delta.Content)
		if chunk.Choices[0].FinishReason != nil && *chunk.Choices[0].FinishReason == "stop" {
			sawFinish = true
		}
	}
	if !sawRole {
		t.Fatal("missing role chunk")
	}
	if !sawFinish {
		t.Fatal("missing finish_reason stop")
	}
	if assembled.String() != content {
		t.Fatalf("assembled %q want %q", assembled.String(), content)
	}
}

func TestCollectStream_OpenAICompat(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		flushes := []string{
			`data: {"id":"chatcmpl-up","model":"m1","choices":[{"delta":{"role":"assistant"}}]}`,
			`data: {"id":"chatcmpl-up","model":"m1","choices":[{"delta":{"content":"Safe "}}]}`,
			`data: {"id":"chatcmpl-up","model":"m1","choices":[{"delta":{"content":"answer"}}]}`,
			`data: {"id":"chatcmpl-up","model":"m1","choices":[{"delta":{},"finish_reason":"stop"}]}`,
			`data: [DONE]`,
		}
		for _, line := range flushes {
			_, _ = w.Write([]byte(line + "\n\n"))
			if f, ok := w.(http.Flusher); ok {
				f.Flush()
			}
		}
	}))
	defer srv.Close()

	res, err := byok.CollectStream(t.Context(), byok.Credentials{
		Provider: byok.ProviderOpenAI,
		APIKey:   "sk-test",
		BaseURL:  srv.URL + "/v1",
	}, byok.ChatRequest{
		Model:    "m1",
		Messages: []byok.Message{{Role: "user", Content: "hi"}},
		Stream:   true,
	})
	if err != nil {
		t.Fatal(err)
	}
	if res.Content != "Safe answer" {
		t.Fatalf("content=%q", res.Content)
	}
	if res.ID != "chatcmpl-up" {
		t.Fatalf("id=%q", res.ID)
	}
	if res.FinishReason != "stop" {
		t.Fatalf("finish=%q", res.FinishReason)
	}
}
