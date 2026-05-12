package cognition

import (
	"strings"
	"testing"
	"time"
)

func TestTemporalClockSessionArcContinuityAndClaimGuard(t *testing.T) {
	clock := NewTemporalClock()
	const sessionID = "temporal-session"

	clock.RecordActivity(sessionID)
	clock.RecordEvent(sessionID, EventRoleUser, "Let's smoke test first, then deploy after verification.")
	clock.RecordEvent(sessionID, EventRoleAssistant, "Smoke test passed for the SCAI regeneration path.")

	prompt := clock.FormatForPrompt(sessionID, "what did we verify?")
	for _, want := range []string{
		"Current session arc:",
		"Tests:",
		"Pending temporal commitments:",
		"Continuity ledger:",
	} {
		if !strings.Contains(prompt, want) {
			t.Fatalf("prompt missing %q:\n%s", want, prompt)
		}
	}

	check := clock.VerifyTemporalClaim(sessionID, "we deployed the SCAI regeneration path")
	if check.OK {
		t.Fatalf("deployment claim unexpectedly passed before deployment evidence: %+v", check)
	}
	if !strings.Contains(check.Reason, "no deployment") {
		t.Fatalf("unexpected deployment rejection reason: %+v", check)
	}

	clock.RecordEvent(sessionID, EventRoleAssistant, "Deployed the SCAI regeneration path live after verification.")
	check = clock.VerifyTemporalClaim(sessionID, "we deployed the SCAI regeneration path")
	if !check.OK {
		t.Fatalf("deployment claim should pass after deployment evidence: %+v", check)
	}
}

func TestTemporalClockContradictionGuardDetectsBlockerAfterVerification(t *testing.T) {
	clock := NewTemporalClock()
	const sessionID = "temporal-blocker"

	clock.RecordActivity(sessionID)
	clock.RecordEvent(sessionID, EventRoleAssistant, "Smoke test passed for temporal clock.")
	clock.RecordEvent(sessionID, EventRoleAssistant, "Blocked by a compile error in temporal_clock.go.")

	check := clock.VerifyTemporalClaim(sessionID, "temporal clock was verified")
	if check.OK {
		t.Fatalf("verification claim unexpectedly passed after later blocker: %+v", check)
	}
	if !strings.Contains(check.Reason, "blocker") {
		t.Fatalf("unexpected blocker rejection reason: %+v", check)
	}
}

func TestJSONChronosStoreContinuity(t *testing.T) {
	store, err := NewJSONChronosStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}

	ledger := ContinuityLedger{
		UpdatedAt:      time.Now().UTC(),
		ActiveFocus:    "Temporal Clock upgrade",
		LastDeployment: "Deployed SCAI remold",
		LastSmoke:      "Smoke test passed",
		OpenLoops:      []string{"Restart/deploy after verification"},
		Commitments: []TemporalCommitment{{
			ID:        "tc_restart",
			CreatedAt: time.Now().UTC(),
			Trigger:   "after_verification",
			Summary:   "Restart/deploy after verification",
			Status:    CommitmentOpen,
		}},
		NextBestMove: "Run smoke test",
	}
	if err := store.SaveContinuity(ledger); err != nil {
		t.Fatal(err)
	}
	loaded, err := store.LoadContinuity()
	if err != nil {
		t.Fatal(err)
	}
	if loaded.ActiveFocus != ledger.ActiveFocus || len(loaded.Commitments) != 1 {
		t.Fatalf("loaded continuity mismatch: %+v", loaded)
	}

	if err := store.Save(ChronosSummary{
		SessionID:    "s1",
		StartedAt:    time.Now().UTC().Add(-time.Minute),
		EndedAt:      time.Now().UTC(),
		MessageCount: 2,
		TopicLine:    "Temporal Clock",
		Synopsis:     "Temporal Clock upgrade",
	}); err != nil {
		t.Fatal(err)
	}
	recent, err := store.LoadRecent(10)
	if err != nil {
		t.Fatal(err)
	}
	if len(recent) != 1 || recent[0].SessionID != "s1" {
		t.Fatalf("LoadRecent should ignore continuity ledger, got %+v", recent)
	}
}
