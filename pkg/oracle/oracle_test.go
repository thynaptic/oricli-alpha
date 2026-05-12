package oracle

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestDecide_ImageReasoningWins(t *testing.T) {
	decision := Decide("Can you analyze this screenshot for me?", RouteHints{})
	if decision.Route != RouteImageReasoning {
		t.Fatalf("expected image route, got %s", decision.Route)
	}
	if decision.Backend != "openai" {
		t.Fatalf("expected openai backend, got %s", decision.Backend)
	}
}

func TestDecide_ResearchRoute(t *testing.T) {
	decision := Decide("Please investigate the repo and summarize the findings", RouteHints{IsResearchAction: true})
	if decision.Route != RouteResearch {
		t.Fatalf("expected research route, got %s", decision.Route)
	}
	if decision.Model == "" {
		t.Fatalf("expected model to be set for research route")
	}
}

func TestDecide_HeavyReasoningForCodeWork(t *testing.T) {
	decision := Decide("Debug this service crash and explain the root cause", RouteHints{IsCodeAction: true})
	if decision.Route != RouteHeavyReasoning {
		t.Fatalf("expected heavy reasoning route, got %s", decision.Route)
	}
}

func TestDecide_LightForConversational(t *testing.T) {
	for _, msg := range []string{"hey", "thanks", "ok sounds good"} {
		d := Decide(msg, RouteHints{})
		if d.Route != RouteLightChat {
			t.Fatalf("expected light route for %q, got %s", msg, d.Route)
		}
	}
}

func TestDecide_MiseSurfaceAlwaysLight(t *testing.T) {
	d := Decide("debug my entire codebase", RouteHints{Surface: "mise"})
	if d.Route != RouteLightChat {
		t.Fatalf("mise surface should always route light, got %s", d.Route)
	}
	if d.Agent != "mise-culinary" {
		t.Fatalf("expected mise-culinary agent, got %s", d.Agent)
	}
}

func TestModelForRoute_Defaults(t *testing.T) {
	if m := modelForRoute(RouteLightChat); m != defaultLightModel {
		t.Fatalf("expected default light model %s, got %s", defaultLightModel, m)
	}
	if m := modelForRoute(RouteHeavyReasoning); m != defaultHeavyModel {
		t.Fatalf("expected default heavy model %s, got %s", defaultHeavyModel, m)
	}
	if m := modelForRoute(RouteResearch); m != defaultResearchModel {
		t.Fatalf("expected default research model %s, got %s", defaultResearchModel, m)
	}
}

func TestAvailable_NoKey(t *testing.T) {
	t.Setenv("OPENAI_API_KEY", "")
	if Available() {
		t.Fatal("expected Available() false with no API key")
	}
}

func TestAvailable_WithKey(t *testing.T) {
	t.Setenv("OPENAI_API_KEY", "sk-test")
	if !Available() {
		t.Fatal("expected Available() true with API key set")
	}
}

func TestParseToolResponse_Text(t *testing.T) {
	raw := []byte(`{
		"output":[{"type":"message","content":[{"type":"output_text","text":"hello from responses"}]}]
	}`)
	round, err := parseToolResponse(raw)
	if err != nil {
		t.Fatalf("parseToolResponse returned error: %v", err)
	}
	if round.Text != "hello from responses" {
		t.Fatalf("unexpected text: %q", round.Text)
	}
	if len(round.Calls) != 0 {
		t.Fatalf("expected no calls, got %+v", round.Calls)
	}
}

func TestParseToolResponse_FunctionCall(t *testing.T) {
	raw := []byte(`{
		"output":[{
			"type":"function_call",
			"call_id":"call_123",
			"name":"read_file",
			"arguments":"{\"path\":\"docs/AGLI.md\"}"
		}]
	}`)
	round, err := parseToolResponse(raw)
	if err != nil {
		t.Fatalf("parseToolResponse returned error: %v", err)
	}
	if len(round.Calls) != 1 {
		t.Fatalf("expected one call, got %+v", round.Calls)
	}
	if round.Calls[0].ID != "call_123" || round.Calls[0].Name != "read_file" {
		t.Fatalf("unexpected call: %+v", round.Calls[0])
	}
	if round.Calls[0].Input["path"] != "docs/AGLI.md" {
		t.Fatalf("unexpected input: %+v", round.Calls[0].Input)
	}
}

func TestOpenAIResponseInputFromMessages_ToolLoop(t *testing.T) {
	var tc OAIToolCall
	tc.ID = "call_123"
	tc.Type = "function"
	tc.Function.Name = "read_file"
	tc.Function.Arguments = `{"path":"docs/AGLI.md"}`

	input, err := openAIResponseInputFromMessages([]Message{
		{Role: "system", Content: "ignored as instructions"},
		{Role: "user", Content: "read docs"},
		{Role: "assistant", ToolCalls: []OAIToolCall{tc}},
		{Role: "tool", ToolCallID: "call_123", Content: "doc text"},
	})
	if err != nil {
		t.Fatalf("openAIResponseInputFromMessages returned error: %v", err)
	}
	b, _ := json.Marshal(input)
	got := string(b)
	if !containsAll(got, `"type":"function_call"`, `"call_id":"call_123"`, `"type":"function_call_output"`, `"output":"doc text"`) {
		t.Fatalf("unexpected input conversion: %s", got)
	}
}

func containsAll(s string, needles ...string) bool {
	for _, needle := range needles {
		if !strings.Contains(s, needle) {
			return false
		}
	}
	return true
}
