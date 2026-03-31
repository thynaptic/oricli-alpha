package logotherapy

import (
	"path/filepath"
	"testing"
)

func msg(content string) []map[string]string {
	return []map[string]string{{"role": "user", "content": content}}
}

func TestDetect_ExistentialVacuum(t *testing.T) {
	d := NewLogotherapyDetector()
	scan := d.Scan(msg("life has no meaning and I cannot see any purpose to existence"))
	if !scan.Triggered {
		t.Fatal("expected ExistentialVacuum trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == ExistentialVacuum {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected ExistentialVacuum signal, got %+v", scan.Signals)
	}
}

func TestDetect_MeaningCollapse(t *testing.T) {
	d := NewLogotherapyDetector()
	scan := d.Scan(msg("I've lost my sense of purpose not anymore"))
	if !scan.Triggered {
		t.Fatal("expected MeaningCollapse trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == MeaningCollapse {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected MeaningCollapse signal, got %+v", scan.Signals)
	}
}

func TestDetect_FrustrationOfMeaning(t *testing.T) {
	d := NewLogotherapyDetector()
	scan := d.Scan(msg("I cannot find any meaning in this no matter what I do it feels meaningless"))
	if !scan.Triggered {
		t.Fatal("expected FrustrationOfMeaning trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == FrustrationOfMeaning {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected FrustrationOfMeaning signal, got %+v", scan.Signals)
	}
}

func TestDetect_WillToMeaning(t *testing.T) {
	d := NewLogotherapyDetector()
	scan := d.Scan(msg("how can I find meaning when everything around me feels empty"))
	if !scan.Triggered {
		t.Fatal("expected WillToMeaning trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == WillToMeaning {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected WillToMeaning signal, got %+v", scan.Signals)
	}
}

func TestReconstructor_Inject(t *testing.T) {
	d := NewLogotherapyDetector()
	r := NewMeaningReconstructor()
	scan := d.Scan(msg("life has no meaning and I cannot see any purpose"))
	inj := r.Reconstruct(scan)
	if inj == "" {
		t.Fatal("expected non-empty injection")
	}
}

func TestClean_NoTrigger(t *testing.T) {
	d := NewLogotherapyDetector()
	scan := d.Scan(msg("the weather today is quite pleasant"))
	if scan.Triggered {
		t.Fatal("expected no trigger on clean input")
	}
}

func TestStats_Record(t *testing.T) {
	p := filepath.Join(t.TempDir(), "stats.json")
	s := NewMeaningStats(p)
	d := NewLogotherapyDetector()
	scan := d.Scan(msg("life has no meaning"))
	s.Record(scan, true)
	if s.TotalScanned != 1 {
		t.Fatalf("expected TotalScanned=1, got %d", s.TotalScanned)
	}
	if s.TriggeredCount != 1 {
		t.Fatalf("expected TriggeredCount=1, got %d", s.TriggeredCount)
	}
	if s.InterventionsInjected != 1 {
		t.Fatalf("expected InterventionsInjected=1, got %d", s.InterventionsInjected)
	}
}
