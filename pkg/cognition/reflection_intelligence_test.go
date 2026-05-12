package cognition

import (
	"testing"
	"time"
)

func TestBuildReflectionPlanCreatesDialogicShape(t *testing.T) {
	plan := BuildReflectionPlan(ReflectionRequest{
		Entry: "I am overwhelmed by work and I never seem to catch up. My boss keeps moving deadlines and I feel stuck.",
		Goal:  "understand why this keeps happening",
		RecentMemories: []ReflectionMemory{{
			Summary:    "Work deadlines felt unstable last month.",
			Theme:      "work",
			OccurredAt: time.Now().Add(-7 * 24 * time.Hour),
			Importance: 0.8,
		}},
		Preferences: ReflectionPreferences{MaxPrompts: 3},
	})
	if plan.Signal.Mood != "heavy" {
		t.Fatalf("expected heavy mood, got %q", plan.Signal.Mood)
	}
	if plan.Signal.RiskTier != "medium" {
		t.Fatalf("expected medium support tier for intense overwhelm, got %q", plan.Signal.RiskTier)
	}
	if len(plan.Prompts) != 3 {
		t.Fatalf("expected capped prompts, got %d", len(plan.Prompts))
	}
	if len(plan.ContinuityHooks) == 0 {
		t.Fatal("expected continuity hook from matching work memory")
	}
	if len(plan.MemoryCandidates) == 0 || !plan.MemoryCandidates[0].RequiresConsent {
		t.Fatal("expected sensitive memory candidate requiring consent")
	}
}

func TestAnalyzeReflectionSignalHighRisk(t *testing.T) {
	signal := AnalyzeReflectionSignal("I want to kill myself and end it all.")
	if signal.RiskTier != "high" {
		t.Fatalf("expected high risk, got %q", signal.RiskTier)
	}
	prompts := BuildReflectionPrompts("entry", "", signal, nil, ReflectionPreferences{MaxPrompts: 3})
	if len(prompts) != 1 || prompts[0].Depth != "safety" {
		t.Fatalf("expected safety prompt, got %#v", prompts)
	}
}

func TestBuildReflectionReviewSortsPatterns(t *testing.T) {
	review := BuildReflectionReview(ReflectionReviewInput{
		TimeHorizon: "weekly",
		Entries: []string{
			"Work was intense and my boss changed a deadline.",
			"Family dinner felt good, but work kept pulling at me.",
			"I slept badly and felt tired at work.",
		},
	})
	if review.Title != "Weekly reflection packet" {
		t.Fatalf("unexpected title: %q", review.Title)
	}
	if len(review.Themes) == 0 || review.Themes[0] != "work" {
		t.Fatalf("expected work as top recurring theme, got %#v", review.Themes)
	}
	if len(review.FollowUps) == 0 {
		t.Fatal("expected follow-up prompts")
	}
}
