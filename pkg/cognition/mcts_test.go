package cognition

import (
	"context"
	"strings"
	"testing"
)

func TestSearchV2PrefersHigherConfidenceCandidate(t *testing.T) {
	e := MCTSEngine{
		Config: MCTSConfig{
			Iterations:         15, // enough to explore all 3 root branches under progressive widening
			BranchFactor:       3,
			RolloutDepth:       2,
			Strategy:           MCTSStrategyPUCT,
			MaxChildrenPerNode: 3,
			MaxConcurrency:     2,
			Deterministic:      true,
			Seed:               11,
		},
		Callbacks: MCTSCallbacks{
			ProposeBranches: func(_ context.Context, _ string, _ int) ([]string, error) {
				return []string{"candidate-low", "candidate-best", "candidate-mid"}, nil
			},
			EvaluatePath: func(_ context.Context, candidate string) (MCTSEvaluation, error) {
				score := 0.2
				if strings.Contains(candidate, "mid") {
					score = 0.55
				}
				if strings.Contains(candidate, "best") {
					score = 0.9
				}
				return MCTSEvaluation{Confidence: score, Candidate: candidate, Prior: score}, nil
			},
			AdversarialEval: func(_ context.Context, candidate string) (MCTSEvaluation, error) {
				score := 0.2
				if strings.Contains(candidate, "mid") {
					score = 0.5
				}
				if strings.Contains(candidate, "best") {
					score = 0.85
				}
				return MCTSEvaluation{Confidence: score, Candidate: candidate, Prior: score}, nil
			},
		},
	}

	res, err := e.SearchV2(context.Background(), "draft")
	if err != nil {
		t.Fatalf("search v2 failed: %v", err)
	}
	if !strings.Contains(res.BestAnswer, "best") {
		t.Fatalf("expected best candidate, got %q", res.BestAnswer)
	}
	if res.Strategy != string(MCTSStrategyPUCT) {
		t.Fatalf("expected puct strategy, got %q", res.Strategy)
	}
	if res.IterationsRun == 0 {
		t.Fatalf("expected non-zero iterations")
	}
}

func TestSearchCompatibilityWrapper(t *testing.T) {
	e := MCTSEngine{
		Config: MCTSConfig{Iterations: 2, BranchFactor: 2, RolloutDepth: 1, Strategy: MCTSStrategyUCB1, Deterministic: true, Seed: 1},
		Callbacks: MCTSCallbacks{
			ProposeBranches: func(_ context.Context, _ string, _ int) ([]string, error) { return []string{"a", "b"}, nil },
			EvaluatePath: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: map[string]float64{"a": 0.2, "b": 0.8}[c], Candidate: c}, nil
			},
			AdversarialEval: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: map[string]float64{"a": 0.2, "b": 0.7}[c], Candidate: c}, nil
			},
		},
	}
	best, ok, root, err := e.Search(context.Background(), "draft")
	if err != nil {
		t.Fatalf("search failed: %v", err)
	}
	if !ok || strings.TrimSpace(best) == "" {
		t.Fatalf("expected non-empty winning answer")
	}
	if root == nil {
		t.Fatalf("expected root node")
	}
}

func TestProgressiveWideningRespectsMaxChildren(t *testing.T) {
	e := MCTSEngine{
		Config: MCTSConfig{BranchFactor: 6, MaxChildrenPerNode: 2, WideningAlpha: 0.8, WideningK: 4, Strategy: MCTSStrategyPUCT},
		Callbacks: MCTSCallbacks{
			ProposeBranches: func(_ context.Context, _ string, _ int) ([]string, error) {
				return []string{"one", "two", "three", "four"}, nil
			},
			EvaluatePath: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: 0.5, Candidate: c}, nil
			},
			AdversarialEval: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: 0.5, Candidate: c}, nil
			},
		},
	}
	cfg := e.normalizedConfig()
	node := &ThoughtNode{ID: "root", Answer: "seed", Visits: 100}
	for i := 0; i < 10; i++ {
		if !shouldExpand(node, cfg) {
			break
		}
		_ = e.expandOneChild(context.Background(), node, cfg)
	}
	if len(node.Children) > cfg.MaxChildrenPerNode {
		t.Fatalf("expected <= %d children, got %d", cfg.MaxChildrenPerNode, len(node.Children))
	}
}

func TestTranspositionTableAvoidsDuplicateEvals(t *testing.T) {
	evalCalls := 0
	advCalls := 0
	// ProposeBranches always returns the same two candidates regardless of
	// which node is being expanded — this guarantees identical answer text
	// appears across multiple tree branches, exercising the table.
	e := MCTSEngine{
		Config: MCTSConfig{
			Iterations:         8,
			BranchFactor:       2,
			RolloutDepth:       2,
			MaxChildrenPerNode: 2,
			Strategy:           MCTSStrategyPUCT,
			Deterministic:      true,
			Seed:               42,
		},
		Callbacks: MCTSCallbacks{
			ProposeBranches: func(_ context.Context, _ string, _ int) ([]string, error) {
				return []string{"shared-answer-alpha", "shared-answer-beta"}, nil
			},
			EvaluatePath: func(_ context.Context, c string) (MCTSEvaluation, error) {
				evalCalls++
				score := 0.6
				if strings.Contains(c, "beta") {
					score = 0.4
				}
				return MCTSEvaluation{Confidence: score, Candidate: c, Prior: score}, nil
			},
			AdversarialEval: func(_ context.Context, c string) (MCTSEvaluation, error) {
				advCalls++
				score := 0.55
				if strings.Contains(c, "beta") {
					score = 0.35
				}
				return MCTSEvaluation{Confidence: score, Candidate: c}, nil
			},
		},
	}

	res, err := e.SearchV2(context.Background(), "draft")
	if err != nil {
		t.Fatalf("search failed: %v", err)
	}
	if res.TranspositionHits == 0 {
		t.Fatalf("expected at least one transposition hit with repeated candidate text, got 0 (evalCalls=%d)", evalCalls)
	}
	// Every hit saved 2 LLM calls (EvaluatePath + AdversarialEval).
	// Verify the total LLM calls are strictly less than iterations*2.
	totalLLMCalls := evalCalls + advCalls
	maxWithoutCache := res.IterationsRun * 2
	if totalLLMCalls >= maxWithoutCache {
		t.Fatalf("transposition table did not reduce LLM calls: got %d, max without cache = %d, hits = %d",
			totalLLMCalls, maxWithoutCache, res.TranspositionHits)
	}
}

func TestTranspositionTableDisabledWhenNegativeOne(t *testing.T) {
	e := MCTSEngine{
		Config: MCTSConfig{
			Iterations:   4,
			BranchFactor: 2,
			RolloutDepth: 1,
			Strategy:     MCTSStrategyUCB1,
			Deterministic: true,
			Seed:         7,
			MaxTableSize: -1, // disabled
		},
		Callbacks: MCTSCallbacks{
			ProposeBranches: func(_ context.Context, _ string, _ int) ([]string, error) {
				return []string{"x", "y"}, nil
			},
			EvaluatePath: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: 0.5, Candidate: c}, nil
			},
			AdversarialEval: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: 0.5, Candidate: c}, nil
			},
		},
	}
	res, err := e.SearchV2(context.Background(), "draft")
	if err != nil {
		t.Fatalf("search failed: %v", err)
	}
	if res.TranspositionHits != 0 {
		t.Fatalf("expected 0 transposition hits when table is disabled, got %d", res.TranspositionHits)
	}
}

func TestTerminalNodeBlocksExpansion(t *testing.T) {
	// Terminal=true returned from eval should prevent the node from expanding.
	e := MCTSEngine{
		Config: MCTSConfig{
			Iterations:         6,
			BranchFactor:       3,
			RolloutDepth:       3,
			MaxChildrenPerNode: 3,
			Strategy:           MCTSStrategyPUCT,
			Deterministic:      true,
			Seed:               99,
		},
		Callbacks: MCTSCallbacks{
			ProposeBranches: func(_ context.Context, _ string, _ int) ([]string, error) {
				return []string{"branch-a", "branch-b", "branch-c"}, nil
			},
			EvaluatePath: func(_ context.Context, c string) (MCTSEvaluation, error) {
				// Mark branch-a as terminal.
				return MCTSEvaluation{Confidence: 0.7, Candidate: c, Terminal: c == "branch-a"}, nil
			},
			AdversarialEval: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: 0.6, Candidate: c}, nil
			},
		},
	}
	res, err := e.SearchV2(context.Background(), "root draft")
	if err != nil {
		t.Fatalf("search failed: %v", err)
	}
	if res.Root == nil {
		t.Fatal("expected root node")
	}
	// Walk the tree and confirm no node with Answer=="branch-a" has children.
	var checkTerminal func(n *ThoughtNode)
	checkTerminal = func(n *ThoughtNode) {
		if n == nil {
			return
		}
		if n.Answer == "branch-a" && len(n.Children) > 0 {
			t.Errorf("terminal node %q should have no children, got %d", n.Answer, len(n.Children))
		}
		for _, c := range n.Children {
			checkTerminal(c)
		}
	}
	checkTerminal(res.Root)
}
