package cognition

import "testing"

func TestCompileWorkGraphCreatesOperatorObjects(t *testing.T) {
	graph := CompileWorkGraph(WorkGraphCompileRequest{
		Surface:   "studio",
		Workspace: "Acme launch",
		Items: []WorkGraphInputItem{
			{Kind: "job", Title: "Acme launch project", Owner: "Mike", Status: "active"},
			{Title: "Approval needed for pricing page", Owner: "Dana", DueHint: "Friday"},
			{Title: "Follow up with client about testimonial", Owner: "Ari"},
			{Title: "Blocked waiting on export fix", Status: "blocked"},
		},
	})

	if graph.Surface != "studio" {
		t.Fatalf("surface = %q", graph.Surface)
	}
	if len(graph.Objects.Jobs) == 0 {
		t.Fatalf("expected jobs, got %+v", graph.Objects)
	}
	if len(graph.Objects.Approvals) == 0 {
		t.Fatalf("expected approvals, got %+v", graph.Objects)
	}
	if len(graph.Objects.FollowUps) == 0 {
		t.Fatalf("expected follow-ups, got %+v", graph.Objects)
	}
	if graph.Pulse.HandleFirst == "" || graph.Pulse.Health == "" {
		t.Fatalf("bad pulse: %+v", graph.Pulse)
	}
}

func TestAnswerWorkGraphQuestionFindsStuckWork(t *testing.T) {
	graph := CompileWorkGraph(WorkGraphCompileRequest{
		Items: []WorkGraphInputItem{
			{Title: "Blocked waiting on export fix", Status: "blocked"},
			{Title: "Follow up with client about testimonial"},
		},
	})

	answer := AnswerWorkGraphQuestion(WorkGraphAnswerRequest{
		Question: "What is stuck?",
		Graph:    graph,
	})

	if len(answer.Findings) == 0 {
		t.Fatalf("expected findings, got %+v", answer)
	}
	if len(answer.Recommended) == 0 {
		t.Fatalf("expected recommended moves")
	}
}
