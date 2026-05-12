package cognition

import "testing"

func TestCoordinateTemporalWorkBuildsScheduleAndConflicts(t *testing.T) {
	out := CoordinateTemporalWork(TemporalCoordinateRequest{
		Surface: "studio",
		Horizon: "today",
		Energy:  "low",
		Available: []TemporalWindow{
			{Label: "morning focus", Minutes: 45, Energy: "medium"},
		},
		Tasks: []TemporalTask{
			{Title: "Send client launch update", Project: "launch", Minutes: 15, DueHint: "today", Importance: "high"},
			{Title: "Rewrite onboarding doc", Project: "ops", Minutes: 60},
			{Title: "Publish pricing page", Minutes: 30, Dependencies: []string{"approval"}},
		},
		Preferences: TemporalPreferences{ProtectFocus: true, PreferShortStarts: true},
	})

	if out.Surface != "studio" {
		t.Fatalf("surface = %q", out.Surface)
	}
	if len(out.Now) == 0 {
		t.Fatalf("expected now candidates, got %+v", out)
	}
	if len(out.Schedule) == 0 {
		t.Fatalf("expected schedule blocks, got %+v", out)
	}
	if len(out.Conflicts) == 0 {
		t.Fatalf("expected capacity/dependency conflicts, got %+v", out)
	}
	if len(out.MemorySeeds) == 0 {
		t.Fatalf("expected memory seeds")
	}
}

func TestCoordinateTemporalWorkKeepsBlockedTasksOutOfSchedule(t *testing.T) {
	out := CoordinateTemporalWork(TemporalCoordinateRequest{
		Available: []TemporalWindow{{Label: "focus", Minutes: 60}},
		Tasks: []TemporalTask{
			{ID: "blocked", Title: "Ship customer email", Minutes: 20, Dependencies: []string{"legal approval"}},
			{ID: "open", Title: "Draft customer email", Minutes: 20},
		},
	})

	for _, block := range out.Schedule {
		if block.TaskID == "blocked" {
			t.Fatalf("blocked task scheduled: %+v", out.Schedule)
		}
	}
	if len(out.Later) == 0 || !out.Later[0].Blocked {
		t.Fatalf("expected blocked task in later bucket, got %+v", out.Later)
	}
}
