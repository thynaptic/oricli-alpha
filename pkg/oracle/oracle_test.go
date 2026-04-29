package oracle

import (
	"testing"
)

func TestDecide_ImageReasoningWins(t *testing.T) {
	decision := Decide("Can you analyze this screenshot for me?", RouteHints{})
	if decision.Route != RouteImageReasoning {
		t.Fatalf("expected image route, got %s", decision.Route)
	}
	if decision.Backend != "anthropic" {
		t.Fatalf("expected anthropic backend, got %s", decision.Backend)
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
	t.Setenv("ANTHROPIC_API_KEY", "")
	if Available() {
		t.Fatal("expected Available() false with no API key")
	}
}

func TestAvailable_WithKey(t *testing.T) {
	t.Setenv("ANTHROPIC_API_KEY", "sk-ant-test")
	if !Available() {
		t.Fatal("expected Available() true with API key set")
	}
}
