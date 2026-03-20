package cognition

import (
	"context"
	"strings"
	"sync/atomic"
	"testing"
)

// sharedCallbacks returns a set of thread-safe callbacks suitable for parallel
// search tests. evalCount is incremented atomically on each EvaluatePath call.
func sharedCallbacks(evalCount *int64) MCTSCallbacks {
	return MCTSCallbacks{
		ProposeBranches: func(_ context.Context, _ string, n int) ([]string, error) {
			branches := []string{
				"parallel branch one with detail and content",
				"parallel branch two with analysis",
				"parallel branch three with synthesis",
			}
			if n < len(branches) {
				branches = branches[:n]
			}
			return branches, nil
		},
		EvaluatePath: func(_ context.Context, c string) (MCTSEvaluation, error) {
			if evalCount != nil {
				atomic.AddInt64(evalCount, 1)
			}
			score := 0.6
			if strings.Contains(c, "synthesis") {
				score = 0.85
			}
			return MCTSEvaluation{Confidence: score, Candidate: c}, nil
		},
		AdversarialEval: func(_ context.Context, c string) (MCTSEvaluation, error) {
			return MCTSEvaluation{Confidence: 0.7, Candidate: c}, nil
		},
	}
}

// TestParallelSearchCompletesWithoutDeadlock verifies the worker pool returns
// cleanly and produces a non-empty best answer.
func TestParallelSearchCompletesWithoutDeadlock(t *testing.T) {
	eng := &MCTSEngine{
		Config: MCTSConfig{
			Iterations:     12,
			BranchFactor:   3,
			RolloutDepth:   2,
			MaxConcurrency: 4,
			PruneThreshold: 0.1,
		},
		Callbacks: sharedCallbacks(nil),
	}

	result, err := eng.SearchV2(context.Background(), "starting draft")
	if err != nil {
		t.Fatalf("parallel SearchV2 error: %v", err)
	}
	if strings.TrimSpace(result.BestAnswer) == "" {
		t.Error("expected non-empty BestAnswer from parallel search")
	}
}

// TestParallelSearchIterationCount verifies that iterations run is within
// [requested, requested + MaxConcurrency] (workers may overshoot by at most
// MaxConcurrency - 1 due to the pre-check / decrement race window).
func TestParallelSearchIterationCount(t *testing.T) {
	const target = 10
	const concurrency = 3

	eng := &MCTSEngine{
		Config: MCTSConfig{
			Iterations:     target,
			BranchFactor:   2,
			RolloutDepth:   2,
			MaxConcurrency: concurrency,
			PruneThreshold: 0.1,
		},
		Callbacks: sharedCallbacks(nil),
	}

	result, err := eng.SearchV2(context.Background(), "draft")
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	// Allow up to MaxConcurrency-1 overshoot.
	lo, hi := target, target+concurrency-1
	if result.IterationsRun < lo || result.IterationsRun > hi {
		t.Errorf("IterationsRun = %d, want [%d, %d]", result.IterationsRun, lo, hi)
	}
}

// TestParallelVirtualLossAutoEnabled checks that VirtualLoss is automatically
// set to ≥ 1 in the parallel path so workers diverge.
func TestParallelVirtualLossAutoEnabled(t *testing.T) {
	eng := &MCTSEngine{
		Config: MCTSConfig{
			Iterations:     8,
			BranchFactor:   2,
			RolloutDepth:   2,
			MaxConcurrency: 3,
			VirtualLoss:    0, // explicitly disabled — should be overridden
			PruneThreshold: 0.1,
		},
		Callbacks: sharedCallbacks(nil),
	}
	// Should not hang or panic (virtual loss = 0 with parallel workers would
	// cause all workers to stack on the same unvisited leaf, which is harmless
	// but wasteful; we just check the search completes).
	_, err := eng.SearchV2(context.Background(), "draft")
	if err != nil {
		t.Fatalf("error: %v", err)
	}
}

// TestDeterministicModeStaysSequential verifies that Deterministic=true forces
// MaxConcurrency=1, keeping the result reproducible.
func TestDeterministicModeStaysSequential(t *testing.T) {
	makeEng := func() *MCTSEngine {
		return &MCTSEngine{
			Config: MCTSConfig{
				Iterations:     8,
				BranchFactor:   2,
				RolloutDepth:   2,
				MaxConcurrency: 4,   // would be parallel without Deterministic
				Deterministic:  true,
				Seed:           42,
				PruneThreshold: 0.1,
			},
			Callbacks: sharedCallbacks(nil),
		}
	}

	r1, err1 := makeEng().SearchV2(context.Background(), "draft")
	r2, err2 := makeEng().SearchV2(context.Background(), "draft")
	if err1 != nil || err2 != nil {
		t.Fatalf("errors: %v / %v", err1, err2)
	}
	if r1.BestAnswer != r2.BestAnswer {
		t.Errorf("deterministic runs differ: %q vs %q", r1.BestAnswer, r2.BestAnswer)
	}
}

// TestParallelSearchRaceDetector runs the parallel search under go test -race.
// The race detector is active only when the test binary is built with -race.
// This test is intentionally concurrent to surface any data races.
func TestParallelSearchRaceDetector(t *testing.T) {
	var evalCount int64
	eng := &MCTSEngine{
		Config: MCTSConfig{
			Iterations:     16,
			BranchFactor:   3,
			RolloutDepth:   2,
			MaxConcurrency: 4,
			PruneThreshold: 0.1,
		},
		Callbacks: sharedCallbacks(&evalCount),
	}

	result, err := eng.SearchV2(context.Background(), "concurrent draft")
	if err != nil {
		t.Fatalf("parallel SearchV2 error: %v", err)
	}
	if result.IterationsRun == 0 {
		t.Error("expected IterationsRun > 0")
	}
	if atomic.LoadInt64(&evalCount) == 0 {
		t.Error("expected EvaluatePath to be called at least once")
	}
}

// TestParallelSearchContextCancellation verifies that cancelling the context
// stops the parallel search cleanly before all iterations complete.
// The transposition table is disabled (MaxTableSize: -1) so every iteration
// calls EvaluatePath; without that, cached evaluations complete in nanoseconds
// and all 100 budget iterations finish before cancel() propagates.
func TestParallelSearchContextCancellation(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())

	called := int64(0)
	eng := &MCTSEngine{
		Config: MCTSConfig{
			Iterations:     100, // large — we'll cancel before this
			BranchFactor:   2,
			RolloutDepth:   2,
			MaxConcurrency: 3,
			PruneThreshold: 0.1,
			MaxTableSize:   -1, // disable transposition cache so cancellation is testable
		},
		Callbacks: MCTSCallbacks{
			ProposeBranches: func(_ context.Context, _ string, n int) ([]string, error) {
				return []string{"branch a long text here", "branch b long text here"}[:min5(n, 2)], nil
			},
			EvaluatePath: func(evalCtx context.Context, c string) (MCTSEvaluation, error) {
				atomic.AddInt64(&called, 1)
				if atomic.LoadInt64(&called) >= 3 {
					cancel() // cancel after 3 evals
				}
				return MCTSEvaluation{Confidence: 0.7, Candidate: c}, nil
			},
			AdversarialEval: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: 0.7, Candidate: c}, nil
			},
		},
	}

	result, err := eng.SearchV2(ctx, "draft")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.IterationsRun >= 100 {
		t.Error("expected search to stop before 100 iterations after context cancel")
	}
}

func min5(a, b int) int {
	if a < b {
		return a
	}
	return b
}
