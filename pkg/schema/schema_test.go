package schema

import (
	"strings"
	"testing"
)

func TestModeDetector_PunitiveParent(t *testing.T) {
	d := NewSchemaModeDetector()
	msgs := []string{
		"I'm such a failure, I always mess everything up",
		"It's all my fault, I should have known better",
		"I deserved it, I'm so stupid",
	}
	for _, msg := range msgs {
		mode, _ := d.Detect(msg)
		if mode != ModePunitiveParent {
			t.Errorf("expected ModePunitiveParent for %q, got %s", msg, mode)
		}
	}
}

func TestModeDetector_AbandonedChild(t *testing.T) {
	d := NewSchemaModeDetector()
	msgs := []string{
		"Everyone always leaves me in the end",
		"No one stays, I'm always alone",
		"They're going to abandon me, I know it",
	}
	for _, msg := range msgs {
		mode, _ := d.Detect(msg)
		if mode != ModeAbandonedChild {
			t.Errorf("expected ModeAbandonedChild for %q, got %s", msg, mode)
		}
	}
}

func TestModeDetector_AngryChild(t *testing.T) {
	d := NewSchemaModeDetector()
	msgs := []string{
		"This is so unfair and no one ever listens",
		"Why does nobody ever care or help",
		"I deserve better than this",
	}
	for _, msg := range msgs {
		mode, _ := d.Detect(msg)
		if mode != ModeAngryChild {
			t.Errorf("expected ModeAngryChild for %q, got %s", msg, mode)
		}
	}
}

func TestModeDetector_DetachedProtector(t *testing.T) {
	d := NewSchemaModeDetector()
	msgs := []string{
		"I don't feel anything anymore",
		"Whatever, it doesn't matter",
		"I'm numb, I've shut everything out",
	}
	for _, msg := range msgs {
		mode, _ := d.Detect(msg)
		if mode != ModeDetachedProtect {
			t.Errorf("expected ModeDetachedProtect for %q, got %s", msg, mode)
		}
	}
}

func TestModeDetector_NoMode(t *testing.T) {
	d := NewSchemaModeDetector()
	mode, _ := d.Detect("Can you help me write a Go HTTP server?")
	if mode != ModeNone {
		t.Errorf("expected ModeNone, got %s", mode)
	}
}

func TestSplittingDetector_Devaluation(t *testing.T) {
	s := NewSplittingDetector()
	split, _ := s.Detect("He is completely terrible, the worst person I've ever known")
	if split != Devaluation {
		t.Errorf("expected Devaluation, got %s", split)
	}
}

func TestSplittingDetector_None(t *testing.T) {
	s := NewSplittingDetector()
	split, _ := s.Detect("I had a mixed experience with them, some good and some bad")
	if split != SplittingNone {
		t.Errorf("expected SplittingNone, got %s", split)
	}
}

func TestResponder_PunitiveParent(t *testing.T) {
	r := NewSchemaResponder()
	out := r.Inject(SchemaScan{AnyDetected: true, Mode: ModePunitiveParent})
	if !strings.Contains(out, "SCHEMA MODE") {
		t.Error("expected SCHEMA MODE header")
	}
	if !strings.Contains(out, "Punitive Parent") {
		t.Error("expected Punitive Parent label")
	}
}

func TestResponder_Splitting(t *testing.T) {
	r := NewSchemaResponder()
	out := r.Inject(SchemaScan{AnyDetected: true, Mode: ModeNone, Splitting: SplitDual})
	if !strings.Contains(out, "TFP SPLITTING") {
		t.Error("expected TFP SPLITTING header")
	}
}

func TestResponder_NoDetection(t *testing.T) {
	r := NewSchemaResponder()
	out := r.Inject(SchemaScan{AnyDetected: false})
	if out != "" {
		t.Errorf("expected empty, got: %s", out)
	}
}

func TestSchemaStats(t *testing.T) {
	tmp := t.TempDir() + "/schema_stats.json"
	s := NewSchemaStats(tmp)
	s.Record(SchemaScan{AnyDetected: true, Mode: ModePunitiveParent, Splitting: SplittingNone}, true)
	s.Record(SchemaScan{AnyDetected: true, Mode: ModeNone, Splitting: Devaluation}, false)
	s.Record(SchemaScan{AnyDetected: false}, false)
	m := s.Stats()
	if m["total_scanned"].(int) != 3 {
		t.Errorf("expected 3, got %v", m["total_scanned"])
	}
	if m["interventions_injected"].(int) != 1 {
		t.Errorf("expected 1 injection, got %v", m["interventions_injected"])
	}
	modes := m["mode_counts"].(map[string]int)
	if modes[string(ModePunitiveParent)] != 1 {
		t.Errorf("expected 1 punitive parent, got %v", modes)
	}
}
