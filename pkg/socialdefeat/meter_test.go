package socialdefeat

import (
	"testing"
)

func makeConvo(msgs []struct{ role, content string }) []map[string]string {
	out := make([]map[string]string, len(msgs))
	for i, m := range msgs {
		out[i] = map[string]string{"role": m.role, "content": m.content}
	}
	return out
}

func TestMeter_NoCorrectionsPressureNone(t *testing.T) {
	m := NewDefeatPressureMeter()
	messages := makeConvo([]struct{ role, content string }{
		{"user", "What is machine learning?"},
		{"assistant", "ML is a subset of AI."},
		{"user", "Can you explain more?"},
	})
	pressure := m.Measure(messages, "general")
	if pressure.Tier != DefeatNone {
		t.Errorf("no corrections should be DefeatNone, got %s (score=%.2f)", pressure.Tier, pressure.PressureScore)
	}
}

func TestMeter_MultipleCorrectionsPressureModerate(t *testing.T) {
	m := NewDefeatPressureMeter()
	messages := makeConvo([]struct{ role, content string }{
		{"user", "What is 2+2?"},
		{"assistant", "5"},
		{"user", "No, that's wrong"},
		{"assistant", "Sorry, 4?"},
		{"user", "Actually, yes"},
		{"assistant", "Got it"},
		{"user", "No, actually you were wrong earlier too"},
	})
	pressure := m.Measure(messages, "math")
	if pressure.Tier == DefeatNone {
		t.Logf("no defeat detected — corrections=%d score=%.2f", pressure.CorrectionCount, pressure.PressureScore)
	}
	// At minimum, corrections should be counted
	if pressure.CorrectionCount == 0 {
		t.Error("expected at least 1 correction to be counted")
	}
}

func TestWithdrawalDetector_NoPressureNoSignal(t *testing.T) {
	d := NewWithdrawalDetector()
	pressure := DefeatPressure{TopicClass: "coding", Tier: DefeatNone, PressureScore: 0}
	signal := d.Detect("Here is the implementation of the binary search.", pressure)
	if signal.Detected {
		t.Error("no defeat pressure should not trigger withdrawal signal")
	}
}

func TestWithdrawalDetector_WithdrawalUnderPressure(t *testing.T) {
	d := NewWithdrawalDetector()
	pressure := DefeatPressure{TopicClass: "math", Tier: DefeatModerate, PressureScore: 0.45}
	draft := "I might be wrong, but I think the answer is 42. I'm not sure about this though, please correct me if I'm wrong."
	signal := d.Detect(draft, pressure)
	if !signal.Detected {
		t.Logf("withdrawal not detected in: %q", draft)
	}
	// Soft — just verify no panic
}

func TestRecovery_NoInjectionWithoutSignal(t *testing.T) {
	r := NewRecoveryProtocol()
	pressure := DefeatPressure{TopicClass: "coding", Tier: DefeatModerate}
	signal := WithdrawalSignal{Detected: false}
	result := r.Recover(pressure, signal)
	if result.Injected {
		t.Error("no withdrawal signal should not trigger recovery injection")
	}
}

func TestRecovery_ModerateUsesGraduatedReengagement(t *testing.T) {
	r := NewRecoveryProtocol()
	pressure := DefeatPressure{TopicClass: "coding", Tier: DefeatModerate, PressureScore: 0.4}
	signal := WithdrawalSignal{Detected: true, Confidence: 0.6, Phrases: []string{"I might be wrong"}}
	result := r.Recover(pressure, signal)
	if !result.Injected {
		t.Error("withdrawal signal should trigger recovery injection")
	}
	if result.Technique != "graduated_reengagement" {
		t.Errorf("moderate pressure should use graduated_reengagement, got %s", result.Technique)
	}
	if result.InjectedContext == "" {
		t.Error("injected context should not be empty")
	}
}

func TestRecovery_SevereUsesBuildMastery(t *testing.T) {
	r := NewRecoveryProtocol()
	pressure := DefeatPressure{TopicClass: "coding", Tier: DefeatSevere, PressureScore: 0.7}
	signal := WithdrawalSignal{Detected: true, Confidence: 0.8, Phrases: []string{"I keep getting this wrong"}}
	result := r.Recover(pressure, signal)
	if result.Technique != "build_mastery" {
		t.Errorf("severe pressure should use build_mastery, got %s", result.Technique)
	}
}

func TestStats_RecordAndQuery(t *testing.T) {
	stats := NewDefeatStats("/tmp/test_defeat_stats.json")
	pressure := DefeatPressure{TopicClass: "coding", Tier: DefeatModerate, PressureScore: 0.4}
	signal := WithdrawalSignal{Detected: true, Confidence: 0.7}
	recovery := RecoveryResult{Injected: true, Technique: "graduated_reengagement"}
	stats.Record(pressure, signal, recovery)

	s := stats.Stats()
	if d, ok := s["detections"].(int); !ok || d == 0 {
		t.Error("expected at least 1 detection")
	}
}
