package cognition

import "testing"

func TestOrchestrateExecutionChoosesStartableNextMove(t *testing.T) {
	out := OrchestrateExecution(ExecutionOrchestrateRequest{
		Surface:       "studio",
		Intent:        "continue launch work",
		Energy:        "medium",
		AvailableMins: 20,
		Tasks: []ExecutionTask{
			{ID: "blocked", Title: "Publish pricing page", Minutes: 30, Dependencies: []string{"approval"}},
			{ID: "open", Title: "Send client launch update", Importance: "high", Minutes: 15},
		},
		Blockers: []ExecutionBlocker{
			{Title: "approval", Owner: "Dana", Severity: "high"},
		},
		Preferences: ExecutionPreferences{PreferSmallStarts: true},
	})

	if out.Surface != "studio" {
		t.Fatalf("surface = %q", out.Surface)
	}
	if out.NextBest.ID != "open" {
		t.Fatalf("next best = %+v", out.NextBest)
	}
	if len(out.BlockedBecause) == 0 {
		t.Fatalf("expected blocker reasoning")
	}
	if out.Momentum.Level == "" {
		t.Fatalf("expected momentum")
	}
}

func TestOrchestrateExecutionHandlesEmptyTaskState(t *testing.T) {
	out := OrchestrateExecution(ExecutionOrchestrateRequest{
		Intent: "resume project",
	})

	if out.NextBest.Title == "" {
		t.Fatalf("expected fallback next move")
	}
	if len(out.Guardrails) == 0 {
		t.Fatalf("expected guardrails")
	}
}
