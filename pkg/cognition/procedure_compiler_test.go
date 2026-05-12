package cognition

import "testing"

func TestCompileProcedureCreatesSkillCandidateAndSOP(t *testing.T) {
	proc := CompileProcedure(ProcedureCompileRequest{
		Surface:       "studio",
		Title:         "client onboarding follow-up",
		Actor:         "operator",
		Frequency:     "weekly",
		Inputs:        []string{"call notes", "account record"},
		Outputs:       []string{"follow-up email", "CRM next touch"},
		OutcomeSignal: "client has a clear next step",
		Observations: []ProcedureObservation{
			{Title: "Review call notes", Tool: "notes", Outcome: "Key decisions and objections are visible."},
			{Title: "Update CRM account state", Tool: "crm", Outcome: "Account state reflects the latest call."},
			{Title: "Draft follow-up email", Tool: "email", Outcome: "Draft is ready for approval."},
		},
	})

	if proc.Surface != "studio" {
		t.Fatalf("expected studio surface, got %s", proc.Surface)
	}
	if len(proc.Steps) != 3 {
		t.Fatalf("expected three steps, got %+v", proc.Steps)
	}
	if proc.SkillCandidate.Name == "" || len(proc.SkillCandidate.TriggerPhrases) == 0 {
		t.Fatalf("expected skill candidate, got %+v", proc.SkillCandidate)
	}
	if proc.SCLSeed.Tier != "skills" || proc.SCLSeed.Confidence <= 0.5 {
		t.Fatalf("expected SCL skill seed, got %+v", proc.SCLSeed)
	}
	if proc.AutomationCandidate.Readiness == "" {
		t.Fatalf("expected automation readiness, got %+v", proc.AutomationCandidate)
	}
	if len(proc.SOP.QualityBar) == 0 || proc.SOP.DoFirst == "" {
		t.Fatalf("expected SOP, got %+v", proc.SOP)
	}
}

func TestCompileProcedureKeepsRiskyStepsAssistive(t *testing.T) {
	proc := CompileProcedure(ProcedureCompileRequest{
		Title: "publish customer update",
		Observations: []ProcedureObservation{
			{Title: "Delete stale customer segment"},
			{Title: "Send update to all clients"},
		},
	})

	if proc.AutomationCandidate.Readiness != "assistive" {
		t.Fatalf("expected assistive readiness, got %+v", proc.AutomationCandidate)
	}
	if len(proc.AutomationCandidate.NeedsHuman) == 0 {
		t.Fatalf("expected human approval requirements, got %+v", proc.AutomationCandidate)
	}
}
