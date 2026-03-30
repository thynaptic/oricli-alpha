package service

import (
	"bufio"
	"context"
	"encoding/json"
	"os"
	"sync"
	"time"

	"github.com/google/uuid"
	pb "github.com/thynaptic/oricli-go/pkg/connectors/pocketbase"
)

type GoalStatus string

const (
	GoalPending   GoalStatus = "pending"
	GoalActive    GoalStatus = "active"
	GoalCompleted GoalStatus = "completed"
	GoalFailed    GoalStatus = "failed"
)

type Objective struct {
	ID         string                 `json:"id"`
	Goal       string                 `json:"goal"`
	Priority   int                    `json:"priority"`
	Status     GoalStatus             `json:"status"`
	CreatedAt  string                 `json:"created_at"`
	UpdatedAt  string                 `json:"updated_at"`
	Progress   float64                `json:"progress"`
	Metadata   map[string]interface{} `json:"metadata"`
	DependsOn  []string               `json:"depends_on,omitempty"`  // IDs of objectives that must complete first
	RetryCount int                    `json:"retry_count,omitempty"` // times re-queued after failure
	Result     string                 `json:"result,omitempty"`      // final output written on completion
	WebhookURL string                 `json:"webhook_url,omitempty"` // POST target on completed/failed
}

// IsReady returns true if all declared dependencies are in a completed state.
func (o *Objective) IsReady(all []Objective) bool {
	if len(o.DependsOn) == 0 {
		return true
	}
	done := make(map[string]bool, len(all))
	for _, obj := range all {
		if obj.Status == GoalCompleted {
			done[obj.ID] = true
		}
	}
	for _, dep := range o.DependsOn {
		if !done[dep] {
			return false
		}
	}
	return true
}

type GoalService struct {
	FilePath string
	PBClient *pb.Client
	mu       sync.Mutex
}

func NewGoalService(path string) *GoalService {
	if path == "" {
		path = "oricli_core/data/global_objectives.jsonl"
	}
	return &GoalService{FilePath: path}
}

func (s *GoalService) pbAvailable() bool {
	return s.PBClient != nil && s.PBClient.IsConfigured()
}

// pbItemToObjective converts a PocketBase response item map to an Objective.
func pbItemToObjective(item map[string]any) Objective {
	obj := Objective{}

	if v, ok := item["goal_id"].(string); ok {
		obj.ID = v
	}
	if v, ok := item["goal"].(string); ok {
		obj.Goal = v
	}
	if v, ok := item["status"].(string); ok {
		obj.Status = GoalStatus(v)
	}
	if v, ok := item["created"].(string); ok {
		obj.CreatedAt = v
	}
	if v, ok := item["updated"].(string); ok {
		obj.UpdatedAt = v
	}
	if v, ok := item["priority"]; v != nil && ok {
		switch n := v.(type) {
		case float64:
			obj.Priority = int(n)
		case int:
			obj.Priority = n
		}
	}
	if v, ok := item["progress"]; v != nil && ok {
		if n, ok := v.(float64); ok {
			obj.Progress = n
		}
	}
	if v, ok := item["retry_count"]; v != nil && ok {
		if n, ok := v.(float64); ok {
			obj.RetryCount = int(n)
		}
	}

	// depends_on comes back as interface{} from JSON — re-marshal to typed []string
	if raw, ok := item["depends_on"]; ok && raw != nil {
		b, _ := json.Marshal(raw)
		var deps []string
		if json.Unmarshal(b, &deps) == nil {
			obj.DependsOn = deps
		}
	}

	// metadata: same treatment
	if raw, ok := item["metadata"]; ok && raw != nil {
		b, _ := json.Marshal(raw)
		var meta map[string]interface{}
		if json.Unmarshal(b, &meta) == nil {
			obj.Metadata = meta
		}
	}

	if v, ok := item["result"].(string); ok {
		obj.Result = v
	}
	if v, ok := item["webhook_url"].(string); ok {
		obj.WebhookURL = v
	}

	return obj
}

func (s *GoalService) AddObjective(goal string, priority int, metadata map[string]interface{}) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	id := uuid.New().String()[:8]
	now := time.Now().Format(time.RFC3339)

	if s.pbAvailable() {
		depsJSON, _ := json.Marshal([]string{})
		metaJSON, _ := json.Marshal(metadata)
		_ = depsJSON
		_ = metaJSON
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_, err := s.PBClient.CreateRecord(ctx, "sovereign_goals", map[string]any{
			"goal_id":     id,
			"goal":        goal,
			"priority":    priority,
			"status":      string(GoalPending),
			"depends_on":  []string{},
			"retry_count": 0,
			"progress":    0.0,
			"metadata":    metadata,
		})
		if err == nil {
			return id, nil
		}
		// fall through to JSONL on PB error
	}

	obj := Objective{
		ID:        id,
		Goal:      goal,
		Priority:  priority,
		Status:    GoalPending,
		CreatedAt: now,
		UpdatedAt: now,
		Progress:  0.0,
		Metadata:  metadata,
	}

	data, err := json.Marshal(obj)
	if err != nil {
		return "", err
	}

	f, err := os.OpenFile(s.FilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return "", err
	}
	defer f.Close()

	if _, err := f.Write(append(data, '\n')); err != nil {
		return "", err
	}

	return id, nil
}

func (s *GoalService) ListObjectives(status string) ([]Objective, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.pbAvailable() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()

		filter := ""
		if status != "" {
			filter = "status='" + status + "'"
		}
		result, err := s.PBClient.QueryRecords(ctx, "sovereign_goals", filter, "-created", 500)
		if err == nil {
			objectives := make([]Objective, 0, len(result.Items))
			for _, item := range result.Items {
				objectives = append(objectives, pbItemToObjective(item))
			}
			return objectives, nil
		}
		// fall through to JSONL
	}

	f, err := os.Open(s.FilePath)
	if err != nil {
		if os.IsNotExist(err) {
			return []Objective{}, nil
		}
		return nil, err
	}
	defer f.Close()

	var objectives []Objective
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		var obj Objective
		if err := json.Unmarshal(scanner.Bytes(), &obj); err != nil {
			continue
		}
		if status == "" || string(obj.Status) == status {
			objectives = append(objectives, obj)
		}
	}

	return objectives, nil
}

// AddObjectiveWithDeps creates a new objective with explicit DAG dependencies.
func (s *GoalService) AddObjectiveWithDeps(goal string, priority int, metadata map[string]interface{}, dependsOn []string) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	id := uuid.New().String()[:8]
	now := time.Now().Format(time.RFC3339)

	if s.pbAvailable() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_, err := s.PBClient.CreateRecord(ctx, "sovereign_goals", map[string]any{
			"goal_id":     id,
			"goal":        goal,
			"priority":    priority,
			"status":      string(GoalPending),
			"depends_on":  dependsOn,
			"retry_count": 0,
			"progress":    0.0,
			"metadata":    metadata,
		})
		if err == nil {
			return id, nil
		}
		// fall through to JSONL
	}

	obj := Objective{
		ID:        id,
		Goal:      goal,
		Priority:  priority,
		Status:    GoalPending,
		CreatedAt: now,
		UpdatedAt: now,
		Progress:  0.0,
		Metadata:  metadata,
		DependsOn: dependsOn,
	}

	data, err := json.Marshal(obj)
	if err != nil {
		return "", err
	}

	f, err := os.OpenFile(s.FilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return "", err
	}
	defer f.Close()

	if _, err := f.Write(append(data, '\n')); err != nil {
		return "", err
	}

	return id, nil
}

func (s *GoalService) GetObjective(id string) (*Objective, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.pbAvailable() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		result, err := s.PBClient.QueryRecords(ctx, "sovereign_goals", "goal_id='"+id+"'", "", 1)
		if err == nil {
			if len(result.Items) > 0 {
				obj := pbItemToObjective(result.Items[0])
				return &obj, nil
			}
			return nil, nil
		}
		// fall through to JSONL
	}

	all, err := s.readAll()
	if err != nil {
		return nil, err
	}

	for _, obj := range all {
		if obj.ID == id {
			return &obj, nil
		}
	}

	return nil, nil
}

func (s *GoalService) UpdateObjective(id string, updates map[string]interface{}) (bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.pbAvailable() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		result, err := s.PBClient.QueryRecords(ctx, "sovereign_goals", "goal_id='"+id+"'", "", 1)
		if err == nil {
			if len(result.Items) == 0 {
				return false, nil
			}
			pbID, _ := result.Items[0]["id"].(string)
			updates["updated_at"] = time.Now().Format(time.RFC3339)
			if err := s.PBClient.UpdateRecord(ctx, "sovereign_goals", pbID, updates); err == nil {
				return true, nil
			}
		}
		// fall through to JSONL
	}

	all, err := s.readAll()
	if err != nil {
		return false, err
	}

	found := false
	for i, obj := range all {
		if obj.ID == id {
			data, _ := json.Marshal(obj)
			var m map[string]interface{}
			json.Unmarshal(data, &m)
			for k, v := range updates {
				m[k] = v
			}
			m["updated_at"] = time.Now().Format(time.RFC3339)

			var updatedObj Objective
			updatedData, _ := json.Marshal(m)
			json.Unmarshal(updatedData, &updatedObj)
			all[i] = updatedObj
			found = true
			break
		}
	}

	if found {
		return true, s.writeAll(all)
	}

	return false, nil
}

func (s *GoalService) DeleteObjective(id string) (bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.pbAvailable() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		result, err := s.PBClient.QueryRecords(ctx, "sovereign_goals", "goal_id='"+id+"'", "", 1)
		if err == nil {
			if len(result.Items) == 0 {
				return false, nil
			}
			pbID, _ := result.Items[0]["id"].(string)
			if err := s.PBClient.DeleteRecord(ctx, "sovereign_goals", pbID); err == nil {
				return true, nil
			}
		}
		// fall through to JSONL
	}

	all, err := s.readAll()
	if err != nil {
		return false, err
	}

	var updated []Objective
	found := false
	for _, obj := range all {
		if obj.ID == id {
			found = true
			continue
		}
		updated = append(updated, obj)
	}

	if found {
		return true, s.writeAll(updated)
	}

	return false, nil
}

func (s *GoalService) readAll() ([]Objective, error) {
	f, err := os.Open(s.FilePath)
	if err != nil {
		if os.IsNotExist(err) {
			return []Objective{}, nil
		}
		return nil, err
	}
	defer f.Close()

	var objectives []Objective
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		var obj Objective
		if err := json.Unmarshal(scanner.Bytes(), &obj); err != nil {
			continue
		}
		objectives = append(objectives, obj)
	}
	return objectives, nil
}

func (s *GoalService) writeAll(objs []Objective) error {
	f, err := os.Create(s.FilePath)
	if err != nil {
		return err
	}
	defer f.Close()

	for _, obj := range objs {
		data, _ := json.Marshal(obj)
		f.Write(append(data, '\n'))
	}
	return nil
}
