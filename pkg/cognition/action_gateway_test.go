package cognition

import "testing"

func TestPlanSovereignActionRoutesExternalCustomerActionThroughApproval(t *testing.T) {
	plan := PlanSovereignAction(ActionGatewayPlanRequest{
		Surface: "studio",
		Intent:  "send a follow-up email to a new quote lead",
		ActionHints: []ActionGatewayActionHint{{
			Title:    "Send quote follow-up email",
			Tool:     "email",
			Inputs:   []string{"lead email", "draft body"},
			Effects:  []string{"customer email"},
			External: true,
		}},
		AvailableProviders: []ActionProvider{
			{ID: "native_email", Name: "Native Email", Kind: "native", Capabilities: []string{"email", "send"}, Scopes: []string{"email:send"}, Reliability: "high", Available: true},
			{ID: "zapier", Name: "Zapier MCP", Kind: "zapier_mcp", Capabilities: []string{"email", "crm"}, Scopes: []string{"zapier:actions"}, Reliability: "medium", Available: true},
		},
		ApprovalPolicy: ActionApprovalPolicy{
			RequireForExternalWrites: true,
			RequireForCustomerTouch:  true,
			ApprovalOwner:            "operator",
		},
		MemoryPolicy: ActionMemoryPolicy{MinimizeContext: true},
	})

	if plan.Surface != "studio" {
		t.Fatalf("expected studio surface, got %q", plan.Surface)
	}
	if len(plan.Candidates) == 0 {
		t.Fatalf("expected action candidates, got %+v", plan)
	}
	if plan.Recommended.ProviderID != "native_email" {
		t.Fatalf("expected native provider to win, got %+v", plan.Recommended)
	}
	if !plan.Recommended.ApprovalRequired || !plan.ApprovalGate.Required {
		t.Fatalf("expected approval for customer-facing external action, got %+v", plan)
	}
	if len(plan.PolicyLabels) == 0 || len(plan.DryRun.Steps) == 0 || len(plan.AuditPlan.Before) == 0 {
		t.Fatalf("expected policy, dry-run, and audit plans, got %+v", plan)
	}
}

func TestPlanSovereignActionBlocksCriticalDestructiveAction(t *testing.T) {
	plan := PlanSovereignAction(ActionGatewayPlanRequest{
		Surface: "dev",
		Intent:  "delete old customer records from the crm",
		ActionHints: []ActionGatewayActionHint{{
			Title:       "Delete old customer records",
			Tool:        "crm",
			Effects:     []string{"delete customer data"},
			Destructive: true,
			External:    true,
		}},
		AvailableProviders: []ActionProvider{
			{ID: "crm_native", Name: "CRM Native", Kind: "native", Capabilities: []string{"crm", "delete"}, Scopes: []string{"crm:write"}, Reliability: "high", Available: true},
		},
		ApprovalPolicy: ActionApprovalPolicy{RequireForDestructive: true},
	})

	if plan.Recommended.RiskTier != "critical" {
		t.Fatalf("expected critical risk, got %+v", plan.Recommended)
	}
	if !plan.Recommended.ApprovalRequired || !plan.ApprovalGate.Required {
		t.Fatalf("expected approval gate, got %+v", plan)
	}
	found := false
	for _, label := range plan.Recommended.PolicyLabels {
		if label == "blocked_until_review" {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected blocked_until_review label, got %+v", plan.Recommended.PolicyLabels)
	}
}
