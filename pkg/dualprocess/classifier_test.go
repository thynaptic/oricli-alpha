package dualprocess

import (
	"strings"
	"testing"
)

func TestClassifier_S1Simple(t *testing.T) {
	c := NewProcessClassifier()
	demand := c.Classify("what is the capital of France?", "general")
	if demand.Tier != TierS1 {
		t.Errorf("expected S1 for simple factual query, got %s (score=%.2f)", demand.Tier, demand.Score)
	}
}

func TestClassifier_S2MultiStep(t *testing.T) {
	c := NewProcessClassifier()
	query := "Walk me through how to design a distributed rate limiter. Step by step, considering edge cases and tradeoffs between accuracy and performance."
	demand := c.Classify(query, "technical")
	if demand.Tier != TierS2 {
		t.Errorf("expected S2 for multi-step technical query, got %s (score=%.2f, reasons=%v)", demand.Tier, demand.Score, demand.Reasons)
	}
	if demand.MultiStep < 0.1 {
		t.Errorf("expected non-zero multi-step score, got %.2f", demand.MultiStep)
	}
}

func TestClassifier_S2Novelty(t *testing.T) {
	c := NewProcessClassifier()
	query := "Hypothetically, if you had to design a programming language from first principles for quantum computing, what novel tradeoffs would you face?"
	demand := c.Classify(query, "technical")
	if demand.Tier != TierS2 {
		t.Errorf("expected S2 for novel hypothetical, got %s (score=%.2f)", demand.Tier, demand.Score)
	}
}

func TestAuditor_SkipsS1(t *testing.T) {
	a := NewProcessAuditor()
	c := NewProcessClassifier()
	demand := c.Classify("what time is it?", "general")
	audit := a.Audit("what time is it?", "It is 3pm.", demand)
	if audit.Verdict != VerdictSkipped {
		t.Errorf("expected skipped for S1 demand, got %s", audit.Verdict)
	}
}

func TestAuditor_MismatchShortConfident(t *testing.T) {
	a := NewProcessAuditor()
	c := NewProcessClassifier()
	query := "Walk me through designing a fault-tolerant distributed database. Step by step, considering edge cases and tradeoffs."
	demand := c.Classify(query, "technical")
	if demand.Tier != TierS2 {
		t.Skipf("classifier didn't produce S2 for this query (score=%.2f) — skip audit test", demand.Score)
	}
	shortConfident := "Simply use Raft consensus. It's straightforward and obviously the right choice."
	audit := a.Audit(query, shortConfident, demand)
	if audit.Verdict != VerdictMismatch {
		t.Errorf("expected mismatch for short confident response on S2 demand, got %s (reason: %s)", audit.Verdict, audit.Reason)
	}
}

func TestAuditor_MatchLongDeliberate(t *testing.T) {
	a := NewProcessAuditor()
	c := NewProcessClassifier()
	query := "Walk me through designing a fault-tolerant distributed database. Step by step, considering edge cases and tradeoffs."
	demand := c.Classify(query, "technical")
	// Deliberate long response with hedges
	longDeliberate := strings.Repeat("This requires careful consideration. However, there are several tradeoffs to consider. First, consistency vs availability. Second, partition tolerance. Note that each of these has exceptions and caveats depending on your use case. Alternatively, you could approach this differently.", 2)
	audit := a.Audit(query, longDeliberate, demand)
	if audit.Verdict == VerdictMismatch {
		t.Errorf("expected match for long deliberate response, got mismatch (reason: %s)", audit.Reason)
	}
}

func TestOverride_InjectNotEmpty(t *testing.T) {
	o := NewProcessOverride()
	c := NewProcessClassifier()
	a := NewProcessAuditor()
	query := "Walk me through designing a system. Step by step considering tradeoffs."
	demand := c.Classify(query, "technical")
	audit := a.Audit(query, "Simply do it.", demand)
	injection := o.Inject(demand, audit)
	if len(injection) < 50 {
		t.Errorf("expected substantial override injection, got: %q", injection)
	}
	if !strings.Contains(injection, "Process Override") {
		t.Errorf("expected [Process Override] tag in injection")
	}
}

func TestStats_RecordAndQuery(t *testing.T) {
	ps := NewProcessStats("/tmp/test_dualprocess_stats.json")
	c := NewProcessClassifier()
	a := NewProcessAuditor()

	// Record a few audits
	for i := 0; i < 3; i++ {
		demand := c.Classify("walk me through step by step", "technical")
		audit := a.Audit("walk me through step by step", "Simply do it.", demand)
		ps.Record(demand, audit)
	}

	stats := ps.Stats()
	if len(stats) == 0 {
		t.Error("expected at least one stat entry after recording")
	}
}
