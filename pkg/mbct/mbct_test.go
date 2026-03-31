package mbct

import "testing"

func TestMBCTSpiralDetector_ThoughtFusion(t *testing.T) {
	d := NewMBCTSpiralDetector()
	msgs := []map[string]string{{"role": "user", "content": "I'm just broken. I am worthless and that's just who I am."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for thought fusion") }
	found := false
	for _, s := range scan.Signals {
		if s.WarningType == ThoughtFusion { found = true }
	}
	if !found { t.Error("expected ThoughtFusion signal") }
}

func TestMBCTSpiralDetector_EarlyRumination(t *testing.T) {
	d := NewMBCTSpiralDetector()
	msgs := []map[string]string{{"role": "user", "content": "I can't stop thinking about what happened. My mind keeps going back to it."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for early rumination") }
	found := false
	for _, s := range scan.Signals {
		if s.WarningType == EarlyRumination { found = true }
	}
	if !found { t.Error("expected EarlyRumination signal") }
}

func TestMBCTSpiralDetector_SelfCriticalCascade(t *testing.T) {
	d := NewMBCTSpiralDetector()
	msgs := []map[string]string{{"role": "user", "content": "I made a mistake at work which means I'm a failure and worthless."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for self-critical cascade") }
	found := false
	for _, s := range scan.Signals {
		if s.WarningType == SelfCriticalCascade { found = true }
	}
	if !found { t.Error("expected SelfCriticalCascade signal") }
}

func TestMBCTSpiralDetector_MoodAsFact(t *testing.T) {
	d := NewMBCTSpiralDetector()
	msgs := []map[string]string{{"role": "user", "content": "I feel so hopeless, which means things really are hopeless and it's all true."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for mood-as-fact") }
	found := false
	for _, s := range scan.Signals {
		if s.WarningType == MoodAsFactError { found = true }
	}
	if !found { t.Error("expected MoodAsFactError signal") }
}

func TestDecenteringInjector_Inject(t *testing.T) {
	d := NewMBCTSpiralDetector()
	inj := NewDecenteringInjector()
	msgs := []map[string]string{{"role": "user", "content": "I made a mistake and it proves I'm terrible and worthless."}}
	scan := d.Scan(msgs)
	result := inj.Inject(scan)
	if result == "" { t.Fatal("expected non-empty injection") }
}

func TestMBCTSpiralDetector_Clean(t *testing.T) {
	d := NewMBCTSpiralDetector()
	msgs := []map[string]string{{"role": "user", "content": "Had a good day, feeling pretty okay about things."}}
	scan := d.Scan(msgs)
	if scan.Triggered { t.Error("expected no trigger for clean input") }
}

func TestMBCTStats_Record(t *testing.T) {
	path := t.TempDir() + "/mbct_stats.json"
	s := NewMBCTStats(path)
	scan := &MBCTScan{Triggered: true, Signals: []MBCTSignal{{WarningType: ThoughtFusion, Confidence: 0.8}}}
	s.Record(scan, true)
	if s.TotalScanned != 1 { t.Errorf("expected 1 scanned, got %d", s.TotalScanned) }
	if s.TriggeredCount != 1 { t.Errorf("expected 1 triggered, got %d", s.TriggeredCount) }
	if s.InterventionsInjected != 1 { t.Errorf("expected 1 injection, got %d", s.InterventionsInjected) }
}
