package cognition

import (
	"strings"
	"testing"
)

func TestBuildBehaviorObjectCreatesSurfaceStateLoop(t *testing.T) {
	behavior := BuildBehaviorObject(BehaviorReinforcementRequest{
		Type:              BehaviorDaily,
		Title:             "walk for 20 minutes",
		Surface:           "home",
		Cadence:           "weekday_morning",
		ReinforcementMode: "calm_progress",
	})

	if behavior.ID == "" || !strings.HasPrefix(behavior.ID, "beh_") {
		t.Fatalf("expected stable behavior id, got %+v", behavior)
	}
	if behavior.FeedbackModel.StateLabel != "Household calm" {
		t.Fatalf("expected home state label, got %+v", behavior.FeedbackModel)
	}
	if !containsPlanningAny(strings.Join(behavior.FeedbackModel.Avoid, " "), "identity labels") {
		t.Fatalf("expected governance against identity labels, got %+v", behavior.FeedbackModel)
	}
	if len(behavior.Integration.Memory) == 0 || len(behavior.Integration.CALI) == 0 {
		t.Fatalf("expected integration hints, got %+v", behavior.Integration)
	}
}

func TestApplyBehaviorEventMissCreatesRecoveryNotPunishment(t *testing.T) {
	feedback := ApplyBehaviorEvent(BehaviorEventRequest{
		Behavior: BehaviorReinforcementRequest{
			Type:    BehaviorDaily,
			Title:   "walk for 20 minutes",
			Surface: "home",
		},
		Event: "missed",
		Context: BehaviorEventContext{
			Energy: "low",
			Notes:  "rainy morning",
		},
		PriorState: &BehaviorState{Streak: 4, StabilityScore: 0.72, CompletedCount: 4},
	})

	if feedback.State.Streak != 0 {
		t.Fatalf("miss should reset streak without punishment semantics, got %+v", feedback.State)
	}
	if len(feedback.Recovery) == 0 {
		t.Fatalf("expected recovery suggestions for miss, got %+v", feedback)
	}
	if !strings.Contains(strings.ToLower(feedback.SymbolicFeedback), "recovery") {
		t.Fatalf("expected recovery-oriented feedback, got %q", feedback.SymbolicFeedback)
	}
	if !strings.Contains(strings.ToLower(feedback.NextBestAction), "smallest recovery") {
		t.Fatalf("expected minimum viable next action, got %q", feedback.NextBestAction)
	}
}

func TestBuildBehaviorStateAggregatesEvents(t *testing.T) {
	state := BuildBehaviorState(BehaviorStateRequest{
		Behavior: BehaviorReinforcementRequest{
			Type:    BehaviorHabit,
			Title:   "write release notes",
			Surface: "dev",
		},
		Events: []BehaviorEventRequest{
			{Event: "completed"},
			{Event: "completed"},
			{Event: "deferred"},
		},
	})

	if state.CompletedCount != 2 || state.DeferredCount != 1 {
		t.Fatalf("expected aggregate counts, got %+v", state)
	}
	if state.StabilityScore <= 0 {
		t.Fatalf("expected stability score, got %+v", state)
	}
	if state.ReinforcementTier == "" || state.NextBestAction == "" {
		t.Fatalf("expected tier and next action, got %+v", state)
	}
}
