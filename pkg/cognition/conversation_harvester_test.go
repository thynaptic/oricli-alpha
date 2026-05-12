package cognition

import "testing"

func TestHarvestConversationContextExtractsDecisionsCommitmentsAndThreads(t *testing.T) {
	out := HarvestConversationContext(ConversationHarvestRequest{
		Surface:      "studio",
		Title:        "client launch sync",
		Intent:       "coordinate launch work",
		Participants: []string{"Mike", "Ari"},
		Messages: []ConversationMessage{
			{Speaker: "Mike", Text: "We decided the landing page ships Friday."},
			{Speaker: "Ari", Text: "I'll send the pricing notes tomorrow."},
			{Speaker: "Mike", Text: "Are we still waiting on the testimonial approval?"},
		},
	})

	if out.Surface != "studio" {
		t.Fatalf("surface = %q", out.Surface)
	}
	if len(out.Decisions) != 1 {
		t.Fatalf("decisions len = %d", len(out.Decisions))
	}
	if len(out.Commitments) != 1 {
		t.Fatalf("commitments len = %d", len(out.Commitments))
	}
	if out.Commitments[0].Owner != "Ari" {
		t.Fatalf("commitment owner = %q", out.Commitments[0].Owner)
	}
	if out.Commitments[0].DueHint != "tomorrow" {
		t.Fatalf("due hint = %q", out.Commitments[0].DueHint)
	}
	if len(out.Unresolved) != 1 {
		t.Fatalf("unresolved len = %d", len(out.Unresolved))
	}
	if len(out.FollowUps) != 2 {
		t.Fatalf("follow ups len = %d", len(out.FollowUps))
	}
	if len(out.MemorySeeds) < 3 {
		t.Fatalf("expected useful memory seeds, got %#v", out.MemorySeeds)
	}
}

func TestHarvestConversationContextDoesNotInventWrites(t *testing.T) {
	out := HarvestConversationContext(ConversationHarvestRequest{
		Transcript: "Great call. We should maybe review the support flow later.",
	})

	if len(out.Guardrails) == 0 {
		t.Fatal("expected persistence guardrails")
	}
	if len(out.OpenQuestions) == 0 {
		t.Fatal("expected open questions for ambiguous conversation")
	}
	if out.Signals.Intent == "" {
		t.Fatal("expected inferred intent")
	}
}
