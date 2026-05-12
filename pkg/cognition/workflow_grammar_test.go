package cognition

import "testing"

func TestCompileWorkflowGrammarBuildsTriggerActionGraph(t *testing.T) {
	plan := CompileWorkflowGrammar(WorkflowGrammarRequest{
		Surface:       "studio",
		Intent:        "turn inbound quote requests into reviewed follow-up drafts",
		Specification: "When a new quote email arrives then review the customer request then create a CRM task and then draft a follow-up email unless the request is missing budget or date.",
		AvailableTools: []WorkflowAvailableTool{
			{Name: "email", Kind: "inbox", Actions: []string{"email", "draft", "reply"}},
			{Name: "crm", Kind: "system", Actions: []string{"customer", "task"}},
		},
		Exceptions: []string{"missing budget or date"},
		Preferences: WorkflowGrammarPreferences{
			RequireHumanApprovals: true,
			DryRunFirst:           true,
		},
	})

	if plan.Surface != "studio" {
		t.Fatalf("expected studio surface, got %q", plan.Surface)
	}
	if plan.Trigger.Kind != "event" || plan.Trigger.Source != "inbox" {
		t.Fatalf("expected inbox event trigger, got %+v", plan.Trigger)
	}
	if len(plan.Nodes) < 3 {
		t.Fatalf("expected at least 3 workflow nodes, got %+v", plan.Nodes)
	}
	if len(plan.Edges) < 3 {
		t.Fatalf("expected trigger and sequential edges, got %+v", plan.Edges)
	}
	if len(plan.ApprovalGates) == 0 {
		t.Fatalf("expected approval gates for customer-facing workflow, got %+v", plan)
	}
	if plan.Readiness.Level == "" || plan.CompiledExpression == "" {
		t.Fatalf("expected readiness and compiled expression, got %+v", plan)
	}
}

func TestCompileWorkflowGrammarKeepsExternalWritesBehindApproval(t *testing.T) {
	plan := CompileWorkflowGrammar(WorkflowGrammarRequest{
		Surface: "dev",
		Title:   "release notes publisher",
		Trigger: "when a release tag is created",
		Actions: []WorkflowActionHint{
			{Title: "Summarize merged pull requests", Tool: "github"},
			{Title: "Publish release notes", Tool: "github", Destructive: false},
		},
		AvailableTools: []WorkflowAvailableTool{
			{Name: "github", Kind: "repo", Actions: []string{"pull requests", "release notes"}, RequiresOK: true},
		},
	})

	publish := WorkflowNode{}
	for _, node := range plan.Nodes {
		if node.Title == "Publish release notes" {
			publish = node
			break
		}
	}
	if publish.ID == "" {
		t.Fatalf("expected publish node, got %+v", plan.Nodes)
	}
	if publish.CanAutomate {
		t.Fatalf("expected publish node to require approval, got %+v", publish)
	}
	if len(plan.ApprovalGates) == 0 {
		t.Fatalf("expected approval gate for publish node, got %+v", plan)
	}
}
