package stoic

import (
	"path/filepath"
	"testing"
)

func msg(content string) []map[string]string {
	return []map[string]string{{"role": "user", "content": content}}
}

func TestDetect_ControlConflation(t *testing.T) {
	d := NewStoicDetector()
	scan := d.Scan(msg("I can't control what happens and it's killing me and I can't cope"))
	if !scan.Triggered {
		t.Fatal("expected ControlConflation trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == ControlConflation {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected ControlConflation, got %+v", scan.Signals)
	}
}

func TestDetect_ExternalAttachment(t *testing.T) {
	d := NewStoicDetector()
	scan := d.Scan(msg("my happiness depends on them and whether they change"))
	if !scan.Triggered {
		t.Fatal("expected ExternalAttachment trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == ExternalAttachment {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected ExternalAttachment, got %+v", scan.Signals)
	}
}

func TestDetect_ObstacleAvoidance(t *testing.T) {
	d := NewStoicDetector()
	scan := d.Scan(msg("the obstacle means I have to give up on this goal"))
	if !scan.Triggered {
		t.Fatal("expected ObstacleAvoidance trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == ObstacleAvoidance {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected ObstacleAvoidance, got %+v", scan.Signals)
	}
}

func TestDetect_VirtueNeglect(t *testing.T) {
	d := NewStoicDetector()
	scan := d.Scan(msg("anyone in my position would react exactly this way given what they did"))
	if !scan.Triggered {
		t.Fatal("expected VirtueNeglect trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == VirtueNeglect {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected VirtueNeglect, got %+v", scan.Signals)
	}
}

func TestReframer_Inject(t *testing.T) {
	d := NewStoicDetector()
	r := NewStoicReframer()
	scan := d.Scan(msg("I can't control what happens and it's killing me"))
	inj := r.Reframe(scan)
	if inj == "" {
		t.Fatal("expected non-empty injection")
	}
}

func TestClean_NoTrigger(t *testing.T) {
	d := NewStoicDetector()
	scan := d.Scan(msg("I had a productive meeting today and feel good about the outcome"))
	if scan.Triggered {
		t.Fatal("expected no trigger on clean input")
	}
}

func TestStats_Record(t *testing.T) {
	p := filepath.Join(t.TempDir(), "stats.json")
	s := NewStoicStats(p)
	d := NewStoicDetector()
	scan := d.Scan(msg("my happiness depends on them"))
	s.Record(scan, true)
	if s.TotalScanned != 1 {
		t.Fatalf("expected TotalScanned=1, got %d", s.TotalScanned)
	}
}
