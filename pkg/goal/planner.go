package goal

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"

	"github.com/google/uuid"
)

// GoalDistiller generates text via Ollama. Satisfied by *service.GenerationService.
type GoalDistiller interface {
	Generate(prompt string, options map[string]interface{}) (map[string]interface{}, error)
}

// GoalPlanner decomposes a high-level objective into a GoalDAG using an LLM.
// Hard limits: max 10 nodes, max 3 dependency levels.
type GoalPlanner struct {
	Distiller GoalDistiller
}

// NewGoalPlanner creates a planner.
func NewGoalPlanner(distiller GoalDistiller) *GoalPlanner {
	return &GoalPlanner{Distiller: distiller}
}

// Plan decomposes objective into a GoalDAG. Falls back to a single-node DAG on error.
func (p *GoalPlanner) Plan(ctx context.Context, objective, contextHint string, maxNodes int) (*GoalDAG, error) {
	if maxNodes < 1 || maxNodes > 10 {
		maxNodes = 10
	}

	dag := NewGoalDAG(objective, contextHint, maxNodes)

	if p.Distiller == nil {
		dag.Nodes = []*SubGoal{{
			ID:          uuid.New().String(),
			Description: objective,
			Status:      StatusPending,
		}}
		dag.Status = StatusRunning
		return dag, nil
	}

	prompt := p.buildPlanPrompt(objective, contextHint, maxNodes)
	raw, err := p.Distiller.Generate(prompt, map[string]interface{}{
		"temperature": 0.2,
		"num_predict": 768,
	})
	if err != nil {
		log.Printf("[GoalPlanner] LLM error, single-node fallback: %v", err)
		return p.singleNodeFallback(dag, objective), nil
	}

	text := extractGoalText(raw)
	nodes, err := parseGoalNodes(text)
	if err != nil || len(nodes) == 0 {
		log.Printf("[GoalPlanner] parse error (%v), single-node fallback", err)
		return p.singleNodeFallback(dag, objective), nil
	}

	// Enforce max nodes and max depth
	if len(nodes) > maxNodes {
		nodes = nodes[:maxNodes]
	}
	enforceDepthLimit(nodes, 3)

	dag.Nodes = nodes
	dag.Status = StatusRunning
	log.Printf("[GoalPlanner] planned %d nodes for objective: %.60s...", len(nodes), objective)
	return dag, nil
}

// ─────────────────────────────────────────────────────────────────────────────
// Internals
// ─────────────────────────────────────────────────────────────────────────────

func (p *GoalPlanner) buildPlanPrompt(objective, contextHint string, maxNodes int) string {
	ctx := ""
	if contextHint != "" {
		ctx = fmt.Sprintf("\nCONTEXT: %s", contextHint)
	}
	return fmt.Sprintf(`You are a goal decomposition planner for Oricli, a sovereign AI.

OBJECTIVE: %s%s
MAX SUB-GOALS: %d
MAX DEPENDENCY LEVELS: 3

Decompose this objective into a directed acyclic graph of sub-goals.
Rules:
- Each sub-goal must be self-contained and independently executable
- Dependencies must form a valid DAG (no cycles)
- Assign string IDs like "sg1", "sg2", etc.
- depends_on lists IDs that must complete before this node starts
- Max 3 levels of dependency depth
- Minimize nodes — prefer 3-6 for most objectives

Respond ONLY with valid JSON (no markdown):
{
  "nodes": [
    {"id": "sg1", "description": "specific sub-goal", "depends_on": []},
    {"id": "sg2", "description": "another sub-goal", "depends_on": ["sg1"]}
  ]
}`, objective, ctx, maxNodes)
}

func (p *GoalPlanner) singleNodeFallback(dag *GoalDAG, objective string) *GoalDAG {
	dag.Nodes = []*SubGoal{{
		ID:          uuid.New().String(),
		Description: objective,
		Status:      StatusPending,
	}}
	dag.Status = StatusRunning
	return dag
}

// ─────────────────────────────────────────────────────────────────────────────
// Parse helpers
// ─────────────────────────────────────────────────────────────────────────────

type rawPlan struct {
	Nodes []struct {
		ID          string   `json:"id"`
		Description string   `json:"description"`
		DependsOn   []string `json:"depends_on"`
	} `json:"nodes"`
}

func parseGoalNodes(text string) ([]*SubGoal, error) {
	text = strings.TrimSpace(text)
	if i := strings.Index(text, "{"); i > 0 {
		text = text[i:]
	}
	if i := strings.LastIndex(text, "}"); i >= 0 && i < len(text)-1 {
		text = text[:i+1]
	}

	var plan rawPlan
	if err := json.Unmarshal([]byte(text), &plan); err != nil {
		return nil, fmt.Errorf("unmarshal: %w", err)
	}

	// Build an ID → UUID map so we can resolve depends_on to real UUIDs
	idMap := make(map[string]string, len(plan.Nodes))
	for _, n := range plan.Nodes {
		idMap[n.ID] = uuid.New().String()
	}

	nodes := make([]*SubGoal, 0, len(plan.Nodes))
	for _, n := range plan.Nodes {
		if strings.TrimSpace(n.Description) == "" {
			continue
		}
		deps := make([]string, 0, len(n.DependsOn))
		for _, dep := range n.DependsOn {
			if realID, ok := idMap[dep]; ok {
				deps = append(deps, realID)
			}
		}
		nodes = append(nodes, &SubGoal{
			ID:          idMap[n.ID],
			Description: n.Description,
			DependsOn:   deps,
			Status:      StatusPending,
		})
	}
	return nodes, nil
}

// enforceDepthLimit trims depends_on for nodes that would exceed maxDepth levels.
func enforceDepthLimit(nodes []*SubGoal, maxDepth int) {
	// Build depth map
	idToNode := make(map[string]*SubGoal, len(nodes))
	for _, n := range nodes {
		idToNode[n.ID] = n
	}

	var depth func(id string, visited map[string]bool) int
	depth = func(id string, visited map[string]bool) int {
		if visited[id] {
			return 0
		}
		visited[id] = true
		n, ok := idToNode[id]
		if !ok || len(n.DependsOn) == 0 {
			return 0
		}
		max := 0
		for _, dep := range n.DependsOn {
			if d := depth(dep, visited); d > max {
				max = d
			}
		}
		return max + 1
	}

	for _, n := range nodes {
		if depth(n.ID, make(map[string]bool)) > maxDepth {
			n.DependsOn = nil // strip deps that exceed limit
		}
	}
}

func extractGoalText(raw map[string]interface{}) string {
	if raw == nil {
		return ""
	}
	for _, key := range []string{"text", "response", "content"} {
		if v, ok := raw[key]; ok {
			if s, ok := v.(string); ok {
				return s
			}
		}
	}
	if msg, ok := raw["message"].(map[string]interface{}); ok {
		if c, ok := msg["content"].(string); ok {
			return c
		}
	}
	return ""
}
