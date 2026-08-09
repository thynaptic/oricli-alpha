package byok_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/thynaptic/ori-capsule/internal/byok"
)

func TestHasToolPayload(t *testing.T) {
	if byok.HasToolPayload(byok.ChatRequest{Messages: []byok.Message{{Role: "user", Content: "hi"}}}) {
		t.Fatal("expected false")
	}
	if !byok.HasToolPayload(byok.ChatRequest{
		Tools: []byok.ToolDefinition{{Type: "function", Function: byok.ToolFunction{Name: "x"}}},
	}) {
		t.Fatal("expected tools true")
	}
	if !byok.HasToolPayload(byok.ChatRequest{
		Messages: []byok.Message{{Role: "tool", Content: "{}", ToolCallID: "c1"}},
	}) {
		t.Fatal("expected tool role true")
	}
}

func TestMsgsToAnthropic_ToolRoundTrip(t *testing.T) {
	// Exercise through ChatNonStream against a fake Anthropic server.
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var body map[string]any
		_ = json.NewDecoder(r.Body).Decode(&body)
		tools, _ := body["tools"].([]any)
		if len(tools) != 1 {
			t.Errorf("tools=%v", body["tools"])
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{
			"id":"msg_1","model":"claude","stop_reason":"tool_use",
			"content":[
				{"type":"text","text":"Calling tool"},
				{"type":"tool_use","id":"tu_1","name":"tasks_list","input":{}}
			],
			"usage":{"input_tokens":1,"output_tokens":2}
		}`))
	}))
	defer srv.Close()

	out, err := byok.ChatNonStream(t.Context(), byok.Credentials{
		Provider: byok.ProviderAnthropic,
		APIKey:   "k",
		BaseURL:  srv.URL,
	}, byok.ChatRequest{
		Model: "claude",
		Messages: []byok.Message{
			{Role: "user", Content: "list tasks"},
		},
		Tools: []byok.ToolDefinition{{
			Type: "function",
			Function: byok.ToolFunction{
				Name:        "tasks_list",
				Description: "list",
				Parameters:  map[string]any{"type": "object"},
			},
		}},
		ToolChoice: "auto",
	})
	if err != nil {
		t.Fatal(err)
	}
	if out.Choices[0].FinishReason != "tool_calls" {
		t.Fatalf("finish=%q", out.Choices[0].FinishReason)
	}
	if len(out.Choices[0].Message.ToolCalls) != 1 || out.Choices[0].Message.ToolCalls[0].Function.Name != "tasks_list" {
		t.Fatalf("calls=%+v", out.Choices[0].Message.ToolCalls)
	}
	if !strings.Contains(out.Choices[0].Message.Content, "Calling") {
		t.Fatalf("content=%q", out.Choices[0].Message.Content)
	}
}

func TestCollectStream_OpenAIToolCalls(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		lines := []string{
			`data: {"id":"c1","model":"m","choices":[{"delta":{"role":"assistant"}}]}`,
			`data: {"id":"c1","model":"m","choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","type":"function","function":{"name":"tasks_list","arguments":""}}]}}]}`,
			`data: {"id":"c1","model":"m","choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{}"}}]}}]}`,
			`data: {"id":"c1","model":"m","choices":[{"delta":{},"finish_reason":"tool_calls"}]}`,
			`data: [DONE]`,
		}
		for _, line := range lines {
			_, _ = w.Write([]byte(line + "\n\n"))
		}
	}))
	defer srv.Close()

	res, err := byok.CollectStream(t.Context(), byok.Credentials{
		Provider: byok.ProviderOpenAI,
		APIKey:   "k",
		BaseURL:  srv.URL + "/v1",
	}, byok.ChatRequest{
		Model:    "m",
		Messages: []byok.Message{{Role: "user", Content: "hi"}},
		Tools: []byok.ToolDefinition{{
			Type:     "function",
			Function: byok.ToolFunction{Name: "tasks_list"},
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if res.FinishReason != "tool_calls" || len(res.ToolCalls) != 1 {
		t.Fatalf("%+v", res)
	}
	if res.ToolCalls[0].Function.Name != "tasks_list" || res.ToolCalls[0].Function.Arguments != "{}" {
		t.Fatalf("call=%+v", res.ToolCalls[0])
	}
}

func TestWriteChatSSEMessage_ToolCalls(t *testing.T) {
	var buf strings.Builder
	msg := byok.Message{
		Role:    "assistant",
		Content: "ok",
		ToolCalls: []byok.ToolCall{{
			ID:   "call_1",
			Type: "function",
			Function: byok.ToolFunctionCall{
				Name:      "tasks_list",
				Arguments: `{}`,
			},
		}},
	}
	if err := byok.WriteChatSSEMessage(&buf, "id", "m", msg, "tool_calls"); err != nil {
		t.Fatal(err)
	}
	raw := buf.String()
	if !strings.Contains(raw, "tool_calls") || !strings.Contains(raw, "tasks_list") {
		t.Fatalf("%s", raw)
	}
}
