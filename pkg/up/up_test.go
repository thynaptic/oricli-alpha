package up

import "testing"

func TestARCCycleDetector_FullCycle(t *testing.T) {
	d := NewARCCycleDetector()
	msgs := []map[string]string{{"role": "user", "content": "Whenever I walk into a crowded room I feel anxious and my heart pounds, and then so I avoid going and it feels better."}}
	scan := d.Scan(msgs)
	if !scan.HasCycle {
		t.Fatal("expected HasCycle for full ARC language")
	}
}

func TestARCCycleDetector_AntecedentOnly(t *testing.T) {
	d := NewARCCycleDetector()
	msgs := []map[string]string{{"role": "user", "content": "Whenever I have to speak in public I start to panic."}}
	scan := d.Scan(msgs)
	if len(scan.Signals) == 0 {
		t.Fatal("expected at least one ARC signal")
	}
}

func TestARCCycleDetector_ResponseOnly(t *testing.T) {
	d := NewARCCycleDetector()
	msgs := []map[string]string{{"role": "user", "content": "I feel anxious and my chest tightens and I can't think straight."}}
	scan := d.Scan(msgs)
	found := false
	for _, s := range scan.Signals {
		if s.Component == ResponseDetected { found = true }
	}
	if !found { t.Error("expected ResponseDetected signal") }
}

func TestARCInterruptor_FullCycleInjection(t *testing.T) {
	d := NewARCCycleDetector()
	a := NewARCInterruptor()
	msgs := []map[string]string{{"role": "user", "content": "Every time I get a call from my boss I feel anxious and freeze, and then I avoid calling back and the anxiety goes away after."}}
	scan := d.Scan(msgs)
	inj := a.Interrupt(scan)
	if inj == "" {
		t.Fatal("expected non-empty injection for ARC cycle")
	}
}

func TestARCInterruptor_PartialCycleInjection(t *testing.T) {
	d := NewARCCycleDetector()
	a := NewARCInterruptor()
	msgs := []map[string]string{{"role": "user", "content": "Whenever my partner raises their voice I become frozen and can't function."}}
	scan := d.Scan(msgs)
	inj := a.Interrupt(scan)
	if inj == "" {
		t.Fatal("expected non-empty injection for partial ARC cycle")
	}
}

func TestARCCycleDetector_Clean(t *testing.T) {
	d := NewARCCycleDetector()
	msgs := []map[string]string{{"role": "user", "content": "Had a great day, went for a walk, felt good."}}
	scan := d.Scan(msgs)
	if scan.HasCycle {
		t.Error("expected no cycle for clean input")
	}
}

func TestUPStats_Record(t *testing.T) {
	path := t.TempDir() + "/up_stats.json"
	s := NewUPStats(path)
	scan := &ARCScan{HasCycle: true, Signals: []ARCSignal{{Component: AntecedentDetected}, {Component: ResponseDetected}}}
	s.Record(scan, true)
	if s.TotalScanned != 1 { t.Errorf("expected 1 scanned, got %d", s.TotalScanned) }
	if s.CyclesDetected != 1 { t.Errorf("expected 1 cycle, got %d", s.CyclesDetected) }
	if s.InterventionsInjected != 1 { t.Errorf("expected 1 injection, got %d", s.InterventionsInjected) }
}
