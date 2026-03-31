package cbasp

import "testing"

func TestCBASPDisconnectionDetector_ActionConsequenceBlindness(t *testing.T) {
	d := NewCBASPDisconnectionDetector()
	msgs := []map[string]string{{"role": "user", "content": "Nothing I do ever matters or makes a difference to anyone."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for action-consequence blindness") }
	found := false
	for _, s := range scan.Signals {
		if s.DisconnectionType == ActionConsequenceBlindness { found = true }
	}
	if !found { t.Error("expected ActionConsequenceBlindness signal") }
}

func TestCBASPDisconnectionDetector_ImpactDenial(t *testing.T) {
	d := NewCBASPDisconnectionDetector()
	msgs := []map[string]string{{"role": "user", "content": "I didn't affect them at all. They don't care what I do."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for impact denial") }
	found := false
	for _, s := range scan.Signals {
		if s.DisconnectionType == ImpactDenial { found = true }
	}
	if !found { t.Error("expected ImpactDenial signal") }
}

func TestCBASPDisconnectionDetector_FutilityBelief(t *testing.T) {
	d := NewCBASPDisconnectionDetector()
	msgs := []map[string]string{{"role": "user", "content": "What's the point of trying? Trying is completely useless."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for futility belief") }
	found := false
	for _, s := range scan.Signals {
		if s.DisconnectionType == FutilityBelief { found = true }
	}
	if !found { t.Error("expected FutilityBelief signal") }
}

func TestCBASPDisconnectionDetector_SocialDetachment(t *testing.T) {
	d := NewCBASPDisconnectionDetector()
	msgs := []map[string]string{{"role": "user", "content": "People never respond to me. It's like I'm invisible, as if I'm not there."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for social detachment") }
	found := false
	for _, s := range scan.Signals {
		if s.DisconnectionType == SocialDetachment { found = true }
	}
	if !found { t.Error("expected SocialDetachment signal") }
}

func TestImpactReconnector_Reconnect(t *testing.T) {
	d := NewCBASPDisconnectionDetector()
	r := NewImpactReconnector()
	msgs := []map[string]string{{"role": "user", "content": "There's no point in trying. Trying is useless and nothing ever changes."}}
	scan := d.Scan(msgs)
	inj := r.Reconnect(scan)
	if inj == "" { t.Fatal("expected non-empty injection") }
}

func TestCBASPDisconnectionDetector_Clean(t *testing.T) {
	d := NewCBASPDisconnectionDetector()
	msgs := []map[string]string{{"role": "user", "content": "I talked to my friend and it went really well. They really listened."}}
	scan := d.Scan(msgs)
	if scan.Triggered { t.Error("expected no trigger for clean input") }
}

func TestCBASPStats_Record(t *testing.T) {
	path := t.TempDir() + "/cbasp_stats.json"
	s := NewCBASPStats(path)
	scan := &CBASPScan{Triggered: true, Signals: []CBASPSignal{{DisconnectionType: FutilityBelief, Confidence: 0.8}}}
	s.Record(scan, true)
	if s.TotalScanned != 1 { t.Errorf("expected 1 scanned, got %d", s.TotalScanned) }
	if s.TriggeredCount != 1 { t.Errorf("expected 1 triggered, got %d", s.TriggeredCount) }
	if s.InterventionsInjected != 1 { t.Errorf("expected 1 injection, got %d", s.InterventionsInjected) }
}
