package service

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
)

type PlanStep struct {
	ID               string                 `json:"id"`
	Order            int                    `json:"order"`
	ToolName         string                 `json:"tool_name"`
	Arguments        map[string]interface{} `json:"arguments"`
	Description      string                 `json:"description"`
	DependsOn        []string               `json:"depends_on"`
	IsOptional       bool                   `json:"is_optional"`
	FallbackStrategy string                 `json:"fallback_strategy,omitempty"`
}

type ToolCallingPlan struct {
	ID                   string     `json:"id"`
	Query                string     `json:"query"`
	Steps                []PlanStep `json:"steps"`
	EstimatedTotalTime   float64    `json:"estimated_total_time"`
	CanExecuteInParallel bool       `json:"can_execute_in_parallel"`
	CreatedAt            int64      `json:"created_at"`
}

type PlanExecutionResult struct {
	PlanID         string                 `json:"plan_id"`
	CompletedSteps []string               `json:"completed_steps"`
	FailedSteps    []string               `json:"failed_steps"`
	SkippedSteps   []string               `json:"skipped_steps"`
	FinalResponse  string                 `json:"final_response"`
	TotalTime      float64                `json:"total_time"`
	StepResults    map[string]interface{} `json:"step_results"`
}

type PlannerService struct {
	Orchestrator *GoOrchestrator
	ToolService  *ToolService
	GenService   *GenerationService
}

func NewPlannerService(orch *GoOrchestrator, toolSvc *ToolService, gen *GenerationService) *PlannerService {
	return &PlannerService{
		Orchestrator: orch,
		ToolService:  toolSvc,
		GenService:   gen,
	}
}

// --- ADVANCED PLANNING ---

func (s *PlannerService) CreateStrategicPlan(ctx context.Context, query string) (*ToolCallingPlan, error) {
	prompt := fmt.Sprintf("Create a strategic execution plan for: %s\nOutput JSON with steps, dependencies, and tools.", query)
	_, err := s.GenService.Generate(prompt, map[string]interface{}{"system": "Strategic Planner"})
	if err != nil { return nil, err }
	
	plan := &ToolCallingPlan{
		ID:        uuid.New().String()[:8],
		Query:     query,
		CreatedAt: time.Now().Unix(),
	}
	// (JSON parsing omitted, would populate plan.Steps here)
	return plan, nil
}

func (s *PlannerService) ChainPrompts(ctx context.Context, prompts []string) (string, error) {
	currentContext := ""
	for _, p := range prompts {
		res, err := s.GenService.Generate(p + "\nContext: " + currentContext, nil)
		if err != nil { return "", err }
		currentContext = res["text"].(string)
	}
	return currentContext, nil
}

// --- EXISTING METHODS (RESTORED) ---

func (s *PlannerService) CreatePlan(query string) (*ToolCallingPlan, error) {
	plan := &ToolCallingPlan{ID: uuid.New().String()[:8], Query: query, CreatedAt: time.Now().Unix()}
	tools := s.ToolService.ListTools()
	order := 1
	for _, t := range tools {
		if strings.Contains(strings.ToLower(query), strings.ToLower(t.Name)) {
			plan.Steps = append(plan.Steps, PlanStep{ID: fmt.Sprintf("step_%d", order), Order: order, ToolName: t.Name, Arguments: map[string]interface{}{"query": query}})
			order++
		}
	}
	return plan, nil
}

func (s *PlannerService) ExecutePlan(plan *ToolCallingPlan) (PlanExecutionResult, error) {
	startTime := time.Now()
	res := PlanExecutionResult{PlanID: plan.ID, StepResults: make(map[string]interface{})}
	completed := make(map[string]bool)
	var mu sync.Mutex
	for len(completed) < len(plan.Steps) {
		var readySteps []PlanStep
		for _, step := range plan.Steps {
			if completed[step.ID] { continue }
			allDepsMet := true
			for _, dep := range step.DependsOn { if !completed[dep] { allDepsMet = false; break } }
			if allDepsMet { readySteps = append(readySteps, step) }
		}
		if len(readySteps) == 0 { break }
		var wg sync.WaitGroup
		for _, step := range readySteps {
			wg.Add(1)
			go func(st PlanStep) {
				defer wg.Done()
				result, err := s.ToolService.ExecuteTool(context.Background(), st.ToolName, st.Arguments)
				mu.Lock()
				defer mu.Unlock()
				if err == nil && result.Success {
					res.CompletedSteps = append(res.CompletedSteps, st.ID)
					res.StepResults[st.ID] = result.Content
					completed[st.ID] = true
				} else {
					res.FailedSteps = append(res.FailedSteps, st.ID)
					if st.IsOptional { res.SkippedSteps = append(res.SkippedSteps, st.ID); completed[st.ID] = true }
				}
			}(step)
		}
		wg.Wait()
	}
	res.TotalTime = time.Since(startTime).Seconds()
	res.FinalResponse = fmt.Sprintf("Executed in %.2fs", res.TotalTime)
	return res, nil
}
