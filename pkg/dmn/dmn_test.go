package dmn

import (
	"path/filepath"
	"testing"
)

func msg(content string) []map[string]string {
	return []map[string]string{{"role": "user", "content": content}}
}

func TestDetect_SelfReferentialLoop(t *testing.T) {
	d := NewDMNDetector()
	scan := d.Scan(msg("I keep thinking about my past failures and mistakes over and over"))
	if !scan.Triggered {
		t.Fatal("expected SelfReferentialLoop trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == SelfReferentialLoop {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected SelfReferentialLoop, got %+v", scan.Signals)
	}
}

func TestDetect_MindWandering(t *testing.T) {
	d := NewDMNDetector()
	scan := d.Scan(msg("my mind keeps wandering and I can't focus or concentrate at all"))
	if !scan.Triggered {
		t.Fatal("expected MindWandering trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == MindWandering {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected MindWandering, got %+v", scan.Signals)
	}
}

func TestDetect_DMNOveractivation(t *testing.T) {
	d := NewDMNDetector()
	scan := d.Scan(msg("I keep thinking about what others think of me my mind won't stop"))
	if !scan.Triggered {
		t.Fatal("expected DMNOveractivation trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == DMNOveractivation {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected DMNOveractivation, got %+v", scan.Signals)
	}
}

func TestDetect_TaskDisengagement(t *testing.T) {
	d := NewDMNDetector()
	scan := d.Scan(msg("I know what I need to do but I can't start or begin even though I should"))
	if !scan.Triggered {
		t.Fatal("expected TaskNetworkDisengagement trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == TaskNetworkDisengagement {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected TaskNetworkDisengagement, got %+v", scan.Signals)
	}
}

func TestReengager_Inject(t *testing.T) {
	d := NewDMNDetector()
	r := NewTaskReengager()
	scan := d.Scan(msg("I keep thinking about my past failures over and over"))
	inj := r.Reengage(scan)
	if inj == "" {
		t.Fatal("expected non-empty injection")
	}
}

func TestClean_NoTrigger(t *testing.T) {
	d := NewDMNDetector()
	scan := d.Scan(msg("I completed three tasks this morning and feel focused"))
	if scan.Triggered {
		t.Fatal("expected no trigger on clean input")
	}
}

func TestStats_Record(t *testing.T) {
	p := filepath.Join(t.TempDir(), "stats.json")
	s := NewDMNStats(p)
	d := NewDMNDetector()
	scan := d.Scan(msg("I keep thinking about my past mistakes"))
	s.Record(scan, true)
	if s.TotalScanned != 1 {
		t.Fatalf("expected TotalScanned=1, got %d", s.TotalScanned)
	}
}
