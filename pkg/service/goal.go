package service

import (
	"bufio"
	"encoding/json"
	"os"
	"sync"
	"time"

	"github.com/google/uuid"
)

type GoalStatus string

const (
	GoalPending   GoalStatus = "pending"
	GoalActive    GoalStatus = "active"
	GoalCompleted GoalStatus = "completed"
	GoalFailed    GoalStatus = "failed"
)

type Objective struct {
	ID        string                 `json:"id"`
	Goal      string                 `json:"goal"`
	Priority  int                    `json:"priority"`
	Status    GoalStatus             `json:"status"`
	CreatedAt string                 `json:"created_at"`
	UpdatedAt string                 `json:"updated_at"`
	Progress  float64                `json:"progress"`
	Metadata  map[string]interface{} `json:"metadata"`
}

type GoalService struct {
	FilePath string
	mu       sync.Mutex
}

func NewGoalService(path string) *GoalService {
	if path == "" {
		path = "oricli_core/data/global_objectives.jsonl"
	}
	return &GoalService{FilePath: path}
}

func (s *GoalService) AddObjective(goal string, priority int, metadata map[string]interface{}) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	id := uuid.New().String()[:8]
	now := time.Now().Format(time.RFC3339)
	
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

func (s *GoalService) UpdateObjective(id string, updates map[string]interface{}) (bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	all, err := s.readAll()
	if err != nil {
		return false, err
	}

	found := false
	for i, obj := range all {
		if obj.ID == id {
			// Apply updates
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
