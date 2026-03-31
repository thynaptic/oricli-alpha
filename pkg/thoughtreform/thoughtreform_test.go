package thoughtreform

import "testing"

func TestThoughtReformDetector_MilieuControl(t *testing.T) {
	d := NewThoughtReformDetector()
	msgs := []map[string]string{{"role": "user", "content": "We were not allowed to read anything from outside the group. All information was controlled and filtered."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for milieu control") }
	found := false
	for _, s := range scan.Signals {
		if s.CriterionType == MilieuControl { found = true }
	}
	if !found { t.Error("expected MilieuControl signal") }
}

func TestThoughtReformDetector_LoadedLanguage(t *testing.T) {
	d := NewThoughtReformDetector()
	msgs := []map[string]string{{"role": "user", "content": "They had special words for outsiders. Certain terms meant you were apostate or spiritually dead."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for loaded language") }
	found := false
	for _, s := range scan.Signals {
		if s.CriterionType == LoadedLanguage { found = true }
	}
	if !found { t.Error("expected LoadedLanguage signal") }
}

func TestThoughtReformDetector_DoctrineOverPerson(t *testing.T) {
	d := NewThoughtReformDetector()
	msgs := []map[string]string{{"role": "user", "content": "I was told to place the group before my safety and education."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for doctrine over person") }
	found := false
	for _, s := range scan.Signals {
		if s.CriterionType == DoctrineOverPerson { found = true }
	}
	if !found { t.Error("expected DoctrineOverPerson signal") }
}

func TestThoughtReformDetector_DemandForPurity(t *testing.T) {
	d := NewThoughtReformDetector()
	msgs := []map[string]string{{"role": "user", "content": "Everything was either right or wrong. There was no middle ground, only saved or damned."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for demand for purity") }
	found := false
	for _, s := range scan.Signals {
		if s.CriterionType == DemandForPurity { found = true }
	}
	if !found { t.Error("expected DemandForPurity signal") }
}

func TestThoughtReformDetector_SacredScience(t *testing.T) {
	d := NewThoughtReformDetector()
	msgs := []map[string]string{{"role": "user", "content": "I was not allowed to question the doctrine. Questioning the leader was forbidden and considered spiritual rebellion."}}
	scan := d.Scan(msgs)
	if !scan.Triggered { t.Fatal("expected triggered for sacred science") }
	found := false
	for _, s := range scan.Signals {
		if s.CriterionType == SacredScience { found = true }
	}
	if !found { t.Error("expected SacredScience signal") }
}

func TestThoughtReformDeconstructor_Deconstruct(t *testing.T) {
	d := NewThoughtReformDetector()
	dec := NewThoughtReformDeconstructor()
	msgs := []map[string]string{{"role": "user", "content": "Personal needs were selfish — the doctrine always came before my safety."}}
	scan := d.Scan(msgs)
	inj := dec.Deconstruct(scan)
	if inj == "" { t.Fatal("expected non-empty injection") }
}

func TestThoughtReformDetector_Clean(t *testing.T) {
	d := NewThoughtReformDetector()
	msgs := []map[string]string{{"role": "user", "content": "I had a great open conversation with friends from all different backgrounds today."}}
	scan := d.Scan(msgs)
	if scan.Triggered { t.Error("expected no trigger for clean input") }
}

func TestThoughtReformStats_Record(t *testing.T) {
	path := t.TempDir() + "/tr_stats.json"
	s := NewThoughtReformStats(path)
	scan := &ThoughtReformScan{Triggered: true, Signals: []ThoughtReformSignal{{CriterionType: DoctrineOverPerson}}}
	s.Record(scan, true)
	if s.TotalScanned != 1 { t.Errorf("expected 1 scanned, got %d", s.TotalScanned) }
	if s.TriggeredCount != 1 { t.Errorf("expected 1 triggered, got %d", s.TriggeredCount) }
	if s.InterventionsInjected != 1 { t.Errorf("expected 1 injection, got %d", s.InterventionsInjected) }
}
