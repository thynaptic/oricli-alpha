package cognition

import (
	"strings"
	"testing"
	"time"
)

func TestBuildPlanningPlanLowOverwhelmShape(t *testing.T) {
	plan := BuildPlanningPlan(PlanningRequest{
		Goal:  "figure out launch prep",
		Notes: "write checklist. review deploy steps. smoke test public health. tell Mike what changed",
		Preferences: PlanningPreferences{
			MaxVisibleSteps:    4,
			PreferredStepMins:  20,
			OverwhelmSensitive: true,
		},
	})

	if plan.Objective == "" || plan.DefinitionOfDone == "" {
		t.Fatalf("expected objective and definition of done: %+v", plan)
	}
	if len(plan.Steps) == 0 || len(plan.Steps) > 4 {
		t.Fatalf("expected 1-4 visible steps, got %d: %+v", len(plan.Steps), plan.Steps)
	}
	if !strings.Contains(strings.ToLower(plan.NextAction), "clarify") {
		t.Fatalf("ambiguous goal should start with clarification, got %q", plan.NextAction)
	}
	if plan.Load.Tier == "" || plan.Load.Score <= 0 {
		t.Fatalf("expected cognitive load score, got %+v", plan.Load)
	}
}

func TestBuildTaskPatchSimplifiesPlan(t *testing.T) {
	patch := BuildTaskPatch(TaskPatchRequest{
		Instruction: "make this simpler and less overwhelming",
		CurrentSteps: []PlanningStep{
			{Title: "Write the whole launch plan", Minutes: 45, Energy: "high"},
			{Title: "Review deploy steps", Minutes: 30, Energy: "medium"},
			{Title: "Smoke test", Minutes: 20, Energy: "medium"},
			{Title: "Update docs", Minutes: 25, Energy: "medium"},
			{Title: "Prepare recap", Minutes: 15, Energy: "low"},
		},
	})

	if patch.Operation != "simplify" {
		t.Fatalf("expected simplify operation, got %+v", patch)
	}
	if len(patch.Steps) > 4 {
		t.Fatalf("expected capped visible steps, got %d", len(patch.Steps))
	}
	for _, step := range patch.Steps {
		if step.Minutes > 20 || step.Energy != "low" {
			t.Fatalf("step was not simplified: %+v", step)
		}
	}
}

func TestBuildFocusCueRescopesLongRunningStep(t *testing.T) {
	cue := BuildFocusCue([]PlanningStep{{Title: "Draft checklist", Minutes: 10}}, 0, 20*time.Minute)
	if !cue.Rescope {
		t.Fatalf("expected rescope cue, got %+v", cue)
	}
	if !strings.Contains(strings.ToLower(cue.Cue), "running long") {
		t.Fatalf("expected running-long cue, got %+v", cue)
	}
}

func TestBuildReviewPlanNoShameReschedule(t *testing.T) {
	review := BuildReviewPlan(ReviewInput{
		OpenLoops:     []string{"write notes", "review deploy", "clean up docs"},
		Blocked:       []string{"waiting on API key"},
		AvailableMins: 25,
		Preferences:   PlanningPreferences{PreferredStepMins: 15, MaxVisibleSteps: 2},
	})

	if review.NextBestMove == "" || len(review.Today) == 0 {
		t.Fatalf("expected actionable review: %+v", review)
	}
	if len(review.Reschedule) != 1 {
		t.Fatalf("expected blocked item to reschedule: %+v", review)
	}
	if !strings.Contains(strings.ToLower(review.ToneGuard), "no shame") {
		t.Fatalf("expected no-shame tone guard, got %q", review.ToneGuard)
	}
}
