package cognition

import "testing"

func TestPrepareAmbientAnticipationBuildsReadinessPrep(t *testing.T) {
	out := PrepareAmbientAnticipation(AnticipationPrepareRequest{
		Surface:      "studio",
		Situation:    "client renewal call",
		Intent:       "advance customer work",
		TimeHorizon:  "tomorrow",
		Participants: []string{"Dana"},
		Signals: []AnticipationSignal{
			{Source: "crm", Title: "Customer asked about pricing", Content: "They want the new annual plan before renewal.", Urgency: "medium"},
			{Source: "support", Title: "Open support issue", Content: "Waiting on export bug fix.", Urgency: "high"},
		},
		Preferences: []AnticipationPreference{
			{Subject: "Dana", Preference: "prefers concise options", Evidence: "prior calls ran better with two choices"},
		},
		RecentOutcomes: []string{"last call ended with export follow-up"},
	})

	if out.Surface != "studio" {
		t.Fatalf("surface = %q", out.Surface)
	}
	if out.Readiness.Level == "" || out.Readiness.Score <= 0 {
		t.Fatalf("bad readiness: %+v", out.Readiness)
	}
	if len(out.PrepPackets) < 2 {
		t.Fatalf("expected prep packets, got %+v", out.PrepPackets)
	}
	if out.SuggestedTone.Mode != "calm operator" {
		t.Fatalf("tone = %+v", out.SuggestedTone)
	}
	if len(out.SafeNextMoves) == 0 {
		t.Fatalf("expected safe next moves")
	}
}

func TestPrepareAmbientAnticipationNamesThinContext(t *testing.T) {
	out := PrepareAmbientAnticipation(AnticipationPrepareRequest{
		Situation: "quick check-in",
	})

	if out.Readiness.Level != "low" {
		t.Fatalf("expected low readiness, got %+v", out.Readiness)
	}
	if len(out.MissingContext) == 0 {
		t.Fatalf("expected missing context")
	}
	if len(out.Guardrails) == 0 {
		t.Fatalf("expected guardrails")
	}
}
