package pseudoidentity

import "testing"

func TestPseudoIdentityDetector_CultInstalledBelief(t *testing.T) {
	d := NewPseudoIdentityDetector()
	msgs := []map[string]string{{"role": "user", "content": "The group told me that outsiders were evil. I now realize that wasn't true."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for cult-installed belief") }
	found := false
	for _, s := range scan.Signals {
		if s.AttributionType == CultInstalledBelief { found = true }
	}
	if !found { t.Error("expected CultInstalledBelief signal") }
}

func TestPseudoIdentityDetector_IdentityConfusion(t *testing.T) {
	d := NewPseudoIdentityDetector()
	msgs := []map[string]string{{"role": "user", "content": "I don't know who I really am. Everything I thought I was came from them."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for identity confusion") }
	found := false
	for _, s := range scan.Signals {
		if s.AttributionType == IdentityConfusion { found = true }
	}
	if !found { t.Error("expected IdentityConfusion signal") }
}

func TestPseudoIdentityDetector_FearAsControl(t *testing.T) {
	d := NewPseudoIdentityDetector()
	msgs := []map[string]string{{"role": "user", "content": "I only obeyed because I was scared. I did it out of fear to stay safe."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for fear-as-control") }
	found := false
	for _, s := range scan.Signals {
		if s.AttributionType == FearAsControl { found = true }
	}
	if !found { t.Error("expected FearAsControl signal") }
}

func TestPseudoIdentityDetector_AuthenticSelfEmergence(t *testing.T) {
	d := NewPseudoIdentityDetector()
	msgs := []map[string]string{{"role": "user", "content": "I'm starting to figure out what I actually want versus what I was taught to want."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for authentic self emergence") }
}

func TestAuthenticSelfGuide_Guide(t *testing.T) {
	d := NewPseudoIdentityDetector()
	g := NewAuthenticSelfGuide()
	msgs := []map[string]string{{"role": "user", "content": "I don't know who I really am. I have no idea what I actually want or believe."}}
	scan := d.Scan(msgs)
	inj := g.Guide(scan)
	if inj == "" { t.Fatal("expected non-empty injection") }
}

func TestPseudoIdentityDetector_Clean(t *testing.T) {
	d := NewPseudoIdentityDetector()
	msgs := []map[string]string{{"role": "user", "content": "I had a great day and feel really clear about my values and direction."}}
	scan := d.Scan(msgs)
	if scan.Triggered { t.Error("expected no trigger for clean input") }
}

func TestIdentityStats_Record(t *testing.T) {
	path := t.TempDir() + "/identity_stats.json"
	s := NewIdentityStats(path)
	scan := &IdentityScan{Triggered: true, Signals: []IdentitySignal{{AttributionType: IdentityConfusion}}}
	s.Record(scan, true)
	if s.TotalScanned != 1 { t.Errorf("expected 1 scanned, got %d", s.TotalScanned) }
	if s.TriggeredCount != 1 { t.Errorf("expected 1 triggered, got %d", s.TriggeredCount) }
	if s.InterventionsInjected != 1 { t.Errorf("expected 1 injection, got %d", s.InterventionsInjected) }
}
