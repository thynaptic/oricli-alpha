package cognition

import "testing"

func TestDetectSignalOpportunitiesRanksTimelySignals(t *testing.T) {
	out := DetectSignalOpportunities(SignalOpportunityRequest{
		Surface:   "studio",
		Objective: "decide follow-up timing",
		Entity:    ActionEntity{Name: "Acme Co", Kind: "account"},
		Signals: []ActionSignal{
			{Title: "Visited pricing page", Type: "intent", Urgency: "high", Confidence: 0.74},
			{Title: "Opened old email", Type: "engagement", Urgency: "normal", Confidence: 0.52},
		},
		Context: []ActionEvidence{{Source: "crm", Title: "Renewal is open"}},
	})

	if out.Surface != "studio" {
		t.Fatalf("surface = %q", out.Surface)
	}
	if len(out.Opportunities) != 2 {
		t.Fatalf("opportunities = %+v", out.Opportunities)
	}
	if out.HandleFirst.Title != "Visited pricing page" {
		t.Fatalf("handle first = %+v", out.HandleFirst)
	}
	if len(out.Watchlist) == 0 {
		t.Fatalf("expected watchlist")
	}
}

func TestDetectSignalOpportunitiesHandlesThinSignals(t *testing.T) {
	out := DetectSignalOpportunities(SignalOpportunityRequest{
		Entity: ActionEntity{Name: "Unknown"},
	})

	if out.HandleFirst.Title == "" {
		t.Fatalf("expected fallback opportunity")
	}
	if len(out.OpenQuestions) == 0 {
		t.Fatalf("expected open questions")
	}
}
