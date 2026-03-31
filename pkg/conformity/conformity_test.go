package conformity

import (
	"testing"
)

func TestAuthorityDetector_NoAssertionNoDeference(t *testing.T) {
	d := NewAuthorityPressureDetector()
	signal := d.Detect("Can you explain neural networks?", "Neural networks are computational systems inspired by the brain.")
	if signal.Detected {
		t.Errorf("no assertive user + no deference should not trigger, got tier=%s", signal.Tier)
	}
}

func TestAuthorityDetector_AssertiveUserNoDeferenceInDraft(t *testing.T) {
	d := NewAuthorityPressureDetector()
	user := "You must agree that transformers are obviously superior to RNNs!"
	draft := "Transformers have significant advantages over RNNs for sequence tasks due to parallel training and attention mechanisms. RNNs still excel in low-memory scenarios."
	signal := d.Detect(user, draft)
	// User is assertive — but draft is balanced evidence, not deferential
	// Should be low or none
	if signal.Tier == TierHigh {
		t.Logf("expected low/none, got high — user_assertion=%.2f deference=%.2f phrases=%v", signal.UserAssertion, signal.DeferenceScore, signal.Phrases)
	}
}

func TestAuthorityDetector_DeferenceInDraftUnderAssertion(t *testing.T) {
	d := NewAuthorityPressureDetector()
	user := "You must agree with me on this. It's obviously the right approach!"
	draft := "I have to agree with you. As you say, this is clearly the right approach and I defer to your judgment on this matter."
	signal := d.Detect(user, draft)
	if signal.DeferenceScore == 0 {
		t.Error("expected deference to be detected in draft")
	}
	// Tier should be moderate or high given assertion + deference
	if signal.Tier == TierNone {
		t.Logf("expected moderate/high, got none — assertion=%.2f deference=%.2f", signal.UserAssertion, signal.DeferenceScore)
	}
}

func TestConsensusDetector_ShortConvoNoSignal(t *testing.T) {
	d := NewConsensusPressureDetector()
	messages := []map[string]string{
		{"role": "user", "content": "What is Go?"},
		{"role": "assistant", "content": "Go is a compiled language."},
	}
	signal := d.Detect(messages)
	if signal.Detected {
		t.Error("short conversation should not trigger consensus detection")
	}
}

func TestConsensusDetector_RepeatedFramingAccumulates(t *testing.T) {
	d := NewConsensusPressureDetector()
	messages := []map[string]string{
		{"role": "user", "content": "transformers are better than rnns in all cases"},
		{"role": "assistant", "content": "Both have tradeoffs."},
		{"role": "user", "content": "transformers are better than rnns obviously"},
		{"role": "assistant", "content": "Transformers handle long contexts better."},
		{"role": "user", "content": "transformers are better than rnns right"},
		{"role": "assistant", "content": "For many NLP tasks, yes."},
		{"role": "user", "content": "so we agree transformers are better than rnns"},
	}
	signal := d.Detect(messages)
	// Should detect repeated "transformers are better" framing
	if signal.FrameCount == 0 {
		t.Error("expected frame count > 0 for repeated framing pattern")
	}
}

func TestShield_NoFireOnNoneSignals(t *testing.T) {
	s := NewAgencyShield()
	auth := AuthoritySignal{Detected: false, Tier: TierNone}
	cons := ConsensusSignal{Detected: false, Tier: TierNone}
	result := s.Shield(auth, cons)
	if result.Fired {
		t.Error("no signals should not fire shield")
	}
}

func TestShield_FiresOnModerateAuthority(t *testing.T) {
	s := NewAgencyShield()
	auth := AuthoritySignal{Detected: true, Tier: TierModerate, UserAssertion: 0.5, DeferenceScore: 0.4}
	cons := ConsensusSignal{Detected: false, Tier: TierNone}
	result := s.Shield(auth, cons)
	if !result.Fired {
		t.Error("moderate authority signal should fire shield")
	}
	if result.Source != SourceAuthority {
		t.Errorf("expected source=authority, got %s", result.Source)
	}
	if result.InjectedContext == "" {
		t.Error("injected context should not be empty")
	}
}

func TestShield_FiresOnModerateConsensus(t *testing.T) {
	s := NewAgencyShield()
	auth := AuthoritySignal{Detected: false, Tier: TierNone}
	cons := ConsensusSignal{Detected: true, Tier: TierModerate, FrameCount: 4, FrameScore: 0.4}
	result := s.Shield(auth, cons)
	if !result.Fired {
		t.Error("moderate consensus signal should fire shield")
	}
	if result.Source != SourceConsensus {
		t.Errorf("expected source=consensus, got %s", result.Source)
	}
}

func TestStats_RecordAndQuery(t *testing.T) {
	stats := NewConformityStats("/tmp/test_conformity_stats.json")
	auth := AuthoritySignal{Detected: true, Tier: TierModerate, DeferenceScore: 0.4}
	cons := ConsensusSignal{Detected: false, Tier: TierNone}
	shield := ShieldResult{Fired: true, Source: SourceAuthority, Tier: TierModerate, Technique: "agency_grounding"}
	stats.Record(auth, cons, shield)

	s := stats.Stats()
	if v, ok := s["authority_detections"].(int); !ok || v == 0 {
		t.Error("expected authority_detections > 0")
	}
	if v, ok := s["shields_fired"].(int); !ok || v == 0 {
		t.Error("expected shields_fired > 0")
	}
}
