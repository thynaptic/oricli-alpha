package cognition

import (
	"strings"
	"testing"
)

func TestBuildContextMomentumSystemRoutesContextIntoPackets(t *testing.T) {
	system := BuildContextMomentumSystem(ContextMomentumRequest{
		Surface:        "studio",
		CurrentProject: "homepage rewrite",
		UserState:      MomentumUserState{Energy: "low", Mood: "scattered"},
		Preferences:    MomentumPreferences{OverwhelmSensitive: true, PreserveNovelty: true},
		Items: []ContextMomentumItem{
			{Title: "Client quote for homepage rewrite", Kind: "note", ProjectHint: "homepage rewrite"},
			{Title: "Interesting positioning article", Kind: "link", Tags: []string{"positioning"}},
			{Title: "Old launch checklist completed", Status: "done"},
		},
	})

	if system.Surface != "studio" {
		t.Fatalf("expected studio surface, got %s", system.Surface)
	}
	if len(system.Actionability.ActiveProjects) == 0 {
		t.Fatalf("expected active project item, got %+v", system.Actionability)
	}
	if len(system.Packets) == 0 || system.NextFiveMinute.Title == "" || system.NextThirtyMinute.Title == "" {
		t.Fatalf("expected packets and next actions, got %+v", system)
	}
	if system.NextFiveMinute.Minutes > 5 {
		t.Fatalf("expected 5-minute packet, got %+v", system.NextFiveMinute)
	}
	if system.SteppingStone.Title == "" {
		t.Fatalf("expected stepping stone, got %+v", system.SteppingStone)
	}
	if !containsPlanningAny(strings.Join(system.Integration.MemoryTags, " "), "context_momentum") {
		t.Fatalf("expected context momentum memory tag, got %+v", system.Integration.MemoryTags)
	}
}

func TestBuildContextMomentumSystemEmptyPileAsksQuestion(t *testing.T) {
	system := BuildContextMomentumSystem(ContextMomentumRequest{
		Surface: "home",
	})
	if system.NextFiveMinute.Title == "" {
		t.Fatalf("expected starter packet, got %+v", system.NextFiveMinute)
	}
	if len(system.OpenQuestions) == 0 {
		t.Fatalf("expected open questions for empty pile, got %+v", system.OpenQuestions)
	}
}
