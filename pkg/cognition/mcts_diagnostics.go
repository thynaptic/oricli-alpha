package cognition

import (
	"encoding/json"
	"fmt"
	"math"
	"sort"
	"strings"
)

// NodeSnapshot is a serialisable, pointer-free snapshot of a ThoughtNode.
// Answers are truncated to 120 characters for readability.
type NodeSnapshot struct {
	ID          string  `json:"id"`
	Answer      string  `json:"answer"`
	Depth       int     `json:"depth"`
	Visits      int     `json:"visits"`
	Confidence  float64 `json:"confidence"`
	Score       float64 `json:"score"`
	Prior       float64 `json:"prior"`
	Pruned      bool    `json:"pruned,omitempty"`
	Terminal    bool    `json:"terminal,omitempty"`
	PruneReason string  `json:"prune_reason,omitempty"`
	EvalErr     string  `json:"eval_err,omitempty"`
	ChildCount  int     `json:"child_count"`
}

// TreeDiagnostics is a complete statistical snapshot of a completed search tree.
// Computed on demand from MCTSResult.Root via DiagnoseTree — zero runtime cost.
type TreeDiagnostics struct {
	TotalNodes      int                `json:"total_nodes"`
	MaxDepth        int                `json:"max_depth"`
	AvgBranchFactor float64            `json:"avg_branch_factor"`
	PrunedCount     int                `json:"pruned_count"`
	TerminalCount   int                `json:"terminal_count"`
	DepthHistogram  map[int]int        `json:"depth_histogram"`  // depth → node count
	AvgScoreByDepth map[int]float64    `json:"avg_score_by_depth"` // depth → mean confidence
	TopNodes        []NodeSnapshot     `json:"top_nodes"`        // top 10 by confidence
	AllNodes        []NodeSnapshot     `json:"all_nodes"`        // BFS order
}

// DiagnoseTree performs a BFS walk over the tree rooted at root and returns
// a fully populated TreeDiagnostics. Returns an empty struct when root is nil.
func DiagnoseTree(root *ThoughtNode) TreeDiagnostics {
	if root == nil {
		return TreeDiagnostics{
			DepthHistogram:  map[int]int{},
			AvgScoreByDepth: map[int]float64{},
		}
	}

	var all []NodeSnapshot
	depthCount := map[int]int{}
	depthScoreSum := map[int]float64{}
	maxDepth := 0
	prunedCount := 0
	terminalCount := 0

	// BFS queue
	queue := []*ThoughtNode{root}
	for len(queue) > 0 {
		node := queue[0]
		queue = queue[1:]

		snap := snapshotNode(node)
		all = append(all, snap)

		depthCount[node.Depth]++
		depthScoreSum[node.Depth] += node.Confidence
		if node.Depth > maxDepth {
			maxDepth = node.Depth
		}
		if node.Pruned {
			prunedCount++
		}
		if node.Terminal {
			terminalCount++
		}

		for _, child := range node.Children {
			if child != nil {
				queue = append(queue, child)
			}
		}
	}

	// Compute avg score per depth
	avgScore := make(map[int]float64, len(depthCount))
	for d, cnt := range depthCount {
		if cnt > 0 {
			avgScore[d] = math.Round(depthScoreSum[d]/float64(cnt)*10000) / 10000
		}
	}

	// Average branch factor: total children / non-leaf nodes
	totalChildren := 0
	nonLeafCount := 0
	for _, snap := range all {
		if snap.ChildCount > 0 {
			totalChildren += snap.ChildCount
			nonLeafCount++
		}
	}
	avgBranch := 0.0
	if nonLeafCount > 0 {
		avgBranch = math.Round(float64(totalChildren)/float64(nonLeafCount)*100) / 100
	}

	// Top 10 nodes by confidence (excluding root for clearer signal)
	sorted := make([]NodeSnapshot, len(all))
	copy(sorted, all)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].Confidence > sorted[j].Confidence
	})
	topN := 10
	if len(sorted) < topN {
		topN = len(sorted)
	}

	return TreeDiagnostics{
		TotalNodes:      len(all),
		MaxDepth:        maxDepth,
		AvgBranchFactor: avgBranch,
		PrunedCount:     prunedCount,
		TerminalCount:   terminalCount,
		DepthHistogram:  depthCount,
		AvgScoreByDepth: avgScore,
		TopNodes:        sorted[:topN],
		AllNodes:        all,
	}
}

// JSON serialises the diagnostics to indented JSON.
func (d TreeDiagnostics) JSON() ([]byte, error) {
	return json.MarshalIndent(d, "", "  ")
}

// Summary returns a compact human-readable plain-text report.
func (d TreeDiagnostics) Summary() string {
	var sb strings.Builder
	sb.WriteString("── Tree Diagnostics ─────────────────────────────────\n")
	fmt.Fprintf(&sb, "  Nodes:         %d total  (%d pruned, %d terminal)\n",
		d.TotalNodes, d.PrunedCount, d.TerminalCount)
	fmt.Fprintf(&sb, "  Depth:         max=%d  avg branch=%.2f\n",
		d.MaxDepth, d.AvgBranchFactor)

	// Depth histogram as a mini bar
	sb.WriteString("  Depth dist:    ")
	depths := make([]int, 0, len(d.DepthHistogram))
	for dep := range d.DepthHistogram {
		depths = append(depths, dep)
	}
	sort.Ints(depths)
	for _, dep := range depths {
		fmt.Fprintf(&sb, "d%d:%d ", dep, d.DepthHistogram[dep])
	}
	sb.WriteString("\n")

	sb.WriteString("  Top nodes:\n")
	for i, n := range d.TopNodes {
		ans := n.Answer
		if len(ans) > 60 {
			ans = ans[:57] + "..."
		}
		pruneTag := ""
		if n.Pruned {
			pruneTag = " [pruned]"
		}
		fmt.Fprintf(&sb, "    %2d. [%.2f] %s%s\n", i+1, n.Confidence, ans, pruneTag)
	}
	sb.WriteString("─────────────────────────────────────────────────────\n")
	return sb.String()
}

// Mermaid renders the top 20 nodes (by confidence) as a Mermaid flowchart.
// Node shapes encode status: parallelogram = pruned/terminal, default = normal.
// Edge labels show the confidence score.
func (d TreeDiagnostics) Mermaid() string {
	if len(d.AllNodes) == 0 {
		return "graph TD\n  empty[No nodes]\n"
	}

	// Build a quick lookup: ID → NodeSnapshot
	byID := make(map[string]NodeSnapshot, len(d.AllNodes))
	for _, n := range d.AllNodes {
		byID[n.ID] = n
	}

	// Select top 20 nodes + their parents (to keep graph connected)
	topN := 20
	if len(d.AllNodes) < topN {
		topN = len(d.AllNodes)
	}
	sorted := make([]NodeSnapshot, len(d.AllNodes))
	copy(sorted, d.AllNodes)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].Confidence > sorted[j].Confidence
	})
	selected := make(map[string]bool)
	for _, n := range sorted[:topN] {
		selected[n.ID] = true
		// Include parent so edges are valid
		parts := strings.Split(n.ID, ".")
		if len(parts) > 1 {
			parentID := strings.Join(parts[:len(parts)-1], ".")
			selected[parentID] = true
		}
	}

	// Build index: parentID → []childSnapshot for selected children
	type edge struct{ from, to, label string }
	var edges []edge
	for _, n := range d.AllNodes {
		if !selected[n.ID] {
			continue
		}
		if n.ID == "" {
			continue
		}
		parts := strings.Split(n.ID, ".")
		if len(parts) <= 1 {
			continue
		}
		parentID := strings.Join(parts[:len(parts)-1], ".")
		if selected[parentID] {
			label := fmt.Sprintf("%.2f", n.Confidence)
			edges = append(edges, edge{parentID, n.ID, label})
		}
	}

	var sb strings.Builder
	sb.WriteString("graph TD\n")

	// Node definitions
	for id := range selected {
		n, ok := byID[id]
		if !ok {
			continue
		}
		ans := n.Answer
		if len(ans) > 40 {
			ans = ans[:37] + "..."
		}
		// Escape special Mermaid characters
		ans = strings.ReplaceAll(ans, `"`, `'`)
		safeID := mermaidID(id)
		if n.Pruned || n.Terminal {
			fmt.Fprintf(&sb, "  %s[/\"%s\"/]\n", safeID, ans)
		} else {
			fmt.Fprintf(&sb, "  %s[\"%s\"]\n", safeID, ans)
		}
	}

	// Edges
	for _, e := range edges {
		fmt.Fprintf(&sb, "  %s -->|%s| %s\n", mermaidID(e.from), e.label, mermaidID(e.to))
	}

	return sb.String()
}

// snapshotNode converts a ThoughtNode to a NodeSnapshot.
func snapshotNode(n *ThoughtNode) NodeSnapshot {
	ans := n.Answer
	if len(ans) > 120 {
		ans = ans[:117] + "..."
	}
	return NodeSnapshot{
		ID:          n.IDOrDefault(),
		Answer:      ans,
		Depth:       n.Depth,
		Visits:      n.Visits,
		Confidence:  math.Round(n.Confidence*10000) / 10000,
		Score:       math.Round(n.Score*10000) / 10000,
		Prior:       math.Round(n.Prior*10000) / 10000,
		Pruned:      n.Pruned,
		Terminal:    n.Terminal,
		PruneReason: n.PruneReason,
		EvalErr:     n.LastEvalErr,
		ChildCount:  len(n.Children),
	}
}

// mermaidID converts a dot-separated node ID to a valid Mermaid node ID.
func mermaidID(id string) string {
	return "n" + strings.ReplaceAll(id, ".", "_")
}
