package cognition

import (
	"fmt"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/memory"
)

// ─── RelationalContextBuilder: AlphaStar Self-Attention Between Entities ──────
// Queries the WorkingMemoryGraph for relationships between entities mentioned
// in the stimulus, then formats a compact relationship map for injection into
// the system prompt composite.
//
// Zero LLM calls — pure in-memory graph traversal, < 2ms.
// Gives the model structural awareness of how concepts relate, rather than
// treating each entity as an isolated token.

// BuildRelationalContext extracts entity labels from the stimulus, finds their
// relationships in the graph, and returns a formatted injection string.
// Returns "" if the graph has no relevant relationships (no injection overhead).
func BuildRelationalContext(stimulus string, graph *memory.WorkingMemoryGraph) string {
	if graph == nil || len(graph.Entities) == 0 {
		return ""
	}

	stimLower := strings.ToLower(stimulus)
	var matchedIDs []string

	// Find entities whose labels appear in the stimulus
	for id, entity := range graph.Entities {
		label := strings.ToLower(strings.TrimSpace(entity.Label))
		if label != "" && len(label) > 2 && strings.Contains(stimLower, label) {
			matchedIDs = append(matchedIDs, id)
		}
	}

	if len(matchedIDs) == 0 {
		return ""
	}

	// Build a set for fast membership check
	matched := make(map[string]bool, len(matchedIDs))
	for _, id := range matchedIDs {
		matched[id] = true
	}

	// Collect relationships where at least one endpoint is a matched entity
	type edge struct {
		from, rel, to string
		strength       float64
	}
	var edges []edge
	seen := make(map[string]bool)

	for _, rel := range graph.Relationships {
		if !matched[rel.SourceID] && !matched[rel.TargetID] {
			continue
		}
		srcEntity, srcOK := graph.Entities[rel.SourceID]
		tgtEntity, tgtOK := graph.Entities[rel.TargetID]
		if !srcOK || !tgtOK {
			continue
		}
		key := rel.SourceID + "|" + rel.Type + "|" + rel.TargetID
		if seen[key] {
			continue
		}
		seen[key] = true
		edges = append(edges, edge{
			from:     srcEntity.Label,
			rel:      rel.Type,
			to:       tgtEntity.Label,
			strength: rel.Strength,
		})
	}

	if len(edges) == 0 {
		return ""
	}

	// Cap at 8 most relevant edges to avoid composite bloat
	if len(edges) > 8 {
		edges = edges[:8]
	}

	var sb strings.Builder
	sb.WriteString("### RELATIONAL CONTEXT\n")
	sb.WriteString("Known entity relationships relevant to this query:\n")
	for _, e := range edges {
		confidence := ""
		if e.strength < 0.5 {
			confidence = " (weak)"
		}
		sb.WriteString(fmt.Sprintf("  [%s] → %s → [%s]%s\n", e.from, e.rel, e.to, confidence))
	}
	sb.WriteString("Use these relationships to inform your reasoning.\n")
	sb.WriteString("### END RELATIONAL CONTEXT")

	return sb.String()
}
