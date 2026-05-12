package cognition

import (
	"strings"
	"testing"
)

func TestBuildQuestScaffoldCreatesAdultGuidedEffortSystem(t *testing.T) {
	scaffold := BuildQuestScaffold(QuestScaffoldRequest{
		Goal:    "I need to study better for my board exam",
		Surface: "home",
		Preferences: PlanningPreferences{
			PreferredStepMins:  25,
			OverwhelmSensitive: true,
		},
	})

	if scaffold.ID == "" || !strings.HasPrefix(scaffold.ID, "quest_") {
		t.Fatalf("expected stable quest id, got %+v", scaffold)
	}
	if scaffold.Role.Label != "Practitioner" {
		t.Fatalf("expected practitioner role for study goal, got %+v", scaffold.Role)
	}
	if scaffold.FirstAction.Title == "" {
		t.Fatalf("expected first action: %+v", scaffold)
	}
	if len(scaffold.Milestones) != 3 {
		t.Fatalf("expected three milestones, got %d", len(scaffold.Milestones))
	}
	if scaffold.Rhythm.DailyMinutes > 20 {
		t.Fatalf("overwhelm-sensitive rhythm should stay small, got %+v", scaffold.Rhythm)
	}
	if !containsPlanningAny(strings.Join(scaffold.Progress.Avoid, " "), "badge spam") {
		t.Fatalf("expected governance against shallow gamification: %+v", scaffold.Progress)
	}
	if len(scaffold.Integration.Memory) == 0 || len(scaffold.Integration.Chronos) == 0 || len(scaffold.Integration.GoalDaemon) == 0 {
		t.Fatalf("expected ORI integration hints: %+v", scaffold.Integration)
	}
}

func TestBuildQuestScaffoldUsesSurfaceRoleForStudioOperator(t *testing.T) {
	scaffold := BuildQuestScaffold(QuestScaffoldRequest{
		Goal:    "get better at sales follow-up",
		Surface: "studio",
	})

	if scaffold.Role.Label != "Operator" {
		t.Fatalf("expected studio sales goal to become operator role, got %+v", scaffold.Role)
	}
	if !containsPlanningAny(strings.Join(scaffold.Workspace.Sections, " "), "pipeline") {
		t.Fatalf("expected business workspace sections, got %+v", scaffold.Workspace)
	}
}
