package goal

import (
	"fmt"
	"time"

	"github.com/google/uuid"
)

// ─────────────────────────────────────────────────────────────────────────────
// Status
// ─────────────────────────────────────────────────────────────────────────────

// GoalStatus represents the lifecycle state of a Goal or SubGoal.
type GoalStatus string

const (
	StatusPending   GoalStatus = "pending"
	StatusPlanning  GoalStatus = "planning"
	StatusRunning   GoalStatus = "running"
	StatusDone      GoalStatus = "done"
	StatusFailed    GoalStatus = "failed"
	StatusCancelled GoalStatus = "cancelled"
)

// ─────────────────────────────────────────────────────────────────────────────
// SubGoal — a node in the GoalDAG
// ─────────────────────────────────────────────────────────────────────────────

// SubGoal is a single node in the execution DAG.
// DependsOn lists SubGoal IDs that must be StatusDone before this node is ready.
type SubGoal struct {
	ID           string     `json:"id"`
	Description  string     `json:"description"`
	DependsOn    []string   `json:"depends_on"`
	Status       GoalStatus `json:"status"`
	Result       string     `json:"result,omitempty"`
	PADSessionID string     `json:"pad_session_id,omitempty"`
	StartedAt    time.Time  `json:"started_at,omitempty"`
	CompletedAt  time.Time  `json:"completed_at,omitempty"`
}

// ─────────────────────────────────────────────────────────────────────────────
// GoalDAG — the top-level goal with its execution graph
// ─────────────────────────────────────────────────────────────────────────────

// GoalDAG is the top-level goal record containing the sub-goal execution graph.
type GoalDAG struct {
	ID          string       `json:"id"`
	Objective   string       `json:"objective"`
	Context     string       `json:"context,omitempty"`
	Nodes       []*SubGoal   `json:"nodes"`
	Status      GoalStatus   `json:"status"`
	FinalAnswer string       `json:"final_answer,omitempty"`
	TickCount   int          `json:"tick_count"`
	MaxNodes    int          `json:"max_nodes"`
	CreatedAt   time.Time    `json:"created_at"`
	UpdatedAt   time.Time    `json:"updated_at"`
}

// NewGoalDAG creates a fresh GoalDAG with a UUID.
func NewGoalDAG(objective, context string, maxNodes int) *GoalDAG {
	if maxNodes < 1 || maxNodes > 10 {
		maxNodes = 10
	}
	return &GoalDAG{
		ID:        uuid.New().String(),
		Objective: objective,
		Context:   context,
		Status:    StatusPlanning,
		MaxNodes:  maxNodes,
		CreatedAt: time.Now().UTC(),
		UpdatedAt: time.Now().UTC(),
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// DAG traversal
// ─────────────────────────────────────────────────────────────────────────────

// ReadyNodes returns sub-goals that are pending and have all dependencies done.
func (g *GoalDAG) ReadyNodes() []*SubGoal {
	doneIDs := g.doneSet()
	var ready []*SubGoal
	for _, n := range g.Nodes {
		if n.Status != StatusPending {
			continue
		}
		if g.depsAllDone(n, doneIDs) {
			ready = append(ready, n)
		}
	}
	return ready
}

// Advance marks a node as done with its result and updates UpdatedAt.
func (g *GoalDAG) Advance(nodeID, result, padSessionID string) error {
	for _, n := range g.Nodes {
		if n.ID == nodeID {
			n.Status = StatusDone
			n.Result = result
			n.PADSessionID = padSessionID
			n.CompletedAt = time.Now().UTC()
			g.UpdatedAt = time.Now().UTC()
			return nil
		}
	}
	return fmt.Errorf("node %q not found", nodeID)
}

// FailNode marks a node as failed.
func (g *GoalDAG) FailNode(nodeID, reason string) error {
	for _, n := range g.Nodes {
		if n.ID == nodeID {
			n.Status = StatusFailed
			n.Result = reason
			n.CompletedAt = time.Now().UTC()
			g.UpdatedAt = time.Now().UTC()
			return nil
		}
	}
	return fmt.Errorf("node %q not found", nodeID)
}

// MarkRunning marks a node as running (dispatcher claimed it).
func (g *GoalDAG) MarkRunning(nodeID string) error {
	for _, n := range g.Nodes {
		if n.ID == nodeID {
			n.Status = StatusRunning
			n.StartedAt = time.Now().UTC()
			g.UpdatedAt = time.Now().UTC()
			return nil
		}
	}
	return fmt.Errorf("node %q not found", nodeID)
}

// IsComplete returns true when all nodes are done or failed.
func (g *GoalDAG) IsComplete() bool {
	for _, n := range g.Nodes {
		if n.Status == StatusPending || n.Status == StatusRunning || n.Status == StatusPlanning {
			return false
		}
	}
	return true
}

// HasFailures returns true if any node failed.
func (g *GoalDAG) HasFailures() bool {
	for _, n := range g.Nodes {
		if n.Status == StatusFailed {
			return true
		}
	}
	return false
}

// Cancel marks all pending/running nodes as cancelled and the goal itself.
func (g *GoalDAG) Cancel() {
	for _, n := range g.Nodes {
		if n.Status == StatusPending || n.Status == StatusRunning {
			n.Status = StatusCancelled
		}
	}
	g.Status = StatusCancelled
	g.UpdatedAt = time.Now().UTC()
}

// AccumulatedResults returns a concatenation of all done node results for acceptor evaluation.
func (g *GoalDAG) AccumulatedResults() string {
	var out string
	for _, n := range g.Nodes {
		if n.Status == StatusDone && n.Result != "" {
			out += "## " + n.Description + "\n" + n.Result + "\n\n"
		}
	}
	return out
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

func (g *GoalDAG) doneSet() map[string]bool {
	done := make(map[string]bool, len(g.Nodes))
	for _, n := range g.Nodes {
		if n.Status == StatusDone {
			done[n.ID] = true
		}
	}
	return done
}

func (g *GoalDAG) depsAllDone(node *SubGoal, doneIDs map[string]bool) bool {
	for _, dep := range node.DependsOn {
		if !doneIDs[dep] {
			return false
		}
	}
	return true
}
