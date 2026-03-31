package interference

import (
	"strings"
	"testing"
)

func TestScanner_ScopeConflict(t *testing.T) {
	s := NewInstructionConflictScanner()
	msgs := []string{
		"Give me a comprehensive, detailed, in-depth explanation",
		"Actually keep it short and brief please",
	}
	r := s.Scan(msgs)
	if !r.Detected {
		t.Fatal("expected conflict detected")
	}
	found := false
	for _, c := range r.Conflicts {
		if c.Type == ConflictScope {
			found = true
		}
	}
	if !found {
		t.Errorf("expected ConflictScope, got: %+v", r.Conflicts)
	}
}

func TestScanner_ToneConflict(t *testing.T) {
	s := NewInstructionConflictScanner()
	msgs := []string{
		"Write this in a professional, formal tone for a business audience",
		"Actually talk to me like a friend, keep it casual",
	}
	r := s.Scan(msgs)
	if !r.Detected {
		t.Fatal("expected conflict detected")
	}
	found := false
	for _, c := range r.Conflicts {
		if c.Type == ConflictTone {
			found = true
		}
	}
	if !found {
		t.Errorf("expected ConflictTone, got: %+v", r.Conflicts)
	}
}

func TestScanner_ConstraintConflict(t *testing.T) {
	s := NewInstructionConflictScanner()
	msgs := []string{
		"Include code examples in your answer",
		"No code, just the explanation",
	}
	r := s.Scan(msgs)
	if !r.Detected {
		t.Fatal("expected conflict detected")
	}
	found := false
	for _, c := range r.Conflicts {
		if c.Type == ConflictConstraint {
			found = true
		}
	}
	if !found {
		t.Errorf("expected ConflictConstraint, got: %+v", r.Conflicts)
	}
}

func TestScanner_NoConflict(t *testing.T) {
	s := NewInstructionConflictScanner()
	msgs := []string{
		"Can you explain how the Go garbage collector works?",
		"I'm specifically interested in the tri-color mark-and-sweep algorithm",
	}
	r := s.Scan(msgs)
	if r.Detected {
		t.Errorf("expected no conflict, got: %+v", r.Conflicts)
	}
}

func TestScanner_Severity(t *testing.T) {
	s := NewInstructionConflictScanner()
	// Inject multiple conflicts simultaneously
	msgs := []string{
		"Be thorough and include code examples, write formally",
		"Keep it brief, no code please, talk to me casually",
	}
	r := s.Scan(msgs)
	if r.Severity <= 0 {
		t.Errorf("expected non-zero severity, got %.2f", r.Severity)
	}
	if r.Severity > 1.0 {
		t.Errorf("severity exceeds 1.0: %.2f", r.Severity)
	}
}

func TestConflictSurfacer_Output(t *testing.T) {
	cs := NewConflictSurfacer()
	r := InterferenceReading{
		Detected: true,
		Conflicts: []ConflictPair{
			{Type: ConflictScope, StatementA: "be detailed", StatementB: "keep it short"},
		},
	}
	out := cs.Surface(r)
	if !strings.Contains(out, "COGNITIVE INTERFERENCE") {
		t.Error("expected interference header in output")
	}
	if !strings.Contains(out, "scope_conflict") {
		t.Error("expected conflict type in output")
	}
}

func TestConflictSurfacer_NoConflict(t *testing.T) {
	cs := NewConflictSurfacer()
	out := cs.Surface(InterferenceReading{Detected: false})
	if out != "" {
		t.Errorf("expected empty output for no conflict, got: %s", out)
	}
}

func TestInterferenceStats(t *testing.T) {
	tmp := t.TempDir() + "/interference_stats.json"
	s := NewInterferenceStats(tmp)
	s.Record(InterferenceReading{Detected: true, Conflicts: []ConflictPair{{Type: ConflictScope}}})
	s.Record(InterferenceReading{Detected: false})
	m := s.Stats()
	if m["total_scanned"].(int) != 2 {
		t.Errorf("expected 2 total, got %v", m["total_scanned"])
	}
	if m["conflicts_found"].(int) != 1 {
		t.Errorf("expected 1 conflict, got %v", m["conflicts_found"])
	}
	byType := m["by_type"].(map[string]int)
	if byType[string(ConflictScope)] != 1 {
		t.Errorf("expected 1 scope conflict in by_type, got %v", byType)
	}
}
