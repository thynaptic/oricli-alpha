package oracle

import (
	"os"
	"strings"
	"testing"
)

func TestCopilotArgs_Defaults(t *testing.T) {
	t.Cleanup(func() {
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_LIGHT")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_HEAVY")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_RESEARCH")
		_ = os.Unsetenv("ORACLE_COPILOT_REASONING_EFFORT")
	})
	_ = os.Unsetenv("ORACLE_COPILOT_MODEL")
	_ = os.Unsetenv("ORACLE_COPILOT_MODEL_LIGHT")
	_ = os.Unsetenv("ORACLE_COPILOT_MODEL_HEAVY")
	_ = os.Unsetenv("ORACLE_COPILOT_MODEL_RESEARCH")
	_ = os.Unsetenv("ORACLE_COPILOT_REASONING_EFFORT")

	args := copilotArgs("hello", RouteLightChat)
	if !containsSeq(args, "-p", "hello", "-s", "--agent", "ori-chat-fast", "--no-ask-user", "--model", defaultCopilotLightModel) {
		t.Fatalf("unexpected args: %s", strings.Join(args, " "))
	}
}

func TestCopilotArgs_CustomModelAndEffort(t *testing.T) {
	t.Cleanup(func() {
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_LIGHT")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_HEAVY")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_RESEARCH")
		_ = os.Unsetenv("ORACLE_COPILOT_REASONING_EFFORT")
	})
	t.Setenv("ORACLE_COPILOT_MODEL_HEAVY", "gpt-5.2")
	t.Setenv("ORACLE_COPILOT_REASONING_EFFORT", "medium")

	args := copilotArgs("x", RouteHeavyReasoning)
	if !containsSeq(args, "--agent", "ori-reasoner") {
		t.Fatalf("expected heavy agent in args, got %s", strings.Join(args, " "))
	}
	if !containsSeq(args, "--no-ask-user") {
		t.Fatalf("expected no-ask-user for heavy lane, got %s", strings.Join(args, " "))
	}
	if !containsSeq(args, "--model", "gpt-5.2", "--reasoning-effort", "medium") {
		t.Fatalf("expected custom model and effort in args, got %s", strings.Join(args, " "))
	}
	if !containsSeq(args, "--allow-tool=write") {
		t.Fatalf("expected heavy lane write permission, got %s", strings.Join(args, " "))
	}
	if !containsSeq(args, "--allow-tool=ori-runtime(get_key_info),ori-runtime(check_health),ori-runtime(get_capabilities),ori-runtime(list_surfaces),ori-runtime(list_working_styles),ori-runtime(get_request_template)") {
		t.Fatalf("expected heavy lane MCP allowlist, got %s", strings.Join(args, " "))
	}
}

func TestCopilotArgs_Gpt5MiniOmitsReasoningEffort(t *testing.T) {
	t.Cleanup(func() {
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_LIGHT")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_HEAVY")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_RESEARCH")
		_ = os.Unsetenv("ORACLE_COPILOT_REASONING_EFFORT")
	})
	t.Setenv("ORACLE_COPILOT_MODEL_LIGHT", "gpt-5-mini")
	t.Setenv("ORACLE_COPILOT_REASONING_EFFORT", "low")

	args := copilotArgs("q", RouteLightChat)
	if containsSeq(args, "--reasoning-effort") {
		t.Fatalf("gpt-5-mini must not get --reasoning-effort, got %s", strings.Join(args, " "))
	}
	if !containsSeq(args, "--model", "gpt-5-mini") {
		t.Fatalf("expected --model gpt-5-mini, got %s", strings.Join(args, " "))
	}
}

func TestCopilotArgs_DefaultOmitsReasoningEffortWhenEnvEffortSet(t *testing.T) {
	t.Cleanup(func() {
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_LIGHT")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_HEAVY")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_RESEARCH")
		_ = os.Unsetenv("ORACLE_COPILOT_REASONING_EFFORT")
	})
	_ = os.Unsetenv("ORACLE_COPILOT_MODEL")
	t.Setenv("ORACLE_COPILOT_REASONING_EFFORT", "low")

	args := copilotArgs("q", RouteLightChat)
	if containsSeq(args, "--reasoning-effort") {
		t.Fatalf("default gpt-5-mini must not get --reasoning-effort, got %s", strings.Join(args, " "))
	}
}

func TestDecide_ImageReasoningWins(t *testing.T) {
	decision := Decide("Can you analyze this screenshot for me?", RouteHints{})
	if decision.Route != RouteImageReasoning {
		t.Fatalf("expected image route, got %s", decision.Route)
	}
	if decision.Backend != "codex" {
		t.Fatalf("expected codex backend, got %s", decision.Backend)
	}
}

func TestDecide_ResearchRoute(t *testing.T) {
	decision := Decide("Please investigate the repo and summarize the findings", RouteHints{IsResearchAction: true})
	if decision.Route != RouteResearch {
		t.Fatalf("expected research route, got %s", decision.Route)
	}
}

func TestDecide_HeavyReasoningForCodeWork(t *testing.T) {
	decision := Decide("Debug this service crash and explain the root cause", RouteHints{IsCodeAction: true})
	if decision.Route != RouteHeavyReasoning {
		t.Fatalf("expected heavy reasoning route, got %s", decision.Route)
	}
}

func TestCopilotArgs_ResearchUsesResearchAgent(t *testing.T) {
	t.Cleanup(func() {
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_LIGHT")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_HEAVY")
		_ = os.Unsetenv("ORACLE_COPILOT_MODEL_RESEARCH")
	})
	args := copilotArgs("research this", RouteResearch)
	if !containsSeq(args, "--agent", "ori-research") {
		t.Fatalf("expected research agent, got %s", strings.Join(args, " "))
	}
	if !containsSeq(args, "--no-ask-user") {
		t.Fatalf("expected no-ask-user for research lane, got %s", strings.Join(args, " "))
	}
	if !containsSeq(args, "--model", defaultCopilotResearchModel) {
		t.Fatalf("expected research agent args, got %s", strings.Join(args, " "))
	}
	if !containsSeq(args, "--allow-tool=ori-runtime(get_key_info),ori-runtime(check_health),ori-runtime(get_capabilities),ori-runtime(list_surfaces),ori-runtime(list_working_styles),ori-runtime(get_request_template)") {
		t.Fatalf("expected research lane MCP allowlist, got %s", strings.Join(args, " "))
	}
}

func containsSeq(slice []string, parts ...string) bool {
outer:
	for i := 0; i <= len(slice)-len(parts); i++ {
		for j := range parts {
			if slice[i+j] != parts[j] {
				continue outer
			}
		}
		return true
	}
	return false
}
