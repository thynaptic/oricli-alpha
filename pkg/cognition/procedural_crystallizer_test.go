package cognition

import "testing"

func TestCrystallizeProcedurePromotesStablePattern(t *testing.T) {
	out := CrystallizeProcedure(ProceduralCrystallizeRequest{
		Surface:       "studio",
		Workflow:      "weekly client status prep",
		Objective:     "reduce repeated prep work",
		Trigger:       "before Friday client updates",
		Inputs:        []string{"latest tasks", "blockers", "wins"},
		Outputs:       []string{"status draft"},
		OutcomeSignal: "client-ready update exists",
		Runs: []WorkflowRunTrace{
			{Steps: []string{"collect tasks", "summarize blockers", "draft update"}, Outcome: "sent"},
			{Steps: []string{"collect tasks", "summarize blockers", "draft update"}, Outcome: "sent"},
			{Steps: []string{"collect tasks", "summarize blockers", "draft update"}, Outcome: "sent"},
		},
	})

	if out.Surface != "studio" {
		t.Fatalf("surface = %q", out.Surface)
	}
	if out.DetectedPattern.Readiness != "skill_candidate" {
		t.Fatalf("readiness = %+v", out.DetectedPattern)
	}
	if out.SkillCandidate.Name == "" || out.CandidateProcedure.Name == "" {
		t.Fatalf("missing candidates: %+v", out)
	}
}

func TestCrystallizeProcedureStaysObserveWhenSparse(t *testing.T) {
	out := CrystallizeProcedure(ProceduralCrystallizeRequest{Workflow: "ad hoc vendor review"})

	if out.DetectedPattern.Readiness == "skill_candidate" {
		t.Fatalf("unexpected promotion: %+v", out.DetectedPattern)
	}
	if len(out.OpenQuestions) == 0 {
		t.Fatalf("expected open questions")
	}
}
