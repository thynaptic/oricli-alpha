package cognition

import "testing"

func TestBuildSemanticMemoryGraphCreatesRecoverableTopology(t *testing.T) {
	out := BuildSemanticMemoryGraph(SemanticMemoryGraphRequest{
		Surface:   "home",
		Workspace: "family logistics",
		Objective: "recover school context without folders",
		Query:     "what school obligations are active?",
		Captures: []SemanticMemoryCapture{
			{ID: "flyer1", Title: "Field trip flyer", Kind: "document", Tags: []string{"school", "deadline"}, People: []string{"Mia"}, Objects: []string{"permission slip"}, Content: "Field trip needs signed permission slip by Friday."},
			{ID: "email1", Title: "Teacher email", Kind: "email", Tags: []string{"school"}, People: []string{"Mia"}, Objects: []string{"lunch form"}, Content: "Teacher asked parents to send lunch form."},
		},
	})

	if out.Surface != "home" {
		t.Fatalf("surface = %q", out.Surface)
	}
	if len(out.Nodes) == 0 || len(out.Clusters) == 0 {
		t.Fatalf("expected nodes and clusters: %+v", out)
	}
	if out.Recoverability.Score <= 0 {
		t.Fatalf("expected recoverability score")
	}
	if len(out.RetrievalPlan) == 0 {
		t.Fatalf("expected retrieval plan")
	}
}

func TestBuildSemanticMemoryGraphClarifiesEmptyInput(t *testing.T) {
	out := BuildSemanticMemoryGraph(SemanticMemoryGraphRequest{})

	if len(out.Nodes) != 1 {
		t.Fatalf("expected clarification node, got %+v", out.Nodes)
	}
	if len(out.OpenQuestions) == 0 {
		t.Fatalf("expected open questions")
	}
}
