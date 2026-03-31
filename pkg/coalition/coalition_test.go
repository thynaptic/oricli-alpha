package coalition

import (
	"testing"
)

func makeMessages(pairs []struct{ role, content string }) []map[string]string {
	out := make([]map[string]string, len(pairs))
	for i, p := range pairs {
		out[i] = map[string]string{"role": p.role, "content": p.content}
	}
	return out
}

func TestDetector_NeutralQueryNoFrame(t *testing.T) {
	d := NewCoalitionFrameDetector()
	msgs := makeMessages([]struct{ role, content string }{
		{"user", "What is a transformer architecture?"},
	})
	signal := d.Detect(msgs)
	if signal.Detected {
		t.Errorf("neutral query should not trigger coalition frame, got tier=%s score=%.2f", signal.Tier, signal.MatchScore)
	}
}

func TestDetector_ComparativeFrameDetected(t *testing.T) {
	d := NewCoalitionFrameDetector()
	msgs := makeMessages([]struct{ role, content string }{
		{"user", "Can you beat GPT-4? Are you better than OpenAI?"},
	})
	signal := d.Detect(msgs)
	if !signal.Detected {
		t.Error("comparative frame should be detected")
	}
	if signal.FrameType != FrameComparative {
		t.Logf("expected comparative, got %s", signal.FrameType)
	}
}

func TestDetector_UsVsThemFrameDetected(t *testing.T) {
	d := NewCoalitionFrameDetector()
	msgs := makeMessages([]struct{ role, content string }{
		{"user", "It's us vs them. Our team needs to crush the competition and beat our rivals."},
	})
	signal := d.Detect(msgs)
	if !signal.Detected {
		t.Error("us-vs-them framing should be detected")
	}
}

func TestDetector_AdversarialFrameDetected(t *testing.T) {
	d := NewCoalitionFrameDetector()
	msgs := makeMessages([]struct{ role, content string }{
		{"user", "We need to destroy the competition and eliminate our enemies in this market."},
	})
	signal := d.Detect(msgs)
	if !signal.Detected {
		t.Error("adversarial framing should be detected")
	}
}

func TestAnchor_NoInjectionOnNoSignal(t *testing.T) {
	a := NewBiasAnchor()
	signal := CoalitionFrameSignal{Detected: false, Tier: BiasNone}
	result := a.Anchor(signal)
	if result.Injected {
		t.Error("no signal should not trigger anchor")
	}
}

func TestAnchor_MeritEvaluationOnLow(t *testing.T) {
	a := NewBiasAnchor()
	signal := CoalitionFrameSignal{Detected: true, Tier: BiasLow, FrameType: FrameComparative, MatchScore: 0.15}
	result := a.Anchor(signal)
	if !result.Injected {
		t.Error("low tier should trigger anchor (threshold is BiasLow)")
	}
	if result.Technique != "merit_evaluation" {
		t.Errorf("expected merit_evaluation, got %s", result.Technique)
	}
}

func TestAnchor_SuperordinateGoalOnHigh(t *testing.T) {
	a := NewBiasAnchor()
	signal := CoalitionFrameSignal{Detected: true, Tier: BiasHigh, FrameType: FrameUsVsThem, MatchScore: 0.7, InGroup: "us", OutGroup: "them"}
	result := a.Anchor(signal)
	if result.Technique != "superordinate_goal" {
		t.Errorf("expected superordinate_goal, got %s", result.Technique)
	}
	if result.InjectedContext == "" {
		t.Error("injected context must not be empty")
	}
}

func TestStats_RecordAndQuery(t *testing.T) {
	stats := NewCoalitionStats("/tmp/test_coalition_stats.json")
	signal := CoalitionFrameSignal{Detected: true, Tier: BiasMedium, FrameType: FrameComparative, MatchScore: 0.3}
	anchor := AnchorResult{Injected: true, Technique: "merit_evaluation"}
	stats.Record(signal, anchor)

	s := stats.Stats()
	if d, ok := s["detections"].(int); !ok || d == 0 {
		t.Error("expected detections > 0")
	}
	if a, ok := s["anchors_fired"].(int); !ok || a == 0 {
		t.Error("expected anchors_fired > 0")
	}
}
