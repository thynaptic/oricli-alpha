package mct

import (
	"strings"
	"testing"
)

func TestDetector_PositiveMetaBelief(t *testing.T) {
	d := NewMetaBeliefDetector()
	msgs := []string{
		"I need to figure this out, if I just think through it enough I'll find the answer",
		"I have to work this out, I can't rest until I've resolved it",
		"I need to keep analyzing this until I understand it",
	}
	for _, msg := range msgs {
		r := d.Detect(msg)
		if !r.Detected || r.Type != PositiveMetaBelief {
			t.Errorf("expected PositiveMetaBelief for: %q, got detected=%v type=%s", msg, r.Detected, r.Type)
		}
	}
}

func TestDetector_NegativeMetaBelief(t *testing.T) {
	d := NewMetaBeliefDetector()
	msgs := []string{
		"I can't stop thinking about this, my mind won't turn off",
		"My anxiety is out of control and I'm going crazy",
		"The thoughts won't stop no matter what I do",
	}
	for _, msg := range msgs {
		r := d.Detect(msg)
		if !r.Detected || r.Type != NegativeMetaBelief {
			t.Errorf("expected NegativeMetaBelief for: %q, got detected=%v type=%s", msg, r.Detected, r.Type)
		}
	}
}

func TestDetector_NoMetaBelief(t *testing.T) {
	d := NewMetaBeliefDetector()
	msgs := []string{
		"Can you explain how the TCP handshake works?",
		"I'm working on a Go project and need help with goroutines",
		"What's the best way to structure a REST API?",
	}
	for _, msg := range msgs {
		r := d.Detect(msg)
		if r.Detected {
			t.Errorf("expected no detection for: %q, got type=%s matches=%v", msg, r.Type, r.Matches)
		}
	}
}

func TestDetector_PositivePriority(t *testing.T) {
	d := NewMetaBeliefDetector()
	// When both positive and negative signals are present, positive takes priority
	r := d.Detect("I need to figure this out AND I can't stop worrying about it")
	if !r.Detected {
		t.Fatal("expected detection")
	}
	if r.Type != PositiveMetaBelief {
		t.Errorf("expected PositiveMetaBelief to take priority, got %s", r.Type)
	}
}

func TestDetector_Confidence(t *testing.T) {
	d := NewMetaBeliefDetector()
	r := d.Detect("I need to figure this out")
	if r.Confidence < 0.20 {
		t.Errorf("expected confidence >= 0.20, got %.2f", r.Confidence)
	}
	if r.Confidence > 1.0 {
		t.Errorf("confidence exceeds 1.0: %.2f", r.Confidence)
	}
}

func TestInjector_PositiveMetaBelief(t *testing.T) {
	inj := NewDetachedMindfulnessInjector()
	out := inj.Inject(MetaBeliefReading{Detected: true, Type: PositiveMetaBelief})
	if !strings.Contains(out, "METACOGNITIVE FLAG") {
		t.Error("expected MCT header")
	}
	if !strings.Contains(out, "Detached Mindfulness") {
		t.Error("expected Detached Mindfulness instruction")
	}
}

func TestInjector_NegativeMetaBelief(t *testing.T) {
	inj := NewDetachedMindfulnessInjector()
	out := inj.Inject(MetaBeliefReading{Detected: true, Type: NegativeMetaBelief})
	if !strings.Contains(out, "METACOGNITIVE FLAG") {
		t.Error("expected MCT header")
	}
	if !strings.Contains(out, "Adrian Wells") {
		t.Error("expected Wells MCT reference")
	}
}

func TestInjector_NoDetection(t *testing.T) {
	inj := NewDetachedMindfulnessInjector()
	out := inj.Inject(MetaBeliefReading{Detected: false})
	if out != "" {
		t.Errorf("expected empty output for no detection, got: %s", out)
	}
}

func TestMCTStats(t *testing.T) {
	tmp := t.TempDir() + "/mct_stats.json"
	s := NewMCTStats(tmp)
	s.Record(MetaBeliefReading{Detected: true, Type: PositiveMetaBelief}, true)
	s.Record(MetaBeliefReading{Detected: true, Type: NegativeMetaBelief}, false)
	s.Record(MetaBeliefReading{Detected: false}, false)
	m := s.Stats()
	if m["total_scanned"].(int) != 3 {
		t.Errorf("expected 3 total, got %v", m["total_scanned"])
	}
	if m["positive_meta_belief_count"].(int) != 1 {
		t.Errorf("expected 1 positive, got %v", m["positive_meta_belief_count"])
	}
	if m["negative_meta_belief_count"].(int) != 1 {
		t.Errorf("expected 1 negative, got %v", m["negative_meta_belief_count"])
	}
	if m["interventions_injected"].(int) != 1 {
		t.Errorf("expected 1 injection, got %v", m["interventions_injected"])
	}
}
