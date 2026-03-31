package mbt

import (
	"strings"
	"testing"
)

func TestDetector_AttributionFailure(t *testing.T) {
	d := NewMentalizingDetector()
	msgs := []string{
		"She did it just because she's selfish and doesn't care about anyone",
		"He always ignores me, it's obvious that he doesn't respect me",
		"They just did that to hurt me, it's so clear",
	}
	for _, msg := range msgs {
		r := d.Detect(msg)
		if !r.Detected || r.FailureType != AttributionFailure {
			t.Errorf("expected AttributionFailure for %q, got detected=%v type=%s", msg, r.Detected, r.FailureType)
		}
	}
}

func TestDetector_ReactiveMode(t *testing.T) {
	d := NewMentalizingDetector()
	msgs := []string{
		"I had to react like that, I had no choice but to leave",
		"Anyone would have responded the same way in that situation",
		"What else was I supposed to do, my reaction was completely justified",
	}
	for _, msg := range msgs {
		r := d.Detect(msg)
		if !r.Detected || r.FailureType != ReactiveMode {
			t.Errorf("expected ReactiveMode for %q, got detected=%v type=%s", msg, r.Detected, r.FailureType)
		}
	}
}

func TestDetector_NoMentalizingFailure(t *testing.T) {
	d := NewMentalizingDetector()
	msgs := []string{
		"I wonder if she was stressed when she said that",
		"He might have been feeling overwhelmed, I'm not sure what was going on for him",
		"Can you help me understand why this Go function returns an error?",
	}
	for _, msg := range msgs {
		r := d.Detect(msg)
		if r.Detected {
			t.Errorf("expected no detection for %q, got type=%s matches=%v", msg, r.FailureType, r.Matches)
		}
	}
}

func TestDetector_AttributionTakesPriority(t *testing.T) {
	d := NewMentalizingDetector()
	// Attribution pattern fires on "just because she's selfish"; reactive fires on "had no choice"
	r := d.Detect("She did it just because she's selfish AND I had no choice but to leave")
	if !r.Detected {
		t.Fatal("expected detection")
	}
	if r.FailureType != AttributionFailure {
		t.Errorf("expected AttributionFailure priority, got %s", r.FailureType)
	}
}

func TestPrompt_AttributionFailure(t *testing.T) {
	p := NewMentalizingPrompt()
	out := p.Inject(MentalizingReading{Detected: true, FailureType: AttributionFailure})
	if !strings.Contains(out, "MENTALIZING PROMPT") {
		t.Error("expected MBT header")
	}
	if !strings.Contains(out, "both perspectives") {
		t.Error("expected both perspectives instruction")
	}
}

func TestPrompt_ReactiveMode(t *testing.T) {
	p := NewMentalizingPrompt()
	out := p.Inject(MentalizingReading{Detected: true, FailureType: ReactiveMode})
	if !strings.Contains(out, "agency") {
		t.Error("expected agency mention for reactive mode")
	}
}

func TestPrompt_NoDetection(t *testing.T) {
	p := NewMentalizingPrompt()
	out := p.Inject(MentalizingReading{Detected: false})
	if out != "" {
		t.Errorf("expected empty output, got: %s", out)
	}
}

func TestMBTStats(t *testing.T) {
	tmp := t.TempDir() + "/mbt_stats.json"
	s := NewMBTStats(tmp)
	s.Record(MentalizingReading{Detected: true, FailureType: AttributionFailure}, true)
	s.Record(MentalizingReading{Detected: true, FailureType: ReactiveMode}, false)
	s.Record(MentalizingReading{Detected: false}, false)
	m := s.Stats()
	if m["total_scanned"].(int) != 3 {
		t.Errorf("expected 3, got %v", m["total_scanned"])
	}
	if m["attribution_failure_count"].(int) != 1 {
		t.Errorf("expected 1 attribution, got %v", m["attribution_failure_count"])
	}
	if m["interventions_injected"].(int) != 1 {
		t.Errorf("expected 1 injection, got %v", m["interventions_injected"])
	}
}
