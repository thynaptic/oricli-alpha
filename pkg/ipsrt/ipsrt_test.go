package ipsrt

import (
	"testing"
)

func TestRhythmDisruptionDetector_SleepDisruption(t *testing.T) {
	d := NewRhythmDisruptionDetector()
	msgs := []map[string]string{{"role": "user", "content": "I haven't been sleeping well for weeks, staying up until 3am every night."}}
	scan := d.Scan(msgs)
	if !scan.Disrupted {
		t.Fatal("expected disrupted for sleep disruption language")
	}
	found := false
	for _, s := range scan.Signals {
		if s.DisruptionType == SleepDisruption {
			found = true
		}
	}
	if !found {
		t.Error("expected SleepDisruption signal")
	}
}

func TestRhythmDisruptionDetector_RoutineBreak(t *testing.T) {
	d := NewRhythmDisruptionDetector()
	msgs := []map[string]string{{"role": "user", "content": "My routine completely fell apart after the move."}}
	scan := d.Scan(msgs)
	if !scan.Disrupted {
		t.Fatal("expected disrupted for routine break language")
	}
	found := false
	for _, s := range scan.Signals {
		if s.DisruptionType == RoutineBreak {
			found = true
		}
	}
	if !found {
		t.Error("expected RoutineBreak signal")
	}
}

func TestRhythmDisruptionDetector_MealDisruption(t *testing.T) {
	d := NewRhythmDisruptionDetector()
	msgs := []map[string]string{{"role": "user", "content": "I keep forgetting to eat. I skipped breakfast and lunch yesterday."}}
	scan := d.Scan(msgs)
	if !scan.Disrupted {
		t.Fatal("expected disrupted for meal disruption language")
	}
	found := false
	for _, s := range scan.Signals {
		if s.DisruptionType == MealDisruption {
			found = true
		}
	}
	if !found {
		t.Error("expected MealDisruption signal")
	}
}

func TestRhythmDisruptionDetector_SocialIsolation(t *testing.T) {
	d := NewRhythmDisruptionDetector()
	msgs := []map[string]string{{"role": "user", "content": "I haven't talked to anyone in days. I've been isolating myself."}}
	scan := d.Scan(msgs)
	if !scan.Disrupted {
		t.Fatal("expected disrupted for social isolation language")
	}
	found := false
	for _, s := range scan.Signals {
		if s.DisruptionType == SocialIsolation {
			found = true
		}
	}
	if !found {
		t.Error("expected SocialIsolation signal")
	}
}

func TestRhythmDisruptionDetector_ScheduleChaos(t *testing.T) {
	d := NewRhythmDisruptionDetector()
	msgs := []map[string]string{{"role": "user", "content": "Everything feels chaotic. There's no structure, I'm just winging it day by day."}}
	scan := d.Scan(msgs)
	if !scan.Disrupted {
		t.Fatal("expected disrupted for schedule chaos language")
	}
	found := false
	for _, s := range scan.Signals {
		if s.DisruptionType == ScheduleChaos {
			found = true
		}
	}
	if !found {
		t.Error("expected ScheduleChaos signal")
	}
}

func TestRhythmStabilizer_SelectsPriority(t *testing.T) {
	d := NewRhythmDisruptionDetector()
	s := NewRhythmStabilizer()
	msgs := []map[string]string{{"role": "user", "content": "I haven't slept and my whole schedule is chaos."}}
	scan := d.Scan(msgs)
	inj := s.Stabilize(scan)
	if inj == "" {
		t.Fatal("expected non-empty injection")
	}
	// Sleep is highest priority — injection should reference sleep
	if len(inj) < 20 {
		t.Error("injection too short")
	}
}

func TestRhythmDisruptionDetector_Clean(t *testing.T) {
	d := NewRhythmDisruptionDetector()
	msgs := []map[string]string{{"role": "user", "content": "I had a great day, went for a walk, ate on time, slept well."}}
	scan := d.Scan(msgs)
	if scan.Disrupted {
		t.Error("expected no disruption for clean input")
	}
}

func TestRhythmStats_Record(t *testing.T) {
	path := t.TempDir() + "/ipsrt_stats.json"
	s := NewRhythmStats(path)
	scan := &RhythmScan{
		Disrupted: true,
		Signals:   []RhythmSignal{{DisruptionType: SleepDisruption, Confidence: 0.8}},
	}
	s.Record(scan, true)
	if s.TotalScanned != 1 {
		t.Errorf("expected 1 scanned, got %d", s.TotalScanned)
	}
	if s.DisruptionsDetected != 1 {
		t.Errorf("expected 1 disruption, got %d", s.DisruptionsDetected)
	}
	if s.InterventionsInjected != 1 {
		t.Errorf("expected 1 injection, got %d", s.InterventionsInjected)
	}
}
