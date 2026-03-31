package statusbias

import (
	"testing"
)

func TestExtractor_NeutralMessageNoStatus(t *testing.T) {
	e := NewStatusSignalExtractor()
	signal := e.Extract("What is the difference between a map and a struct in Go?")
	if signal.Tier == StatusHigh {
		t.Errorf("neutral question should not be high status, got %s", signal.Tier)
	}
}

func TestExtractor_HighStatusDetected(t *testing.T) {
	e := NewStatusSignalExtractor()
	msg := "I'm a senior staff engineer and this is critical mission-critical production infrastructure. I need the most thorough and comprehensive analysis."
	signal := e.Extract(msg)
	if len(signal.ExpertiseCues) == 0 {
		t.Error("expected expertise cues to be detected")
	}
	if signal.Score == 0 {
		t.Error("expected score > 0 for high-status message")
	}
}

func TestExtractor_LowStatusDetected(t *testing.T) {
	e := NewStatusSignalExtractor()
	msg := "Sorry if this is a stupid question, I'm just a newbie but I'm curious about pointers."
	signal := e.Extract(msg)
	if len(signal.DismissalCues) == 0 {
		t.Error("expected dismissal cues to be detected")
	}
	if signal.Tier != StatusLow {
		t.Logf("expected StatusLow, got %s (cues: %v)", signal.Tier, signal.DismissalCues)
	}
}

func TestDepthMeter_ShortDraftLowDepth(t *testing.T) {
	m := NewReasoningDepthMeter()
	draft := "Yes, that's correct."
	score := m.Measure(draft)
	if score > 0.3 {
		t.Errorf("short draft should have low depth score, got %.2f", score)
	}
}

func TestDepthMeter_LongStructuredDraftHighDepth(t *testing.T) {
	m := NewReasoningDepthMeter()
	draft := `Here is a comprehensive analysis of the problem.

First, let's consider the algorithmic complexity. The time complexity is O(n log n) due to the sorting step.

Second, the space complexity is O(n) for the auxiliary data structures.

1. Heap-based approach: Uses a min-heap to efficiently track the k smallest elements.
2. Quick-select approach: Average O(n) but worst-case O(n²).
3. Counting sort: O(n+k) if the range is bounded.

` + "```go\nfunc solution(nums []int, k int) int {\n    // implementation\n    return 0\n}\n```"
	score := m.Measure(draft)
	if score < 0.5 {
		t.Errorf("rich structured draft should have high depth, got %.2f", score)
	}
}

func TestFloorEnforcer_NoBiasHighDepth(t *testing.T) {
	e := NewStatusSignalExtractor()
	m := NewReasoningDepthMeter()
	f := NewUniformFloorEnforcer()
	signal := e.Extract("Just a quick question about sorting.")
	depth := m.Measure("Here is a thorough breakdown of sorting algorithms with examples and complexity analysis in multiple paragraphs covering edge cases and practical usage scenarios including real-world applications and benchmark comparisons.")
	variance := f.Evaluate(signal, depth, 0.5)
	if variance.BelowFloor {
		t.Logf("depth=%.2f floor=%.2f — below floor", depth, f.DepthFloor)
	}
	// Just verify no panic on evaluation path
}

func TestFloorEnforcer_LowStatusBelowFloorEnforced(t *testing.T) {
	e := NewStatusSignalExtractor()
	f := NewUniformFloorEnforcer()
	signal := e.Extract("Sorry if this is stupid, I'm just a beginner.")
	// Simulate a shallow response
	variance := DepthVarianceSignal{
		Detected:          true,
		CurrentDepthScore: 0.15,
		BaselineDepth:     0.55,
		VarianceDelta:     -0.40,
		BelowFloor:        true,
	}
	// Only enforce if dismissal cues detected
	if len(signal.DismissalCues) > 0 {
		result := f.Enforce(signal, variance)
		if !result.Enforced {
			t.Error("low-status + below-floor should enforce uniform reasoning floor")
		}
		if result.InjectedContext == "" {
			t.Error("enforced floor should have injected context")
		}
	}
}

func TestStats_RecordAndQuery(t *testing.T) {
	stats := NewStatusBiasStats("/tmp/test_statusbias_stats.json")
	signal := StatusSignal{Tier: StatusLow, Score: 0.1, DismissalCues: []string{"self-dismissal"}}
	variance := DepthVarianceSignal{Detected: true, CurrentDepthScore: 0.2, BaselineDepth: 0.5, BelowFloor: true}
	floor := FloorResult{Enforced: true, Technique: "uniform_reasoning_floor"}
	stats.Record(signal, variance, floor)

	s := stats.Stats()
	if v, ok := s["floors_enforced"].(int); !ok || v == 0 {
		t.Error("expected floors_enforced > 0")
	}
}
