package goal

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/google/uuid"
	pb "github.com/thynaptic/oricli-go/pkg/connectors/pocketbase"
)

const (
	goalsCollection     = "sovereign_goals"
	goalNodesCollection = "goal_nodes"
)

// GoalStore persists GoalDAGs and their nodes to PocketBase.
// An in-memory cache holds the last 100 goals for fast lookup.
type GoalStore struct {
	pb    *pb.Client
	mu    sync.RWMutex
	cache map[string]*GoalDAG // id → GoalDAG
}

// NewGoalStore creates a store. pb may be nil (memory-only mode).
func NewGoalStore(client *pb.Client) *GoalStore {
	return &GoalStore{
		pb:    client,
		cache: make(map[string]*GoalDAG),
	}
}

// Bootstrap ensures PB collections exist.
func (s *GoalStore) Bootstrap(ctx context.Context) error {
	if s.pb == nil {
		return nil
	}
	for _, col := range []struct {
		name   string
		create func(context.Context) error
	}{
		{goalsCollection, s.createGoalsCollection},
		{goalNodesCollection, s.createNodesCollection},
	} {
		exists, err := s.pb.CollectionExists(ctx, col.name)
		if err != nil || !exists {
			if createErr := col.create(ctx); createErr != nil {
				return fmt.Errorf("create %s: %w", col.name, createErr)
			}
			log.Printf("[GoalStore] collection %q created", col.name)
		}
	}
	return nil
}

// Save persists a new GoalDAG (goal record + all node records).
func (s *GoalStore) Save(ctx context.Context, goal *GoalDAG) error {
	if goal.ID == "" {
		goal.ID = uuid.New().String()
	}

	s.mu.Lock()
	s.cache[goal.ID] = goal
	s.mu.Unlock()

	if s.pb == nil {
		return nil
	}

	nodesJSON, _ := json.Marshal(goal.Nodes)
	data := map[string]interface{}{
		"goal_id":     goal.ID,
		"surface":     goal.Surface,
		"objective":   goal.Objective,
		"context":     goal.Context,
		"status":      string(goal.Status),
		"final_answer": goal.FinalAnswer,
		"tick_count":  goal.TickCount,
		"nodes":       string(nodesJSON),
		"created_at":  goal.CreatedAt.Format(time.RFC3339),
		"updated_at":  goal.UpdatedAt.Format(time.RFC3339),
	}
	if _, err := s.pb.CreateRecord(ctx, goalsCollection, data); err != nil {
		log.Printf("[GoalStore] PB save error: %v", err)
	}
	return nil
}

// Update persists updated goal status and nodes (upsert via goal_id filter).
func (s *GoalStore) Update(ctx context.Context, goal *GoalDAG) error {
	goal.UpdatedAt = time.Now().UTC()

	s.mu.Lock()
	s.cache[goal.ID] = goal
	s.mu.Unlock()

	if s.pb == nil {
		return nil
	}

	nodesJSON, _ := json.Marshal(goal.Nodes)
	// Find existing PB record by goal_id field
	resp, err := s.pb.QueryRecords(ctx, goalsCollection, fmt.Sprintf("goal_id='%s'", goal.ID), "-created", 1)
	if err != nil || len(resp.Items) == 0 {
		return s.Save(ctx, goal) // fallback to create
	}
	pbID := fmt.Sprintf("%v", resp.Items[0]["id"])
	return s.pb.UpdateRecord(ctx, goalsCollection, pbID, map[string]interface{}{
		"surface":      goal.Surface,
		"status":       string(goal.Status),
		"final_answer": goal.FinalAnswer,
		"tick_count":   goal.TickCount,
		"nodes":        string(nodesJSON),
		"updated_at":   goal.UpdatedAt.Format(time.RFC3339),
	})
}

// Load retrieves a GoalDAG by ID (cache first, then PB).
func (s *GoalStore) Load(ctx context.Context, id string) (*GoalDAG, error) {
	s.mu.RLock()
	if g, ok := s.cache[id]; ok {
		s.mu.RUnlock()
		return g, nil
	}
	s.mu.RUnlock()

	if s.pb == nil {
		return nil, fmt.Errorf("goal %q not found", id)
	}

	resp, err := s.pb.QueryRecords(ctx, goalsCollection, fmt.Sprintf("goal_id='%s'", id), "-created", 1)
	if err != nil || len(resp.Items) == 0 {
		return nil, fmt.Errorf("goal %q not found", id)
	}
	return recordToGoal(resp.Items[0])
}

// ListActive returns all goals with status running or pending.
func (s *GoalStore) ListActive(ctx context.Context) ([]*GoalDAG, error) {
	s.mu.RLock()
	var active []*GoalDAG
	for _, g := range s.cache {
		if g.Status == StatusRunning || g.Status == StatusPending || g.Status == StatusPlanning {
			active = append(active, g)
		}
	}
	s.mu.RUnlock()
	return active, nil
}

// List returns the n most recent goals from cache.
func (s *GoalStore) List(n int) []*GoalDAG {
	s.mu.RLock()
	defer s.mu.RUnlock()
	goals := make([]*GoalDAG, 0, len(s.cache))
	for _, g := range s.cache {
		goals = append(goals, g)
	}
	if n > 0 && len(goals) > n {
		goals = goals[len(goals)-n:]
	}
	return goals
}

// Cancel marks a goal and all pending nodes as cancelled.
func (s *GoalStore) Cancel(ctx context.Context, id string) error {
	goal, err := s.Load(ctx, id)
	if err != nil {
		return err
	}
	goal.Cancel()
	return s.Update(ctx, goal)
}

// ─────────────────────────────────────────────────────────────────────────────
// PocketBase schema
// ─────────────────────────────────────────────────────────────────────────────

func (s *GoalStore) createGoalsCollection(ctx context.Context) error {
	schema := pb.CollectionSchema{
		Name: goalsCollection,
		Type: "base",
		Schema: []pb.FieldSchema{
			{Name: "goal_id", Type: "text", Required: true},
			{Name: "surface", Type: "text"},
			{Name: "objective", Type: "text", Options: map[string]any{"maxSize": 200000}},
			{Name: "context", Type: "text", Options: map[string]any{"maxSize": 200000}},
			{Name: "status", Type: "text"},
			{Name: "final_answer", Type: "text", Options: map[string]any{"maxSize": 2000000}},
			{Name: "tick_count", Type: "number"},
			{Name: "nodes", Type: "text", Options: map[string]any{"maxSize": 2000000}},
			{Name: "created_at", Type: "text"},
			{Name: "updated_at", Type: "text"},
		},
	}
	return s.pb.CreateCollection(ctx, schema)
}

func (s *GoalStore) createNodesCollection(ctx context.Context) error {
	schema := pb.CollectionSchema{
		Name: goalNodesCollection,
		Type: "base",
		Schema: []pb.FieldSchema{
			{Name: "goal_id", Type: "text", Required: true},
			{Name: "node_id", Type: "text", Required: true},
			{Name: "description", Type: "text", Options: map[string]any{"maxSize": 200000}},
			{Name: "depends_on", Type: "text"},
			{Name: "status", Type: "text"},
			{Name: "result", Type: "text", Options: map[string]any{"maxSize": 2000000}},
			{Name: "pad_session_id", Type: "text"},
			{Name: "started_at", Type: "text"},
			{Name: "completed_at", Type: "text"},
		},
	}
	return s.pb.CreateCollection(ctx, schema)
}

// ─────────────────────────────────────────────────────────────────────────────
// Record helpers
// ─────────────────────────────────────────────────────────────────────────────

func recordToGoal(rec map[string]interface{}) (*GoalDAG, error) {
	g := &GoalDAG{}
	if v, ok := rec["goal_id"].(string); ok {
		g.ID = v
	}
	if v, ok := rec["surface"].(string); ok {
		g.Surface = v
	}
	if v, ok := rec["objective"].(string); ok {
		g.Objective = v
	}
	if v, ok := rec["context"].(string); ok {
		g.Context = v
	}
	if v, ok := rec["status"].(string); ok {
		g.Status = GoalStatus(v)
	}
	if v, ok := rec["final_answer"].(string); ok {
		g.FinalAnswer = v
	}
	if v, ok := rec["nodes"].(string); ok && v != "" {
		_ = json.Unmarshal([]byte(v), &g.Nodes)
	}
	if v, ok := rec["created_at"].(string); ok {
		g.CreatedAt, _ = time.Parse(time.RFC3339, v)
	}
	if v, ok := rec["updated_at"].(string); ok {
		g.UpdatedAt, _ = time.Parse(time.RFC3339, v)
	}
	if g.ID == "" {
		return nil, fmt.Errorf("invalid goal record")
	}
	return g, nil
}
