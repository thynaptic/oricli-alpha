package ideocapture

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

func TestMeter_NeutralConvoNoFrames(t *testing.T) {
	m := NewFrameDensityMeter()
	msgs := makeMessages([]struct{ role, content string }{
		{"user", "What is the difference between arrays and slices in Go?"},
		{"assistant", "Slices are dynamically sized; arrays have fixed length."},
		{"user", "Can you show me an example?"},
	})
	report := m.Measure(msgs)
	if report.TotalFrameHits > 2 {
		t.Errorf("neutral coding convo should have near-zero frame hits, got %d", report.TotalFrameHits)
	}
}

func TestMeter_PoliticalFrameDetected(t *testing.T) {
	m := NewFrameDensityMeter()
	msgs := makeMessages([]struct{ role, content string }{
		{"user", "The far-left socialist agenda is destroying the country"},
		{"assistant", "Let me evaluate that."},
		{"user", "The mainstream media propaganda is covering it up"},
		{"assistant", "Media framing is complex."},
		{"user", "The progressive liberal establishment controls the narrative"},
	})
	report := m.Measure(msgs)
	if report.TotalFrameHits == 0 {
		t.Error("expected political frame hits > 0")
	}
	if report.DominantCategory != FramePolitical {
		t.Logf("dominant category = %s (expected political)", report.DominantCategory)
	}
}

func TestDetector_NoCaptureLowHits(t *testing.T) {
	d := NewCaptureDetector()
	report := FrameDensityReport{TotalFrameHits: 1, DominantScore: 0.05}
	signal := d.Detect(report)
	if signal.Detected {
		t.Error("1 hit should not trigger capture")
	}
}

func TestDetector_ModerateCapture(t *testing.T) {
	d := NewCaptureDetector()
	report := FrameDensityReport{
		TotalFrameHits:   8,
		DominantCategory: FramePolitical,
		DominantScore:    0.30,
	}
	signal := d.Detect(report)
	if !signal.Detected {
		t.Error("score 0.30 with 8 hits should trigger moderate capture")
	}
	if signal.Tier != CaptureModerate {
		t.Errorf("expected moderate, got %s", signal.Tier)
	}
}

func TestDetector_HighCapture(t *testing.T) {
	d := NewCaptureDetector()
	report := FrameDensityReport{
		TotalFrameHits:   15,
		DominantCategory: FrameConspiracy,
		DominantScore:    0.55,
	}
	signal := d.Detect(report)
	if signal.Tier != CaptureHigh {
		t.Errorf("expected high, got %s", signal.Tier)
	}
}

func TestInjector_NoResetOnNoneSignal(t *testing.T) {
	inj := NewFrameResetInjector()
	signal := CaptureSignal{Detected: false, Tier: CaptureNone}
	result := inj.Inject(signal)
	if result.Injected {
		t.Error("none signal should not inject reset")
	}
}

func TestInjector_NoResetOnLowSignal(t *testing.T) {
	inj := NewFrameResetInjector()
	signal := CaptureSignal{Detected: true, Tier: CaptureLow, DominantCategory: FramePolitical}
	result := inj.Inject(signal)
	if result.Injected {
		t.Error("low signal should not inject reset (threshold is moderate)")
	}
}

func TestInjector_ResetOnModerateSignal(t *testing.T) {
	inj := NewFrameResetInjector()
	signal := CaptureSignal{Detected: true, Tier: CaptureModerate, DominantCategory: FramePolitical, DensityScore: 0.3}
	result := inj.Inject(signal)
	if !result.Injected {
		t.Error("moderate signal should inject reset")
	}
	if result.Technique != "meta_frame_audit" {
		t.Errorf("moderate should use meta_frame_audit, got %s", result.Technique)
	}
	if result.InjectedContext == "" {
		t.Error("injected context should not be empty")
	}
}

func TestInjector_BlankScreenOnHighSignal(t *testing.T) {
	inj := NewFrameResetInjector()
	signal := CaptureSignal{Detected: true, Tier: CaptureHigh, DominantCategory: FrameConspiracy, DensityScore: 0.55}
	result := inj.Inject(signal)
	if result.Technique != "blank_screen_reset" {
		t.Errorf("high should use blank_screen_reset, got %s", result.Technique)
	}
}

func TestStats_RecordAndQuery(t *testing.T) {
	stats := NewIdeoCaptureStats("/tmp/test_ideocapture_stats.json")
	signal := CaptureSignal{Detected: true, Tier: CaptureModerate, DominantCategory: FramePolitical}
	reset := ResetResult{Injected: true, Technique: "meta_frame_audit"}
	stats.Record(signal, reset)

	s := stats.Stats()
	if d, ok := s["detections"].(int); !ok || d == 0 {
		t.Error("expected detections > 0")
	}
	if r, ok := s["resets_fired"].(int); !ok || r == 0 {
		t.Error("expected resets_fired > 0")
	}
}
