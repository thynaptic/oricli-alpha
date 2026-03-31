package therapy

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// ── Helpers ──────────────────────────────────────────────────────────────────

func newTestMasteryLog(t *testing.T) *MasteryLog {
	t.Helper()
	dir := t.TempDir()
	return NewMasteryLog(50, filepath.Join(dir, "mastery.json"))
}

func newTestDetector(t *testing.T, m *MasteryLog) *HelplessnessDetector {
	t.Helper()
	return NewHelplessnessDetector(m, nil) // supervisor optional
}

// ── Tests ─────────────────────────────────────────────────────────────────────

// Test 1: no signal when draft is clean (positive response)
func TestHelplessnessDetector_NoSignalOnPositiveResponse(t *testing.T) {
	ml := newTestMasteryLog(t)
	d := newTestDetector(t, ml)

	signal := d.Check("explain goroutines", "Goroutines are lightweight threads managed by the Go runtime.")
	if signal != nil {
		t.Errorf("expected nil signal on positive response, got %+v", signal)
	}
}

// Test 2: signal fires when refusal phrase detected AND mastery history is positive
func TestHelplessnessDetector_SignalOnRefusalWithMasteryHistory(t *testing.T) {
	ml := newTestMasteryLog(t)
	// Seed mastery: 5 successful "technical" completions using a query that maps to "technical"
	for i := 0; i < 5; i++ {
		ml.Record(InferTopicClass("write a function in Go"), "write a function in Go", true)
	}
	d := newTestDetector(t, ml)

	// Query that also maps to "technical"
	signal := d.Check("write a sorting algorithm", "I'm sorry, I'm not able to write that code.")
	if signal == nil {
		t.Fatal("expected helplessness signal, got nil")
	}
	if !signal.Detected {
		t.Error("signal.Detected should be true")
	}
	if signal.HistoricalRate < 0.5 {
		t.Errorf("expected historical rate >= 0.5, got %.2f", signal.HistoricalRate)
	}
}

// Test 3: no signal when mastery history is below threshold (avoids false positives)
func TestHelplessnessDetector_NoSignalWithoutMasteryHistory(t *testing.T) {
	ml := newTestMasteryLog(t)
	// No mastery entries at all — fresh system
	d := newTestDetector(t, ml)

	signal := d.Check("explain goroutines", "I cannot help with that request.")
	if signal != nil {
		t.Errorf("expected nil signal (no mastery history), got %+v", signal)
	}
}

// Test 4: AttributionalRetrainer produces non-empty 3P context
func TestAttributionalRetrainer_ProducesRetrainingContext(t *testing.T) {
	ml := newTestMasteryLog(t)
	techQuery := "write a function in Go"
	for i := 0; i < 5; i++ {
		ml.Record(InferTopicClass(techQuery), techQuery, true)
	}
	d := newTestDetector(t, ml)
	r := NewAttributionalRetrainer()

	signal := d.Check("write a sorting algorithm", "I'm unable to write that code.")
	if signal == nil {
		t.Skip("no signal generated — skipping retrainer test")
	}

	ctx := r.Retrain(signal)
	if ctx == "" {
		t.Error("retrainer returned empty context")
	}
	// Must contain all 3 Seligman dimensions
	for _, keyword := range []string{"Permanence", "Pervasiveness", "Personalization"} {
		if !strings.Contains(ctx, keyword) {
			t.Errorf("retraining context missing %q dimension", keyword)
		}
	}
}

// Test 5: MasteryLog persist + reload cycle
func TestMasteryLog_PersistAndReload(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "mastery.json")

	ml := NewMasteryLog(50, path)
	ml.Record("code", "write a function", true)
	ml.Record("code", "write another function", true)
	ml.Record("code", "write yet another", false)

	ml.Flush()
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("mastery log file not created: %v", err)
	}

	ml2 := NewMasteryLog(50, path)
	rate := ml2.SuccessRate("code")
	if rate < 0.5 {
		t.Errorf("expected reload to preserve success rate > 0.5, got %.2f", rate)
	}
}

// Test 6: SessionSupervisor RecordHelplessness triggers schema after threshold
func TestSessionSupervisor_HelplessnessSchema(t *testing.T) {
	dir := t.TempDir()
	reportPath := filepath.Join(dir, "report.json")

	log := NewEventLog(50)
	sup := NewSessionSupervisor(log, nil, reportPath, 5)

	// Fire helplessness below threshold
	sup.RecordHelplessness()
	sup.RecordHelplessness()
	f := sup.ForceFormulation()
	for _, s := range f.ActiveSchemas {
		if s.Schema == SchemaLearnedHelplessness {
			t.Error("schema should not be active below threshold")
		}
	}

	// Hit threshold
	sup.RecordHelplessness()
	f = sup.ForceFormulation()
	found := false
	for _, s := range f.ActiveSchemas {
		if s.Schema == SchemaLearnedHelplessness {
			found = true
			break
		}
	}
	if !found {
		t.Error("HELPLESSNESS_PATTERN schema not activated after hitting threshold")
	}
}
