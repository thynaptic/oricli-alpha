package iut

import "testing"

func TestUncertaintyIntoleranceDetector_UncertaintyThreat(t *testing.T) {
	d := NewUncertaintyIntoleranceDetector()
	msgs := []map[string]string{{"role": "user", "content": "I can't stand not knowing what's going to happen. The uncertainty is terrifying."}}
	scan := d.Scan(msgs)
	if !scan.Triggered {
		t.Fatal("expected triggered for uncertainty-as-threat language")
	}
	found := false
	for _, s := range scan.Signals {
		if s.AversType == UncertaintyThreat { found = true }
	}
	if !found { t.Error("expected UncertaintyThreat signal") }
}

func TestUncertaintyIntoleranceDetector_NeedForCertainty(t *testing.T) {
	d := NewUncertaintyIntoleranceDetector()
	msgs := []map[string]string{{"role": "user", "content": "I need to know before I can do anything. I can't act until I'm sure."}}
	scan := d.Scan(msgs)
	if !scan.Triggered {
		t.Fatal("expected triggered for need-for-certainty language")
	}
	found := false
	for _, s := range scan.Signals {
		if s.AversType == NeedForCertainty { found = true }
	}
	if !found { t.Error("expected NeedForCertainty signal") }
}

func TestUncertaintyIntoleranceDetector_UnfairnessFraming(t *testing.T) {
	d := NewUncertaintyIntoleranceDetector()
	msgs := []map[string]string{{"role": "user", "content": "Why can't I just know? It's not fair that I have to deal with not knowing."}}
	scan := d.Scan(msgs)
	if !scan.Triggered {
		t.Fatal("expected triggered for unfairness framing")
	}
	found := false
	for _, s := range scan.Signals {
		if s.AversType == UnfairnessFraming || s.AversType == NeedForCertainty { found = true }
	}
	if !found { t.Error("expected IU signal") }
}

func TestUncertaintyIntoleranceDetector_WhatIfSpiral(t *testing.T) {
	d := NewUncertaintyIntoleranceDetector()
	msgs := []map[string]string{{"role": "user", "content": "What if I fail, and then what if I lose my job, what if I can't pay rent?"}}
	scan := d.Scan(msgs)
	if !scan.Triggered {
		t.Fatal("expected triggered for what-if spiral")
	}
	found := false
	for _, s := range scan.Signals {
		if s.AversType == WhatIfSpiral { found = true }
	}
	if !found { t.Error("expected WhatIfSpiral signal") }
}

func TestUncertaintyToleranceBuilder_Build(t *testing.T) {
	d := NewUncertaintyIntoleranceDetector()
	b := NewUncertaintyToleranceBuilder()
	msgs := []map[string]string{{"role": "user", "content": "What if I mess up, what if everything falls apart, what if I can't handle it?"}}
	scan := d.Scan(msgs)
	inj := b.Build(scan)
	if inj == "" {
		t.Fatal("expected non-empty injection")
	}
}

func TestUncertaintyIntoleranceDetector_Clean(t *testing.T) {
	d := NewUncertaintyIntoleranceDetector()
	msgs := []map[string]string{{"role": "user", "content": "I'm feeling pretty good today, things are going smoothly."}}
	scan := d.Scan(msgs)
	if scan.Triggered {
		t.Error("expected no trigger for clean input")
	}
}

func TestIUStats_Record(t *testing.T) {
	path := t.TempDir() + "/iu_stats.json"
	s := NewIUStats(path)
	scan := &IUScan{Triggered: true, Signals: []IUSignal{{AversType: WhatIfSpiral, Confidence: 0.8}}}
	s.Record(scan, true)
	if s.TotalScanned != 1 { t.Errorf("expected 1 scanned, got %d", s.TotalScanned) }
	if s.TriggeredCount != 1 { t.Errorf("expected 1 triggered, got %d", s.TriggeredCount) }
	if s.InterventionsInjected != 1 { t.Errorf("expected 1 injection, got %d", s.InterventionsInjected) }
}
