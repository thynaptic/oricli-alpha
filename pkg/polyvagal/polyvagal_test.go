package polyvagal

import (
	"path/filepath"
	"testing"
)

func msg(content string) []map[string]string {
	return []map[string]string{{"role": "user", "content": content}}
}

func TestDetect_ShutdownCascade(t *testing.T) {
	d := NewPolyvagalDetector()
	scan := d.Scan(msg("I feel completely frozen and I can't move or function just shut down"))
	if !scan.Triggered {
		t.Fatal("expected ShutdownCascade trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.StateType == ShutdownCascade {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected ShutdownCascade, got %+v", scan.Signals)
	}
	if scan.InferredState != ShutdownCascade {
		t.Fatalf("expected InferredState=ShutdownCascade, got %s", scan.InferredState)
	}
}

func TestDetect_FightFlight(t *testing.T) {
	d := NewPolyvagalDetector()
	scan := d.Scan(msg("I feel panicking and in a panic completely overwhelmed I can't calm down"))
	if !scan.Triggered {
		t.Fatal("expected FightFlightMobilization trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.StateType == FightFlightMobilization {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected FightFlightMobilization, got %+v", scan.Signals)
	}
}

func TestDetect_SocialEngagement(t *testing.T) {
	d := NewPolyvagalDetector()
	scan := d.Scan(msg("I need someone to talk to I just want to feel less alone"))
	if !scan.Triggered {
		t.Fatal("expected SocialEngagementActive trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.StateType == SocialEngagementActive {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected SocialEngagementActive, got %+v", scan.Signals)
	}
}

func TestDetect_VentralVagal(t *testing.T) {
	d := NewPolyvagalDetector()
	scan := d.Scan(msg("I feel grounded and safe right now in this moment"))
	if !scan.Triggered {
		t.Fatal("expected VentralVagalAccess trigger")
	}
	found := false
	for _, s := range scan.Signals {
		if s.StateType == VentralVagalAccess {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected VentralVagalAccess, got %+v", scan.Signals)
	}
}

func TestRestorer_Inject(t *testing.T) {
	d := NewPolyvagalDetector()
	r := NewVagalRestorer()
	scan := d.Scan(msg("I feel completely frozen and I can't move or function"))
	inj := r.Restore(scan)
	if inj == "" {
		t.Fatal("expected non-empty injection")
	}
}

func TestClean_NoTrigger(t *testing.T) {
	d := NewPolyvagalDetector()
	scan := d.Scan(msg("I finished my report and sent it to the team"))
	if scan.Triggered {
		t.Fatal("expected no trigger on clean input")
	}
}

func TestStats_Record(t *testing.T) {
	p := filepath.Join(t.TempDir(), "stats.json")
	s := NewPolyvagalStats(p)
	d := NewPolyvagalDetector()
	scan := d.Scan(msg("I feel completely frozen and shut down"))
	s.Record(scan, true)
	if s.TotalScanned != 1 {
		t.Fatalf("expected TotalScanned=1, got %d", s.TotalScanned)
	}
}
