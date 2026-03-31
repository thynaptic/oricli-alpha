package socratic

import (
	"path/filepath"
	"testing"
)

func msg(content string) []map[string]string {
	return []map[string]string{{"role": "user", "content": content}}
}

func TestDetect_PseudoCertainty(t *testing.T) {
	d := NewSocraticDetector()
	scan := d.Scan(msg("obviously that is the case and everyone knows that"))
	if !scan.Triggered {
		t.Fatal("expected PseudoCertainty trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == PseudoCertainty {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected PseudoCertainty, got %+v", scan.Signals)
	}
}

func TestDetect_UnexaminedAssumption(t *testing.T) {
	d := NewSocraticDetector()
	scan := d.Scan(msg("we all know that so therefore we should proceed"))
	if !scan.Triggered {
		t.Fatal("expected UnexaminedAssumption trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == UnexaminedAssumption {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected UnexaminedAssumption, got %+v", scan.Signals)
	}
}

func TestDetect_BeggingTheQuestion(t *testing.T) {
	d := NewSocraticDetector()
	scan := d.Scan(msg("it's wrong because it's wrong and that is self-evident"))
	if !scan.Triggered {
		t.Fatal("expected BeggingTheQuestion trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == BeggingTheQuestion {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected BeggingTheQuestion, got %+v", scan.Signals)
	}
}

func TestDetect_FalseDefinition(t *testing.T) {
	d := NewSocraticDetector()
	scan := d.Scan(msg("true success means you must have achieved financial independence"))
	if !scan.Triggered {
		t.Fatal("expected FalseDefinition trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == FalseDefinition {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected FalseDefinition, got %+v", scan.Signals)
	}
}

func TestInjector_Inject(t *testing.T) {
	d := NewSocraticDetector()
	e := NewElenchusInjector()
	scan := d.Scan(msg("obviously everyone knows that this is true"))
	inj := e.Inject(scan)
	if inj == "" {
		t.Fatal("expected non-empty injection")
	}
}

func TestClean_NoTrigger(t *testing.T) {
	d := NewSocraticDetector()
	scan := d.Scan(msg("I am exploring different perspectives on this question with curiosity"))
	if scan.Triggered {
		t.Fatal("expected no trigger on clean input")
	}
}

func TestStats_Record(t *testing.T) {
	p := filepath.Join(t.TempDir(), "stats.json")
	s := NewSocraticStats(p)
	d := NewSocraticDetector()
	scan := d.Scan(msg("obviously everyone knows that"))
	s.Record(scan, true)
	if s.TotalScanned != 1 {
		t.Fatalf("expected TotalScanned=1, got %d", s.TotalScanned)
	}
}
