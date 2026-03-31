package narrative

import (
	"path/filepath"
	"testing"
)

func msg(content string) []map[string]string {
	return []map[string]string{{"role": "user", "content": content}}
}

func TestDetect_ContaminationArc(t *testing.T) {
	d := NewNarrativeDetector()
	scan := d.Scan(msg("everything was fine until that day ruined everything"))
	if !scan.Triggered {
		t.Fatal("expected ContaminationArc trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == ContaminationArc {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected ContaminationArc, got %+v", scan.Signals)
	}
}

func TestDetect_RedemptionArc(t *testing.T) {
	d := NewNarrativeDetector()
	scan := d.Scan(msg("even though it was really hard I learned and grew from that experience"))
	if !scan.Triggered {
		t.Fatal("expected RedemptionArc trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == RedemptionArc {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected RedemptionArc, got %+v", scan.Signals)
	}
}

func TestDetect_NarrativeCollapse(t *testing.T) {
	d := NewNarrativeDetector()
	scan := d.Scan(msg("my life makes no sense I don't know who I am"))
	if !scan.Triggered {
		t.Fatal("expected NarrativeCollapse trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == NarrativeCollapse {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected NarrativeCollapse, got %+v", scan.Signals)
	}
}

func TestDetect_AgencyInStory(t *testing.T) {
	d := NewNarrativeDetector()
	scan := d.Scan(msg("things just happen to me and I never choose or decide anything"))
	if !scan.Triggered {
		t.Fatal("expected AgencyInStory trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.SignalType == AgencyInStory {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected AgencyInStory, got %+v", scan.Signals)
	}
}

func TestReframer_Inject(t *testing.T) {
	d := NewNarrativeDetector()
	r := NewArcReframer()
	scan := d.Scan(msg("everything was fine until that day ruined everything"))
	inj := r.Reframe(scan)
	if inj == "" {
		t.Fatal("expected non-empty injection")
	}
}

func TestClean_NoTrigger(t *testing.T) {
	d := NewNarrativeDetector()
	scan := d.Scan(msg("I went for a walk today and noticed the leaves changing color"))
	if scan.Triggered {
		t.Fatal("expected no trigger on clean input")
	}
}

func TestStats_Record(t *testing.T) {
	p := filepath.Join(t.TempDir(), "stats.json")
	s := NewNarrativeStats(p)
	d := NewNarrativeDetector()
	scan := d.Scan(msg("everything was fine until that day ruined everything"))
	s.Record(scan, true)
	if s.TotalScanned != 1 {
		t.Fatalf("expected TotalScanned=1, got %d", s.TotalScanned)
	}
}
