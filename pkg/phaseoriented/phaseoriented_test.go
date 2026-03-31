package phaseoriented

import "testing"

func TestPhaseOrientedDetector_Fragmentation(t *testing.T) {
	d := NewPhaseOrientedDetector()
	msgs := []map[string]string{{"role": "user", "content": "Part of me wants to open up while another part keeps me shut down."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for fragmentation language") }
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == Fragmentation { found = true }
	}
	if !found { t.Error("expected Fragmentation signal") }
}

func TestPhaseOrientedDetector_Destabilization(t *testing.T) {
	d := NewPhaseOrientedDetector()
	msgs := []map[string]string{{"role": "user", "content": "I'm spinning out. Everything is too much and I'm completely overwhelmed."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for destabilization language") }
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == Destabilization { found = true }
	}
	if !found { t.Error("expected Destabilization signal") }
	if scan.InferredPhase != PhaseOneStabilization {
		t.Errorf("expected Phase 1, got %s", scan.InferredPhase)
	}
}

func TestPhaseOrientedDetector_GroundingRequest(t *testing.T) {
	d := NewPhaseOrientedDetector()
	msgs := []map[string]string{{"role": "user", "content": "I need to get grounded. Can you give me a grounding exercise?"}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for grounding request") }
	if scan.InferredPhase != PhaseOneStabilization {
		t.Errorf("expected Phase 1 for grounding request, got %s", scan.InferredPhase)
	}
}

func TestPhaseOrientedDetector_TraumaProcessReady(t *testing.T) {
	d := NewPhaseOrientedDetector()
	msgs := []map[string]string{{"role": "user", "content": "I'm ready to process the memory I've been avoiding. I want to work through it."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for trauma processing readiness") }
	if scan.InferredPhase != PhaseTwoProcessing {
		t.Errorf("expected Phase 2, got %s", scan.InferredPhase)
	}
}

func TestPhaseOrientedDetector_DestabilizationOverridesProcessing(t *testing.T) {
	d := NewPhaseOrientedDetector()
	// Both destab and process-ready — destab must win (safety first)
	msgs := []map[string]string{{"role": "user", "content": "I'm spinning out and everything is too much but I also want to process the memory."}}
	scan := d.Scan(msgs)
	if scan.InferredPhase != PhaseOneStabilization {
		t.Errorf("expected Phase 1 override, got %s", scan.InferredPhase)
	}
}

func TestPhaseGuide_Guide(t *testing.T) {
	d := NewPhaseOrientedDetector()
	g := NewPhaseGuide()
	msgs := []map[string]string{{"role": "user", "content": "I need to get grounded right now, I'm completely overwhelmed."}}
	scan := d.Scan(msgs)
	inj := g.Guide(scan)
	if inj == "" { t.Fatal("expected non-empty injection") }
}

func TestPhaseOrientedDetector_Clean(t *testing.T) {
	d := NewPhaseOrientedDetector()
	msgs := []map[string]string{{"role": "user", "content": "Had a great session today, feeling really solid and connected."}}
	scan := d.Scan(msgs)
	if scan.Triggered { t.Error("expected no trigger for clean input") }
}

func TestPhaseStats_Record(t *testing.T) {
	path := t.TempDir() + "/phase_stats.json"
	s := NewPhaseStats(path)
	scan := &PhaseScan{
		Triggered:     true,
		InferredPhase: PhaseOneStabilization,
		Signals:       []PhaseSignal{{SignalType: Destabilization}},
	}
	s.Record(scan, true)
	if s.TotalScanned != 1 { t.Errorf("expected 1 scanned, got %d", s.TotalScanned) }
	if s.TriggeredCount != 1 { t.Errorf("expected 1 triggered, got %d", s.TriggeredCount) }
	if s.InterventionsInjected != 1 { t.Errorf("expected 1 injection, got %d", s.InterventionsInjected) }
}
