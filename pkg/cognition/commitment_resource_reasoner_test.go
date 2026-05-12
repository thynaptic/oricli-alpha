package cognition

import "testing"

func TestReasonAboutCommitmentResourcesBuildsTradeoffs(t *testing.T) {
	out := ReasonAboutCommitmentResources(CommitmentResourceRequest{
		Surface:          "home",
		Context:          "household monthly plan",
		DecisionQuestion: "Can we do takeout tonight?",
		ProposedAction:   ResourceProposedAction{Title: "Takeout tonight", ResourceType: "money", Amount: 45},
		ResourcePools: []ResourcePool{
			{Type: "money", Label: "discretionary buffer", Amount: 80, Unit: "usd", Source: "user supplied", Confidence: 0.75},
		},
		Commitments: []ResourceCommitment{
			{Title: "rent", ResourceType: "money", Claim: 1200, Priority: "critical", Flexibility: "fixed"},
			{Title: "birthday gift plan", ResourceType: "money", Claim: 40, Priority: "medium", Flexibility: "movable"},
		},
	})

	if out.Surface != "home" {
		t.Fatalf("surface = %q", out.Surface)
	}
	if out.ResourceReality.Status == "" {
		t.Fatalf("expected reality status")
	}
	if len(out.ProtectedCommitments) == 0 {
		t.Fatalf("expected protected commitments")
	}
	if len(out.Options) == 0 || out.LeastDisruptive.Title == "" {
		t.Fatalf("expected tradeoff options: %+v", out)
	}
	if out.PermissionLanguage == "" {
		t.Fatalf("expected permission language")
	}
}

func TestReasonAboutCommitmentResourcesFramesDriftAsRecovery(t *testing.T) {
	out := ReasonAboutCommitmentResources(CommitmentResourceRequest{
		Surface:          "studio",
		Context:          "operator cashflow",
		DecisionQuestion: "Invoice slipped; can we approve the tool?",
		ProposedAction:   ResourceProposedAction{Title: "Approve tool", ResourceType: "money", Amount: 300},
		ResourcePools:    []ResourcePool{{Type: "money", Label: "cash buffer", Amount: 200, Unit: "usd", Source: "operator note"}},
		Commitments:      []ResourceCommitment{{Title: "payroll buffer", ResourceType: "money", Claim: 1000, Priority: "critical", Flexibility: "fixed"}},
		DriftEvent:       ResourceDriftEvent{Title: "invoice slipped", ResourceType: "money", Amount: 500},
	})

	if !out.Recovery.Needed {
		t.Fatalf("expected recovery plan")
	}
	if out.LeastDisruptive.Posture == "" {
		t.Fatalf("expected least disruptive posture")
	}
	if len(out.Guardrails) == 0 {
		t.Fatalf("expected guardrails")
	}
}
