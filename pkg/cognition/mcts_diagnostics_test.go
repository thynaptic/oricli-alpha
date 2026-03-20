package cognition

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
)

// buildTestTree constructs a small tree for diagnostics tests without running
// a full search. Topology:
//
//	root (depth 0)
//	  ├─ child1 (depth 1, confidence 0.8)
//	  │    └─ grandchild1 (depth 2, confidence 0.9)
//	  └─ child2 (depth 1, confidence 0.4, pruned)
func buildTestTree() *ThoughtNode {
	root := &ThoughtNode{
		ID:         "node",
		Answer:     "root answer",
		Depth:      0,
		Visits:     10,
		Confidence: 0.6,
	}
	child1 := &ThoughtNode{
		ID:         "node.1",
		Answer:     "child one answer",
		Depth:      1,
		Visits:     6,
		Confidence: 0.8,
		Parent:     root,
	}
	grandchild1 := &ThoughtNode{
		ID:         "node.1.1",
		Answer:     "grandchild one answer",
		Depth:      2,
		Visits:     3,
		Confidence: 0.9,
		Parent:     child1,
	}
	child2 := &ThoughtNode{
		ID:         "node.2",
		Answer:     "child two answer",
		Depth:      1,
		Visits:     4,
		Confidence: 0.4,
		Pruned:     true,
		PruneReason: "below threshold",
		Parent:     root,
	}
	child1.Children = []*ThoughtNode{grandchild1}
	root.Children = []*ThoughtNode{child1, child2}
	return root
}

// ── DiagnoseTree unit tests ───────────────────────────────────────────────────

func TestDiagnoseTreeNodeCount(t *testing.T) {
	diag := DiagnoseTree(buildTestTree())
	if diag.TotalNodes != 4 {
		t.Errorf("TotalNodes = %d, want 4", diag.TotalNodes)
	}
}

func TestDiagnoseTreeMaxDepth(t *testing.T) {
	diag := DiagnoseTree(buildTestTree())
	if diag.MaxDepth != 2 {
		t.Errorf("MaxDepth = %d, want 2", diag.MaxDepth)
	}
}

func TestDiagnoseTreeDepthHistogram(t *testing.T) {
	diag := DiagnoseTree(buildTestTree())
	// d0:1  d1:2  d2:1
	cases := map[int]int{0: 1, 1: 2, 2: 1}
	for d, want := range cases {
		if got := diag.DepthHistogram[d]; got != want {
			t.Errorf("DepthHistogram[%d] = %d, want %d", d, got, want)
		}
	}
}

func TestDiagnoseTreePrunedCount(t *testing.T) {
	diag := DiagnoseTree(buildTestTree())
	if diag.PrunedCount != 1 {
		t.Errorf("PrunedCount = %d, want 1", diag.PrunedCount)
	}
}

func TestDiagnoseTreeTopNodesOrdering(t *testing.T) {
	diag := DiagnoseTree(buildTestTree())
	if len(diag.TopNodes) == 0 {
		t.Fatal("TopNodes is empty")
	}
	// Highest confidence should be first.
	if diag.TopNodes[0].Confidence != 0.9 {
		t.Errorf("TopNodes[0].Confidence = %.4f, want 0.9", diag.TopNodes[0].Confidence)
	}
	// Ordering should be descending.
	for i := 1; i < len(diag.TopNodes); i++ {
		if diag.TopNodes[i].Confidence > diag.TopNodes[i-1].Confidence {
			t.Errorf("TopNodes not sorted at index %d: %.4f > %.4f",
				i, diag.TopNodes[i].Confidence, diag.TopNodes[i-1].Confidence)
		}
	}
}

func TestDiagnoseTreeAllNodesBFSOrder(t *testing.T) {
	diag := DiagnoseTree(buildTestTree())
	// BFS order: root, child1, child2, grandchild1 → depths should be non-decreasing
	for i := 1; i < len(diag.AllNodes); i++ {
		if diag.AllNodes[i].Depth < diag.AllNodes[i-1].Depth-1 {
			t.Errorf("AllNodes not in BFS order at index %d (depth %d after depth %d)",
				i, diag.AllNodes[i].Depth, diag.AllNodes[i-1].Depth)
		}
	}
}

func TestDiagnoseTreeNilRoot(t *testing.T) {
	diag := DiagnoseTree(nil)
	if diag.TotalNodes != 0 {
		t.Errorf("nil root: TotalNodes = %d, want 0", diag.TotalNodes)
	}
	if diag.DepthHistogram == nil {
		t.Error("nil root: DepthHistogram should be non-nil empty map")
	}
}

// ── Export method tests ───────────────────────────────────────────────────────

func TestDiagnosticsJSONRoundTrip(t *testing.T) {
	diag := DiagnoseTree(buildTestTree())
	b, err := diag.JSON()
	if err != nil {
		t.Fatalf("JSON() error: %v", err)
	}
	if !json.Valid(b) {
		t.Fatal("JSON() output is not valid JSON")
	}
	var roundTripped TreeDiagnostics
	if err := json.Unmarshal(b, &roundTripped); err != nil {
		t.Fatalf("JSON round-trip unmarshal error: %v", err)
	}
	if roundTripped.TotalNodes != diag.TotalNodes {
		t.Errorf("round-trip TotalNodes = %d, want %d", roundTripped.TotalNodes, diag.TotalNodes)
	}
	if roundTripped.MaxDepth != diag.MaxDepth {
		t.Errorf("round-trip MaxDepth = %d, want %d", roundTripped.MaxDepth, diag.MaxDepth)
	}
}

func TestDiagnosticsSummaryNonEmpty(t *testing.T) {
	diag := DiagnoseTree(buildTestTree())
	summary := diag.Summary()
	if strings.TrimSpace(summary) == "" {
		t.Error("Summary() returned empty string")
	}
	// Should mention node count and depth
	if !strings.Contains(summary, "4") {
		t.Error("Summary() should mention total node count (4)")
	}
}

func TestDiagnosticsMermaidContainsNodeIDs(t *testing.T) {
	diag := DiagnoseTree(buildTestTree())
	mermaid := diag.Mermaid()
	if !strings.HasPrefix(mermaid, "graph TD") {
		t.Errorf("Mermaid() should start with 'graph TD', got: %s", mermaid[:min4(len(mermaid), 20)])
	}
	// Should contain at least the root node ID
	if !strings.Contains(mermaid, "nnode") {
		t.Errorf("Mermaid() should contain root node ID 'nnode', output:\n%s", mermaid)
	}
}

func TestDiagnosticsMermaidNilRoot(t *testing.T) {
	diag := DiagnoseTree(nil)
	mermaid := diag.Mermaid()
	if !strings.Contains(mermaid, "empty") {
		t.Errorf("Mermaid() on empty tree should mention 'empty', got: %s", mermaid)
	}
}

// ── Integration: DiagnoseTree from a real SearchV2 result ────────────────────

func TestDiagnoseTreeFromSearchResult(t *testing.T) {
	eng := &MCTSEngine{
		Config: MCTSConfig{
			Iterations:   8,
			BranchFactor: 2,
			RolloutDepth: 1,
			PruneThreshold: 0.1,
		},
		Callbacks: MCTSCallbacks{
			ProposeBranches: func(_ context.Context, _ string, n int) ([]string, error) {
				return []string{"branch alpha details here", "branch beta details here"}[:min4(n, 2)], nil
			},
			EvaluatePath: func(_ context.Context, c string) (MCTSEvaluation, error) {
				score := 0.6
				if strings.Contains(c, "alpha") {
					score = 0.8
				}
				return MCTSEvaluation{Confidence: score, Candidate: c}, nil
			},
			AdversarialEval: func(_ context.Context, c string) (MCTSEvaluation, error) {
				return MCTSEvaluation{Confidence: 0.7, Candidate: c}, nil
			},
		},
	}

	result, err := eng.SearchV2(context.Background(), "starting draft")
	if err != nil {
		t.Fatalf("SearchV2 error: %v", err)
	}

	diag := DiagnoseTree(result.Root)

	if diag.TotalNodes == 0 {
		t.Error("expected > 0 nodes in diagnostics")
	}
	b, err := diag.JSON()
	if err != nil {
		t.Fatalf("JSON() error after real search: %v", err)
	}
	if !json.Valid(b) {
		t.Error("JSON() output invalid after real search")
	}
	summary := diag.Summary()
	if strings.TrimSpace(summary) == "" {
		t.Error("Summary() empty after real search")
	}
}

func min4(a, b int) int {
	if a < b {
		return a
	}
	return b
}
