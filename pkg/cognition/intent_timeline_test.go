package cognition

import "testing"

func TestBuildIntentTimelineDetectsIntentShift(t *testing.T) {
	out := BuildIntentTimeline(IntentTimelineRequest{
		Surface:   "dev",
		Project:   "ORI primitives",
		Objective: "preserve rationale across code changes",
		Events: []IntentEvent{
			{Action: "read retention canvas", Intent: "extract calm software primitive", Rationale: "doc says retention comes from less bookkeeping", Evidence: []string{"research doc"}},
			{Action: "choose intent timeline first", Intent: "preserve why work changed", Rationale: "procedural crystallizer benefits from rationale trail", Outcome: "implementation order chosen", Evidence: []string{"handoff"}},
		},
		OpenLoops: []string{"document API contract"},
	})

	if out.Surface != "dev" {
		t.Fatalf("surface = %q", out.Surface)
	}
	if len(out.Moments) != 2 {
		t.Fatalf("moments = %+v", out.Moments)
	}
	if len(out.IntentShifts) == 0 {
		t.Fatalf("expected intent shift")
	}
	if out.CurrentIntent.Goal == "" || out.ContinuityPacket.ResumeLine == "" {
		t.Fatalf("missing current state: %+v", out)
	}
}

func TestBuildIntentTimelineClarifiesEmptyInput(t *testing.T) {
	out := BuildIntentTimeline(IntentTimelineRequest{})

	if len(out.Moments) != 1 {
		t.Fatalf("expected clarification moment, got %+v", out.Moments)
	}
	if len(out.OpenQuestions) == 0 {
		t.Fatalf("expected open questions")
	}
}
