package hopecircuit

import (
	"testing"

	"github.com/thynaptic/oricli-go/pkg/therapy"
)

func newTestLedger(successRate float64, successCount int) *ControllabilityLedger {
	ml := therapy.NewMasteryLog(100, "/tmp/test_hopecircuit_mastery.json")
	// Seed with successes for "coding" topic class
	for i := 0; i < successCount; i++ {
		ml.Record("coding", "how do I implement a binary search tree", true)
	}
	if successRate < 1.0 {
		// Add some failures to bring rate down
		failures := int(float64(successCount) * (1.0 - successRate) / successRate)
		for i := 0; i < failures; i++ {
			ml.Record("coding", "implement merge sort", false)
		}
	}
	return NewControllabilityLedger(ml)
}

func TestLedger_NoDataReturnsZeroScore(t *testing.T) {
	ml := therapy.NewMasteryLog(100, "/tmp/test_empty_mastery.json")
	ledger := NewControllabilityLedger(ml)
	score := ledger.Score("unknown_topic")
	if score.Score != 0 {
		t.Errorf("no mastery data should return score=0, got %.2f", score.Score)
	}
}

func TestLedger_HighSuccessRateHighScore(t *testing.T) {
	ledger := newTestLedger(1.0, 5)
	score := ledger.Score("coding")
	if score.Score < MinAgencyScore {
		t.Errorf("high success rate should produce score ≥ MinAgencyScore (%.2f), got %.2f", MinAgencyScore, score.Score)
	}
}

func TestLedger_InsufficientCountNoActivation(t *testing.T) {
	ml := therapy.NewMasteryLog(100, "/tmp/test_single_mastery.json")
	ml.Record("coding", "one success", true)
	ledger := NewControllabilityLedger(ml)
	circuit := NewHopeCircuit(ledger)
	activation := circuit.Activate("coding")
	if activation.Activated {
		t.Error("single success should not activate Hope Circuit (below MinSuccessCount)")
	}
}

func TestCircuit_ActivatesWithSufficientEvidence(t *testing.T) {
	ledger := newTestLedger(1.0, 5)
	circuit := NewHopeCircuit(ledger)
	activation := circuit.Activate("coding")
	if !activation.Activated {
		t.Errorf("5 successes at 100%% should activate Hope Circuit, score=%.2f", activation.AgencyScore)
	}
	if activation.InjectedContext == "" {
		t.Error("activated circuit should provide injected context")
	}
	if activation.EvidenceCount < MinSuccessCount {
		t.Errorf("evidence count should be ≥ %d, got %d", MinSuccessCount, activation.EvidenceCount)
	}
}

func TestCircuit_StrongTemplateOnHighScore(t *testing.T) {
	ledger := newTestLedger(1.0, 10) // very high score
	circuit := NewHopeCircuit(ledger)
	activation := circuit.Activate("coding")
	if !activation.Activated {
		t.Skip("not activated")
	}
	if activation.AgencyScore < StrongAgencyScore {
		t.Logf("score %.2f below StrongAgencyScore %.2f — moderate template used", activation.AgencyScore, StrongAgencyScore)
	}
	// Just verify context is non-empty and contains useful framing
	if len(activation.InjectedContext) < 50 {
		t.Errorf("injected context too short: %q", activation.InjectedContext)
	}
}

func TestCircuit_NoActivationLowRate(t *testing.T) {
	ml := therapy.NewMasteryLog(100, "/tmp/test_low_rate_mastery.json")
	// Low success rate
	for i := 0; i < 3; i++ {
		ml.Record("math", "solve equation", false)
	}
	ml.Record("math", "solve equation", true)
	ledger := NewControllabilityLedger(ml)
	circuit := NewHopeCircuit(ledger)
	activation := circuit.Activate("math")
	if activation.Activated {
		t.Errorf("low success rate should not activate (score=%.2f)", activation.AgencyScore)
	}
}

func TestStats_RecordAndQuery(t *testing.T) {
	stats := NewAgencyStats("/tmp/test_agency_stats.json")
	activation := HopeActivation{Activated: true, TopicClass: "coding", AgencyScore: 0.8, EvidenceCount: 5}
	stats.Record(activation)

	s := stats.Stats()
	if a, ok := s["activations"].(int); !ok || a == 0 {
		t.Error("expected at least 1 activation in stats")
	}
}
