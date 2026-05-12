package cognition

import "testing"

func TestBuildContextualActionPlanCreatesEvidenceAndAction(t *testing.T) {
	out := BuildContextualActionPlan(ContextualActionRequest{
		Surface:   "studio",
		Objective: "decide best follow-up",
		Entity: ActionEntity{
			Name:   "Acme Co",
			Kind:   "account",
			Fields: map[string]string{"domain": "acme.test", "stage": "renewal"},
		},
		AvailableTools: []string{"crm_read", "web_search", "docs_read"},
		Evidence: []ActionEvidence{
			{Source: "crm", Type: "stage", Title: "Renewal open", Confidence: 0.7},
		},
		Signals: []ActionSignal{{Title: "Visited pricing page", Urgency: "high"}},
	})

	if out.Surface != "studio" {
		t.Fatalf("surface = %q", out.Surface)
	}
	if out.EntityProfile.Label != "Acme Co" {
		t.Fatalf("profile = %+v", out.EntityProfile)
	}
	if len(out.EvidencePlan) == 0 {
		t.Fatalf("expected evidence plan")
	}
	if len(out.Recommended) == 0 {
		t.Fatalf("expected recommendations")
	}
	if out.SkillFunction.Name == "" {
		t.Fatalf("expected skill function candidate")
	}
}

func TestBuildContextualActionPlanFlagsExternalActionBoundary(t *testing.T) {
	out := BuildContextualActionPlan(ContextualActionRequest{
		Objective: "send outreach email",
		Entity:    ActionEntity{Name: "Dana", Kind: "person"},
	})

	if len(out.Score.RiskFlags) == 0 {
		t.Fatalf("expected risk flags, got %+v", out.Score)
	}
	if len(out.OpenQuestions) == 0 {
		t.Fatalf("expected open questions")
	}
}
