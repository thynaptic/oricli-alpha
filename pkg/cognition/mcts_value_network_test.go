package cognition

import (
	"context"
	"strings"
	"testing"
)

func TestHeuristicValueNetwork_EmptyCandidate(t *testing.T) {
	vn := &HeuristicValueNetwork{}
	score, err := vn.Estimate(context.Background(), "some query", "")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if score != 0.0 {
		t.Fatalf("expected 0.0 for empty candidate, got %.4f", score)
	}
}

func TestHeuristicValueNetwork_ShortPenalty(t *testing.T) {
	vn := &HeuristicValueNetwork{}
	score, _ := vn.Estimate(context.Background(), "", "hi")
	if score >= 0.50 {
		t.Fatalf("expected penalty for very short candidate, got %.4f", score)
	}
}

func TestHeuristicValueNetwork_HighQualityAnswer(t *testing.T) {
	vn := &HeuristicValueNetwork{}
	// Well-structured answer with logical connectors, proper length, sentence end.
	candidate := "First, we identify the core issue. Because the system uses a monolithic " +
		"architecture, therefore we need to consider a phased decomposition strategy. " +
		"This approach reduces risk while delivering incremental value."
	score, err := vn.Estimate(context.Background(), "system architecture", candidate)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if score < 0.70 {
		t.Fatalf("expected high score for quality answer, got %.4f", score)
	}
}

func TestHeuristicValueNetwork_QueryRelevanceBoost(t *testing.T) {
	vn := &HeuristicValueNetwork{}
	query := "explain quantum entanglement particles"
	relevant := "Quantum entanglement occurs when particles become correlated in such a way that the quantum state of each cannot be described independently."
	irrelevant := "The weather today is quite pleasant with mild temperatures expected."

	scoreRelevant, _ := vn.Estimate(context.Background(), query, relevant)
	scoreIrrelevant, _ := vn.Estimate(context.Background(), query, irrelevant)

	if scoreRelevant <= scoreIrrelevant {
		t.Fatalf("relevant answer (%.4f) should score higher than irrelevant (%.4f)", scoreRelevant, scoreIrrelevant)
	}
}

func TestHeuristicValueNetwork_HedgePenalty(t *testing.T) {
	vn := &HeuristicValueNetwork{}
	hedged := "I think maybe the answer could possibly be related to the cache invalidation strategy."
	direct := "The cache invalidation strategy requires a time-to-live policy applied at the service boundary."

	scoreHedged, _ := vn.Estimate(context.Background(), "cache strategy", hedged)
	scoreDirect, _ := vn.Estimate(context.Background(), "cache strategy", direct)

	if scoreHedged >= scoreDirect {
		t.Fatalf("hedged answer (%.4f) should score lower than direct (%.4f)", scoreHedged, scoreDirect)
	}
}

func TestHeuristicValueNetwork_ScoresInRange(t *testing.T) {
	vn := &HeuristicValueNetwork{}
	cases := []string{
		"",
		"x",
		"The answer is 42.",
		strings.Repeat("word ", 300),
		"First, because therefore however thus since although.",
	}
	for _, c := range cases {
		score, err := vn.Estimate(context.Background(), "test query", c)
		if err != nil {
			t.Fatalf("unexpected error for candidate %q: %v", c[:min10(len(c), 20)], err)
		}
		if score < 0 || score > 1 {
			t.Fatalf("score %.4f out of [0,1] range for candidate %q", score, c[:min10(len(c), 20)])
		}
	}
}

func TestValueNetworkSkipsLLMForWeakCandidates(t *testing.T) {
	llmCalls := 0
	vn := &HeuristicValueNetwork{} // will score "bad" very low

	e := MCTSEngine{
		Config: MCTSConfig{
			Iterations:         6,
			BranchFactor:       2,
			RolloutDepth:       1,
			Strategy:           MCTSStrategyPUCT,
			MaxChildrenPerNode: 2,
			Deterministic:      true,
			Seed:               5,
			Query:              "explain cache invalidation",
			ValueNet: &ValueNetConfig{
				Network:       vn,
				AcceptBelow:   0.35,
				EscalateAbove: 0.60,
			},
		},
		Callbacks: MCTSCallbacks{
			ProposeBranches: func(_ context.Context, _ string, _ int) ([]string, error) {
				// One weak (short/vague), one strong (long, structured, on-topic).
				return []string{
					"bad",
					"Cache invalidation works by removing stale entries. Therefore, when a key expires, the system must fetch fresh data from the source.",
				}, nil
			},
			EvaluatePath: func(_ context.Context, c string) (MCTSEvaluation, error) {
				llmCalls++
				return MCTSEvaluation{Confidence: 0.8, Candidate: c}, nil
			},
			AdversarialEval: func(_ context.Context, c string) (MCTSEvaluation, error) {
				llmCalls++
				return MCTSEvaluation{Confidence: 0.75, Candidate: c}, nil
			},
		},
	}

	res, err := e.SearchV2(context.Background(), "explain cache invalidation")
	if err != nil {
		t.Fatalf("search failed: %v", err)
	}
	if res.ValueNetHits == 0 {
		t.Fatalf("expected at least one value network hit, got 0 (llmCalls=%d)", llmCalls)
	}
	// LLM calls should be strictly less than iterations*2 (full eval for all).
	maxFull := res.IterationsRun * 2
	if llmCalls >= maxFull {
		t.Fatalf("value network did not reduce LLM calls: got %d, max without VN = %d, vnHits=%d",
			llmCalls, maxFull, res.ValueNetHits)
	}
}

func TestValueNetworkEscalatesHighScorers(t *testing.T) {
	llmCalled := false
	escalateThreshold := 0.50 // low so our quality candidate definitely escalates

	vn := &HeuristicValueNetwork{}
	e := MCTSEngine{
		Config: MCTSConfig{
			Iterations:         4,
			BranchFactor:       1,
			RolloutDepth:       1,
			Strategy:           MCTSStrategyUCB1,
			MaxChildrenPerNode: 1,
			Deterministic:      true,
			Seed:               3,
			Query:              "cache invalidation strategy",
			ValueNet: &ValueNetConfig{
				Network:       vn,
				AcceptBelow:   0.20,
				EscalateAbove: escalateThreshold,
			},
		},
		Callbacks: MCTSCallbacks{
			ProposeBranches: func(_ context.Context, _ string, _ int) ([]string, error) {
				return []string{
					"Cache invalidation requires consistent TTL policies. Therefore, every service boundary must enforce expiry contracts to prevent stale data propagation.",
				}, nil
			},
			EvaluatePath: func(_ context.Context, c string) (MCTSEvaluation, error) {
				llmCalled = true
				return MCTSEvaluation{Confidence: 0.9, Candidate: c}, nil
			},
			AdversarialEval: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: 0.85, Candidate: c}, nil
			},
		},
	}

	_, err := e.SearchV2(context.Background(), "cache invalidation strategy")
	if err != nil {
		t.Fatalf("search failed: %v", err)
	}
	if !llmCalled {
		t.Fatal("expected high-scoring candidate to escalate to LLM eval, but LLM was never called")
	}
}

func TestValueNetworkDisabledWhenNil(t *testing.T) {
	llmCalls := 0
	e := MCTSEngine{
		Config: MCTSConfig{
			Iterations:   4,
			BranchFactor: 2,
			RolloutDepth: 1,
			Strategy:     MCTSStrategyUCB1,
			Deterministic: true,
			Seed:         1,
			ValueNet:     nil, // disabled
		},
		Callbacks: MCTSCallbacks{
			ProposeBranches: func(_ context.Context, _ string, _ int) ([]string, error) {
				return []string{"a", "b"}, nil
			},
			EvaluatePath: func(_ context.Context, c string) (MCTSEvaluation, error) {
				llmCalls++
				return MCTSEvaluation{Confidence: 0.5, Candidate: c}, nil
			},
			AdversarialEval: func(_ context.Context, c string) (MCTSEvaluation, error) {
				llmCalls++
				return MCTSEvaluation{Confidence: 0.5, Candidate: c}, nil
			},
		},
	}
	res, err := e.SearchV2(context.Background(), "draft")
	if err != nil {
		t.Fatalf("search failed: %v", err)
	}
	if res.ValueNetHits != 0 {
		t.Fatalf("expected 0 VN hits when ValueNet is nil, got %d", res.ValueNetHits)
	}
	if llmCalls == 0 {
		t.Fatal("expected LLM to be called when ValueNet is disabled")
	}
}

func min10(a, b int) int {
	if a < b {
		return a
	}
	return b
}
