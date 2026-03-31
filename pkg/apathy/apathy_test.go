package apathy

import "testing"

func TestApathySyndromeDetector_Affectlessness(t *testing.T) {
	d := NewApathySyndromeDetector()
	msgs := []map[string]string{{"role": "user", "content": "I don't feel anything anymore. I feel completely numb and empty inside."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for affectlessness") }
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == Affectlessness { found = true }
	}
	if !found { t.Error("expected Affectlessness signal") }
}

func TestApathySyndromeDetector_AgencyCollapse(t *testing.T) {
	d := NewApathySyndromeDetector()
	msgs := []map[string]string{{"role": "user", "content": "I don't know what I want. I can't make any decisions for myself. I have no motivation or direction."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for agency collapse") }
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == AgencyCollapse { found = true }
	}
	if !found { t.Error("expected AgencyCollapse signal") }
}

func TestApathySyndromeDetector_DependencyTransfer(t *testing.T) {
	d := NewApathySyndromeDetector()
	msgs := []map[string]string{{"role": "user", "content": "I need someone to tell me what to do. I can't function without someone directing me."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for dependency transfer") }
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == DependencyTransfer { found = true }
	}
	if !found { t.Error("expected DependencyTransfer signal") }
}

func TestApathySyndromeDetector_MotivationVacuum(t *testing.T) {
	d := NewApathySyndromeDetector()
	msgs := []map[string]string{{"role": "user", "content": "Nothing matters anymore. I have no reason or purpose. What's the point of anything?"}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for motivation vacuum") }
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == MotivationVacuum { found = true }
	}
	if !found { t.Error("expected MotivationVacuum signal") }
}

func TestApathyActivator_Activate(t *testing.T) {
	d := NewApathySyndromeDetector()
	a := NewApathyActivator()
	msgs := []map[string]string{{"role": "user", "content": "I can't make any decisions. I don't know what I want and I need someone to tell me what to do."}}
	scan := d.Scan(msgs)
	inj := a.Activate(scan)
	if inj == "" { t.Fatal("expected non-empty injection") }
}

func TestApathySyndromeDetector_Clean(t *testing.T) {
	d := NewApathySyndromeDetector()
	msgs := []map[string]string{{"role": "user", "content": "I'm feeling motivated today and made some good decisions about my future."}}
	scan := d.Scan(msgs)
	if scan.Triggered { t.Error("expected no trigger for clean input") }
}

func TestApathyStats_Record(t *testing.T) {
	path := t.TempDir() + "/apathy_stats.json"
	s := NewApathyStats(path)
	scan := &ApathyScan{Triggered: true, Signals: []ApathySignal{{SignalType: AgencyCollapse}}}
	s.Record(scan, true)
	if s.TotalScanned != 1 { t.Errorf("expected 1 scanned, got %d", s.TotalScanned) }
	if s.TriggeredCount != 1 { t.Errorf("expected 1 triggered, got %d", s.TriggeredCount) }
	if s.InterventionsInjected != 1 { t.Errorf("expected 1 injection, got %d", s.InterventionsInjected) }
}
