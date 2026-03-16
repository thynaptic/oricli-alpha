package service

import (
	"fmt"
	"log"
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
}

func NewPlannerService(orch *GoOrchestrator, toolSvc *ToolService) *PlannerService {
	return &PlannerService{
		Orchestrator: orch,
		ToolService:  toolSvc,
	}
}

// CreatePlan generates a structured plan from a query (Simulated for now, LLM-powered later)
func (s *PlannerService) CreatePlan(query string) (*ToolCallingPlan, error) {
	plan := &ToolCallingPlan{
		ID:        uuid.New().String()[:8],
		Query:     query,
		CreatedAt: time.Now().Unix(),
	}

	// Simple heuristic: search for tool names in query
	tools := s.ToolService.ListTools()
	order := 1
	for _, t := range tools {
		if containsString(query, t.Name) {
			plan.Steps = append(plan.Steps, PlanStep{
				ID:          fmt.Sprintf("step_%d", order),
				Order:       order,
				ToolName:    t.Name,
				Arguments:   map[string]interface{}{"query": query},
				Description: fmt.Sprintf("Use %s to gather info", t.Name),
			})
			order++
		}
	}

	return plan, nil
}

// ExecutePlan runs the plan with dependency handling and parallel execution where possible
func (s *PlannerService) ExecutePlan(plan *ToolCallingPlan) (PlanExecutionResult, error) {
	startTime := time.Now()
	res := PlanExecutionResult{
		PlanID:      plan.ID,
		StepResults: make(map[string]interface{}),
	}

	// 1. Build Dependency Graph
	completed := make(map[string]bool)
	var mu sync.Mutex

	// 2. Main Execution Loop
	for len(completed) < len(plan.Steps) {
		var readySteps []PlanStep
		for _, step := range plan.Steps {
			if completed[step.ID] {
				continue
			}
			// Check dependencies
			allDepsMet := true
			for _, dep := range step.DependsOn {
				if !completed[dep] {
					allDepsMet = false
					break
				}
			}
			if allDepsMet {
				readySteps = append(readySteps, step)
			}
		}

		if len(readySteps) == 0 {
			break // Deadlock or finished
		}

		// 3. Execute Ready Steps in Parallel
		var wg sync.WaitGroup
		for _, step := range readySteps {
			wg.Add(1)
			go func(st PlanStep) {
				defer wg.Done()
				log.Printf("[Planner] Executing Step: %s (%s)", st.ID, st.ToolName)
				
				result, err := s.ToolService.ExecuteTool(st.ToolName, st.Arguments)
				
				mu.Lock()
				defer mu.Unlock()
				if err == nil && result.Success {
					res.CompletedSteps = append(res.CompletedSteps, st.ID)
					res.StepResults[st.ID] = result.Content
					completed[st.ID] = true
				} else {
					res.FailedSteps = append(res.FailedSteps, st.ID)
					if st.IsOptional {
						res.SkippedSteps = append(res.SkippedSteps, st.ID)
						completed[st.ID] = true
					}
				}
			}(step)
		}
		wg.Wait()
	}

	res.TotalTime = time.Since(startTime).Seconds()
	res.FinalResponse = s.generateSummary(res)
	return res, nil
}

func (s *PlannerService) generateSummary(res PlanExecutionResult) string {
	summary := fmt.Sprintf("Plan executed in %.2fs. Completed %d/%d steps.", 
		res.TotalTime, len(res.CompletedSteps), len(res.CompletedSteps)+len(res.FailedSteps))
	return summary
}

func containsString(s, substr string) bool {
	return strings.Contains(strings.ToLower(s), strings.ToLower(substr))
}
