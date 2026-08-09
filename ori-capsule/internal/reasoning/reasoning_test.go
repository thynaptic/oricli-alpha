package reasoning_test

import (
	"strings"
	"testing"

	"github.com/thynaptic/ori-capsule/internal/reasoning"
)

func TestPrecomputeArith(t *testing.T) {
	res := reasoning.Compute("what is 12345 + 67890?")
	if len(res) == 0 {
		t.Fatal("expected arithmetic result")
	}
	inj := reasoning.FormatPrecomputeInjection(res)
	if !strings.Contains(inj, "80235") {
		t.Fatalf("unexpected inject: %s", inj)
	}
}

func TestTrapDetect(t *testing.T) {
	hints := reasoning.Detect("A man and a goat need to cross a river in a boat. How?")
	if len(hints) == 0 {
		t.Fatal("expected trivial river crossing hint")
	}
}

func TestPrepareNoLLM(t *testing.T) {
	out := reasoning.Prepare([]reasoning.ChatMessage{
		{Role: "user", Content: "Explain step by step how distributed consensus algorithms work in detail"},
	}, "Explain step by step how distributed consensus algorithms work in detail")
	if out.SystemExtra == "" {
		t.Fatal("expected system extras")
	}
	if out.Meta["reasoning_hint"] == nil {
		t.Fatal("expected reasoning hint meta")
	}
	if !strings.Contains(out.SystemExtra, "RESPONSE PLAN") {
		t.Fatalf("missing response plan: %s", out.SystemExtra)
	}
}

func TestEpistemicFilter(t *testing.T) {
	ok := reasoning.EpistemicFilter("bm25 retrieval", "Local BM25 ranks documents by keyword relevance without embeddings for retrieval tasks.", "https://example.org/docs")
	if !ok.Pass {
		t.Fatalf("expected pass: %+v", ok)
	}
	bad := reasoning.EpistemicFilter("bm25", "hi", "http://localhost/x")
	if bad.Pass {
		t.Fatal("expected fail on localhost/short")
	}
}

func TestPlanningPlan(t *testing.T) {
	plan := reasoning.BuildPlanningPlan(reasoning.PlanningRequest{
		Goal: "Ship ori-capsule reasoning pack",
		Preferences: reasoning.PlanningPreferences{
			MaxVisibleSteps: 3, PreferredStepMins: 25, OverwhelmSensitive: true,
		},
	})
	if plan.Objective == "" || len(plan.Steps) == 0 {
		t.Fatalf("empty plan: %+v", plan)
	}
}

func TestReframeInject(t *testing.T) {
	inj := reasoning.CollectReframes("Obviously everyone knows that this is the only correct approach")
	if inj == "" {
		t.Fatal("expected pseudo-certainty reframe")
	}
}
