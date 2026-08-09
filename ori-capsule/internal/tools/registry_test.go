package tools_test

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/thynaptic/ori-capsule/internal/byok"
	"github.com/thynaptic/ori-capsule/internal/tools"
)

func TestRegistry_ExecuteAllowlist(t *testing.T) {
	r := tools.NewRegistry()
	_ = r.Register(byok.ToolDefinition{
		Type: "function",
		Function: byok.ToolFunction{
			Name:       "echo_tool",
			Parameters: map[string]any{"type": "object"},
		},
	}, func(args map[string]any) (string, error) {
		b, _ := json.Marshal(args)
		return string(b), nil
	})
	out := r.Execute("echo_tool", `{"x":1}`)
	if !strings.Contains(out, `"x":1`) {
		t.Fatalf("out=%s", out)
	}
	unknown := r.Execute("nope", `{}`)
	if !strings.Contains(unknown, "unknown_tool") {
		t.Fatalf("unknown=%s", unknown)
	}
}

func TestRegistry_ExecuteCalls(t *testing.T) {
	r := tools.NewRegistry()
	_ = r.Register(byok.ToolDefinition{
		Type:     "function",
		Function: byok.ToolFunction{Name: "ping"},
	}, func(args map[string]any) (string, error) {
		return `{"pong":true}`, nil
	})
	msgs := r.ExecuteCalls([]byok.ToolCall{{
		ID:   "call_1",
		Type: "function",
		Function: byok.ToolFunctionCall{
			Name:      "ping",
			Arguments: `{}`,
		},
	}})
	if len(msgs) != 1 || msgs[0].Role != "tool" || msgs[0].ToolCallID != "call_1" {
		t.Fatalf("%+v", msgs)
	}
}
