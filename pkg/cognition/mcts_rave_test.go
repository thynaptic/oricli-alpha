package cognition

import (
	"context"
	"math"
	"testing"
)

// ── raveTable unit tests ──────────────────────────────────────────────────────

func TestRaveTableUpdateAndEstimate(t *testing.T) {
	rt := newRaveTable()

	// No data yet.
	if _, ok := rt.estimate("foo"); ok {
		t.Fatal("expected no estimate for unseen answer")
	}

	rt.update("foo", 0.8)
	rt.update("foo", 0.6)

	est, ok := rt.estimate("foo")
	if !ok {
		t.Fatal("expected estimate after two updates")
	}
	want := (0.8 + 0.6) / 2
	if math.Abs(est-want) > 1e-9 {
		t.Errorf("estimate = %.4f, want %.4f", est, want)
	}
}

func TestRaveTableNormalisation(t *testing.T) {
	rt := newRaveTable()
	// Same answer with different whitespace/capitalisation should produce the same key.
	rt.update("  Hello World  ", 1.0)
	est, ok := rt.estimate("hello world")
	if !ok {
		t.Fatal("whitespace/case normalisation failed: no estimate")
	}
	if math.Abs(est-1.0) > 1e-9 {
		t.Errorf("estimate = %.4f, want 1.0", est)
	}
}

func TestRaveTableSize(t *testing.T) {
	rt := newRaveTable()
	rt.update("alpha", 0.5)
	rt.update("beta", 0.7)
	rt.update("alpha", 0.6) // duplicate key — should NOT add a new entry
	if rt.size() != 2 {
		t.Errorf("size = %d, want 2", rt.size())
	}
}

// ── raveBlend unit tests ──────────────────────────────────────────────────────

func TestRaveBlendAtZeroVisits(t *testing.T) {
	beta := raveBlend(0, 300)
	if math.Abs(beta-1.0) > 1e-9 {
		t.Errorf("β at N=0 = %.4f, want 1.0", beta)
	}
}

func TestRaveBlendDecreases(t *testing.T) {
	k := 300.0
	prev := raveBlend(0, k)
	for _, n := range []int{1, 10, 100, 1000} {
		b := raveBlend(n, k)
		if b >= prev {
			t.Errorf("β did not decrease at N=%d (prev=%.4f, cur=%.4f)", n, prev, b)
		}
		prev = b
	}
}

func TestRaveBlendDisabledAtZeroK(t *testing.T) {
	beta := raveBlend(0, 0)
	if beta != 0 {
		t.Errorf("β with k=0 = %.4f, want 0", beta)
	}
}

func TestRaveBlendMidpointAtExpectedVisits(t *testing.T) {
	// Solve for N where β = 0.5:
	//   0.5 = sqrt(k / (3N + k))  →  N = k
	k := 300.0
	n := int(k) // 300
	beta := raveBlend(n, k)
	if math.Abs(beta-0.5) > 0.01 {
		t.Errorf("β at N=k = %.4f, want ~0.5", beta)
	}
}

// ── integration tests ─────────────────────────────────────────────────────────

// TestRAVEBlendPushesQTowardHighRaveEstimate confirms that when a node has
// few real visits but the RAVE table has a high estimate, selectionScore
// returns a value higher than the node's raw average Q.
func TestRAVEBlendPushesQTowardHighRaveEstimate(t *testing.T) {
	eng := &MCTSEngine{}
	eng.rave = newRaveTable()

	// Record answer "X" as high-scoring in RAVE.
	eng.rave.update("X", 1.0)
	eng.rave.update("X", 1.0)

	parent := &ThoughtNode{Visits: 10}
	child := &ThoughtNode{
		Answer:   "X",
		Visits:   2,
		ValueSum: 0.2, // raw Q = 0.1 (poor)
		Prior:    0.5,
		Parent:   parent,
	}
	parent.Children = []*ThoughtNode{child}

	cfg := MCTSConfig{
		RAVEEquivalence: 300,
		PriorWeight:     1.0,
	}

	score := eng.selectionScore(child, parent, cfg)
	rawQ := child.AverageValue() // 0.1

	// RAVE estimate is 1.0, so blended Q should be > rawQ.
	if score <= rawQ {
		t.Errorf("expected RAVE to push score (%.4f) above raw Q (%.4f)", score, rawQ)
	}
}

// TestRAVETableSizeInResult ensures RAVETableSize is populated in MCTSResult
// when RAVEEquivalence > 0.
func TestRAVETableSizeInResult(t *testing.T) {
	eng := &MCTSEngine{
		Config: MCTSConfig{
			Iterations:      6,
			BranchFactor:    2,
			RolloutDepth:    1,
			PruneThreshold:  0.1,
			RAVEEquivalence: 300,
		},
		Callbacks: MCTSCallbacks{
			ProposeBranches: func(_ context.Context, _ string, n int) ([]string, error) {
				return []string{"answer one", "answer two"}[:min2(n, 2)], nil
			},
			EvaluatePath: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: 0.7, Candidate: c}, nil
			},
			AdversarialEval: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: 0.7, Candidate: c}, nil
			},
		},
	}

	result, err := eng.SearchV2(context.Background(), "test")
	if err != nil {
		t.Fatalf("SearchV2 error: %v", err)
	}
	if result.RAVETableSize == 0 {
		t.Error("expected RAVETableSize > 0 when RAVE is enabled and nodes were evaluated")
	}
}

// TestRAVEDisabledWhenEquivalenceIsZero ensures RAVE table stays nil and
// RAVETableSize == 0 when RAVEEquivalence is not set.
func TestRAVEDisabledWhenEquivalenceIsZero(t *testing.T) {
	eng := &MCTSEngine{
		Config: MCTSConfig{
			Iterations:     4,
			BranchFactor:   2,
			RolloutDepth:   1,
			PruneThreshold: 0.1,
			// RAVEEquivalence intentionally 0 (zero value = disabled)
		},
		Callbacks: MCTSCallbacks{
			ProposeBranches: func(_ context.Context, _ string, n int) ([]string, error) {
				return []string{"only one"}[:min2(n, 1)], nil
			},
			EvaluatePath: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: 0.8, Candidate: c}, nil
			},
			AdversarialEval: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: 0.8, Candidate: c}, nil
			},
		},
	}

	result, err := eng.SearchV2(context.Background(), "test")
	if err != nil {
		t.Fatalf("SearchV2 error: %v", err)
	}
	if result.RAVETableSize != 0 {
		t.Errorf("expected RAVETableSize == 0 when RAVE disabled, got %d", result.RAVETableSize)
	}
}

func min2(a, b int) int {
	if a < b {
		return a
	}
	return b
}

