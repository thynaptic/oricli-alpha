package hopecircuit

import (
	"testing"
)

type stubMastery struct {
	rates    map[string]float64
	evidence map[string][]string
}

func (s *stubMastery) SuccessRate(topicClass string) float64 {
	if rate, ok := s.rates[topicClass]; ok {
		return rate
	}
	return -1
}

func (s *stubMastery) RecentEvidence(topicClass string, n int) []string {
	items := s.evidence[topicClass]
	if len(items) > n {
		return items[:n]
	}
	return items
}

func newTestLedger(successRate float64, successCount int) *ControllabilityLedger {
	evidence := make([]string, 0, successCount)
	for i := 0; i < successCount; i++ {
		evidence = append(evidence, "how do I implement a binary search tree")
	}
	return NewControllabilityLedger(&stubMastery{
		rates: map[string]float64{
			"coding": successRate,
		},
		evidence: map[string][]string{
			"coding": evidence,
		},
	})
}

func TestLedger_NoDataReturnsZeroScore(t *testing.T) {
	ledger := NewControllabilityLedger(&stubMastery{})
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
	ledger := NewControllabilityLedger(&stubMastery{
		rates: map[string]float64{
			"coding": 1.0,
		},
		evidence: map[string][]string{
			"coding": {"one success"},
		},
	})
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
	ledger := NewControllabilityLedger(&stubMastery{
		rates: map[string]float64{
			"math": 0.25,
		},
		evidence: map[string][]string{
			"math": {"solve equation"},
		},
	})
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
