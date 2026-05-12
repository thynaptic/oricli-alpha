package cognition

import "testing"

func TestPlanCodebaseResidentTaskBuildsScopedPackets(t *testing.T) {
	out := PlanCodebaseResidentTask(CodebaseTaskPlanRequest{
		Surface:     "dev",
		Intent:      "add a cognition endpoint",
		Repo:        "/home/mike/Mavaia",
		CurrentArea: "pkg/api",
		Files: []CodebaseFileSignal{
			{Path: "pkg/api/server_v2.go", Role: "api", CanModify: true},
			{Path: "pkg/api/example_handlers.go", Role: "handler", CanModify: true},
			{Path: "pkg/api/example_handlers_test.go", Role: "test", CanModify: true},
		},
		TestCommands: []string{"go test ./pkg/api"},
	})

	if out.Surface != "dev" {
		t.Fatalf("surface = %q", out.Surface)
	}
	if out.Scope.BlastRadius == "" || out.Scope.NeedsReadback {
		t.Fatalf("bad scope: %+v", out.Scope)
	}
	if len(out.WorkPackets) == 0 {
		t.Fatalf("expected work packets")
	}
	if len(out.Verification) != 1 || out.Verification[0].Command != "go test ./pkg/api" {
		t.Fatalf("verification = %+v", out.Verification)
	}
	if len(out.FileOwnership) != 3 {
		t.Fatalf("ownership = %+v", out.FileOwnership)
	}
}

func TestPlanCodebaseResidentTaskFlagsUnknownScope(t *testing.T) {
	out := PlanCodebaseResidentTask(CodebaseTaskPlanRequest{
		Intent: "fix auth bug",
	})

	if !out.Scope.NeedsReadback {
		t.Fatalf("expected readback need: %+v", out.Scope)
	}
	if len(out.Risks) == 0 {
		t.Fatalf("expected risks")
	}
	if len(out.OpenQuestions) == 0 {
		t.Fatalf("expected open questions")
	}
}
