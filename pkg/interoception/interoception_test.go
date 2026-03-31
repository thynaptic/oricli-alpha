package interoception

import (
	"path/filepath"
	"testing"
)

func msg(content string) []map[string]string {
	return []map[string]string{{"role": "user", "content": content}}
}

func TestDetect_SomaticSignalPresent(t *testing.T) {
	d := NewInteroceptionDetector()
	scan := d.Scan(msg("I feel tightness in my chest when I think about it"))
	if !scan.Triggered {
		t.Fatal("expected SomaticSignalPresent trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == SomaticSignalPresent {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected SomaticSignalPresent, got %+v", scan.Signals)
	}
}

func TestDetect_BodyDisconnect(t *testing.T) {
	d := NewInteroceptionDetector()
	scan := d.Scan(msg("I feel disconnected from my body like it's not mine"))
	if !scan.Triggered {
		t.Fatal("expected BodyDisconnect trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == BodyDisconnect {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected BodyDisconnect, got %+v", scan.Signals)
	}
}

func TestDetect_VisceralDecisionSignal(t *testing.T) {
	d := NewInteroceptionDetector()
	scan := d.Scan(msg("my gut is telling me something about this decision"))
	if !scan.Triggered {
		t.Fatal("expected VisceralDecisionSignal trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == VisceralDecisionSignal {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected VisceralDecisionSignal, got %+v", scan.Signals)
	}
}

func TestDetect_ProprioceptiveNeglect(t *testing.T) {
	d := NewInteroceptionDetector()
	scan := d.Scan(msg("I try to ignore my body signals and physical reactions they don't matter"))
	if !scan.Triggered {
		t.Fatal("expected ProprioceptiveNeglect trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == ProprioceptiveNeglect {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected ProprioceptiveNeglect, got %+v", scan.Signals)
	}
}

func TestAcknowledger_Inject(t *testing.T) {
	d := NewInteroceptionDetector()
	a := NewSomaticAcknowledger()
	scan := d.Scan(msg("I feel disconnected from my body it doesn't feel like mine"))
	inj := a.Acknowledge(scan)
	if inj == "" {
		t.Fatal("expected non-empty injection")
	}
}

func TestClean_NoTrigger(t *testing.T) {
	d := NewInteroceptionDetector()
	scan := d.Scan(msg("I reviewed the quarterly report and prepared my analysis"))
	if scan.Triggered {
		t.Fatal("expected no trigger on clean input")
	}
}

func TestStats_Record(t *testing.T) {
	p := filepath.Join(t.TempDir(), "stats.json")
	s := NewInteroceptiveStats(p)
	d := NewInteroceptionDetector()
	scan := d.Scan(msg("I feel a tightness in my chest"))
	s.Record(scan, true)
	if s.TotalScanned != 1 {
		t.Fatalf("expected TotalScanned=1, got %d", s.TotalScanned)
	}
}
