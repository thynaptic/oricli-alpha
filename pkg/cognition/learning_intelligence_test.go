package cognition

import (
	"testing"
	"time"
)

func TestBuildMaterialToMasteryCompilerProducesReportArtifacts(t *testing.T) {
	deadline := time.Now().UTC().Add(7 * 24 * time.Hour)
	system := BuildMaterialToMasteryCompiler(MaterialToMasteryRequest{
		Objective: "prepare for architecture review",
		Surface:   "dev",
		Deadline:  deadline,
		Sources: []LearningSource{{
			ID:      "src_repo_notes",
			Kind:    "docs",
			Title:   "Repo architecture notes",
			Content: "API gateway routes requests through Caddy and Go services. Session identity uses X-Session-ID. Missing session identity causes stateless behavior.",
		}},
		Preferences: LearningPreferences{
			SkillLevel:        "intermediate",
			ExplanationStyle:  "peer-language",
			SocraticByDefault: true,
		},
	})

	if len(system.ConceptGraph) == 0 {
		t.Fatalf("expected concept graph")
	}
	if len(system.Flashcards) == 0 || len(system.Quizzes) == 0 || len(system.MockAssessments) == 0 {
		t.Fatalf("expected generated study artifacts, got flashcards=%d quizzes=%d mocks=%d", len(system.Flashcards), len(system.Quizzes), len(system.MockAssessments))
	}
	if system.Assistance.Mode != "scaffold" {
		t.Fatalf("expected socratic scaffold mode, got %#v", system.Assistance)
	}
	if len(system.GoalDAG.Nodes) < 3 {
		t.Fatalf("expected learning goal DAG, got %#v", system.GoalDAG)
	}
	if len(system.ReviewCadence) == 0 {
		t.Fatalf("expected review cadence")
	}
	if system.Ledger.Concepts[system.ConceptGraph[0].ID] <= 0 {
		t.Fatalf("expected mastery ledger concept score, got %#v", system.Ledger)
	}
}

func TestChooseGuidedCompletionModeClarifiesWithoutSources(t *testing.T) {
	decision := ChooseGuidedCompletionMode(GuidedCompletionInput{})
	if decision.Mode != "clarify" {
		t.Fatalf("expected clarify mode without source context, got %#v", decision)
	}
}

func TestScoreMasteryLedgerFindsNextBottleneck(t *testing.T) {
	concepts := []ConceptNode{
		{ID: "a", Title: "A"},
		{ID: "b", Title: "B"},
	}
	score := ScoreMasteryLedger(MasteryLedger{Concepts: map[string]float64{"a": 0.8, "b": 0.2}}, concepts)
	if score.NextBottleneck != "b" {
		t.Fatalf("expected b as bottleneck, got %#v", score)
	}
	if score.Tier != "forming" {
		t.Fatalf("expected forming tier, got %#v", score)
	}
}
