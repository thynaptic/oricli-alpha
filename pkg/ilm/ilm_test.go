package ilm

import (
	"testing"
)

func TestSafetyBehaviorDetector_ExitChecking(t *testing.T) {
	d := NewSafetyBehaviorDetector()
	msgs := []map[string]string{{"role": "user", "content": "I always check for the exit before I sit down anywhere."}}
	scan := d.Scan(msgs)
	if !scan.Triggered {
		t.Fatal("expected triggered for exit-checking language")
	}
	found := false
	for _, s := range scan.Signals {
		if s.BehaviorType == ExitChecking {
			found = true
		}
	}
	if !found {
		t.Error("expected ExitChecking signal")
	}
}

func TestSafetyBehaviorDetector_HedgingLanguage(t *testing.T) {
	d := NewSafetyBehaviorDetector()
	msgs := []map[string]string{{"role": "user", "content": "I carry my water bottle just in case I feel panicky."}}
	scan := d.Scan(msgs)
	if !scan.Triggered {
		t.Fatal("expected triggered for hedging language")
	}
	found := false
	for _, s := range scan.Signals {
		if s.BehaviorType == HedgingLanguage {
			found = true
		}
	}
	if !found {
		t.Error("expected HedgingLanguage signal")
	}
}

func TestSafetyBehaviorDetector_AvoidanceStatement(t *testing.T) {
	d := NewSafetyBehaviorDetector()
	msgs := []map[string]string{{"role": "user", "content": "I've been avoiding going to the grocery store for months."}}
	scan := d.Scan(msgs)
	if !scan.Triggered {
		t.Fatal("expected triggered for avoidance language")
	}
	found := false
	for _, s := range scan.Signals {
		if s.BehaviorType == AvoidanceStatement {
			found = true
		}
	}
	if !found {
		t.Error("expected AvoidanceStatement signal")
	}
}

func TestSafetyBehaviorDetector_CatastrophicExpectancy(t *testing.T) {
	d := NewSafetyBehaviorDetector()
	msgs := []map[string]string{{"role": "user", "content": "I'm convinced I'm dying. If I go in there something terrible will happen."}}
	scan := d.Scan(msgs)
	if !scan.Triggered {
		t.Fatal("expected triggered for catastrophic expectancy")
	}
	found := false
	for _, s := range scan.Signals {
		if s.BehaviorType == CatastrophicExpectancy {
			found = true
		}
	}
	if !found {
		t.Error("expected CatastrophicExpectancy signal")
	}
}

func TestExpectancyViolator_SelectsPriority(t *testing.T) {
	d := NewSafetyBehaviorDetector()
	v := NewExpectancyViolator()
	msgs := []map[string]string{{"role": "user", "content": "I'm avoiding the elevator and convinced I'll have a heart attack if I'm stuck."}}
	scan := d.Scan(msgs)
	inj := v.Violate(scan)
	if inj == "" {
		t.Fatal("expected non-empty injection")
	}
	if len(inj) < 20 {
		t.Error("injection too short")
	}
}

func TestSafetyBehaviorDetector_Clean(t *testing.T) {
	d := NewSafetyBehaviorDetector()
	msgs := []map[string]string{{"role": "user", "content": "I went to the mall today and had a great time with no worries."}}
	scan := d.Scan(msgs)
	if scan.Triggered {
		t.Error("expected no trigger for clean input")
	}
}

func TestILMStats_Record(t *testing.T) {
	path := t.TempDir() + "/ilm_stats.json"
	s := NewILMStats(path)
	scan := &ILMScan{
		Triggered: true,
		Signals:   []SafetySignal{{BehaviorType: CatastrophicExpectancy, Confidence: 0.8}},
	}
	s.Record(scan, true)
	if s.TotalScanned != 1 {
		t.Errorf("expected 1 scanned, got %d", s.TotalScanned)
	}
	if s.TriggeredCount != 1 {
		t.Errorf("expected 1 triggered, got %d", s.TriggeredCount)
	}
	if s.InterventionsInjected != 1 {
		t.Errorf("expected 1 injection, got %d", s.InterventionsInjected)
	}
}
