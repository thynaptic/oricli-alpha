package cognition

import "testing"

func TestRecoverContinuityBuildsRestartPoint(t *testing.T) {
	out := RecoverContinuity(ContinuityRecoverRequest{
		Surface:     "dev",
		Intent:      "resume cognition primitive work",
		Project:     "ORI primitives",
		Decisions:   []string{"ship app-neutral endpoints before product UI"},
		Commitments: []string{"restart services after two primitives"},
		OpenLoops:   []string{"decide next Pulse extraction"},
		PreviousSessions: []ContinuitySession{
			{ID: "s1", Title: "SaaS scan implementation", Summary: "Shipped anticipation and codebase task planner", Outcome: "decided to keep extracting primitives"},
		},
		Artifacts: []ContinuityArtifact{
			{ID: "a1", Title: "Pulse report", Kind: "research", Summary: "Continuity of cognition is the moat", Status: "active"},
		},
	})

	if out.Surface != "dev" {
		t.Fatalf("surface = %q", out.Surface)
	}
	if out.RecoveredThread.Title == "" || out.SuggestedContinuation.Title == "" {
		t.Fatalf("missing thread/continuation: %+v", out)
	}
	if len(out.ContextPackets) < 2 {
		t.Fatalf("expected context packets, got %+v", out.ContextPackets)
	}
	if len(out.DecisionLog) == 0 || len(out.OpenLoops) == 0 {
		t.Fatalf("expected decisions and open loops, got %+v", out)
	}
}

func TestRecoverContinuityHandlesThinContext(t *testing.T) {
	out := RecoverContinuity(ContinuityRecoverRequest{
		Intent: "resume work",
	})

	if len(out.OpenQuestions) == 0 {
		t.Fatalf("expected open questions")
	}
	if out.RecoveredThread.Confidence <= 0 {
		t.Fatalf("expected confidence")
	}
	if len(out.Guardrails) == 0 {
		t.Fatalf("expected guardrails")
	}
}
