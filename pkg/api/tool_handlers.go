package api

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type toolPlanRequest struct {
	Query string `json:"query"`
}

type executeToolPlanRequest struct {
	PlanID               string                   `json:"plan_id"`
	Query                string                   `json:"query"`
	Steps                []map[string]interface{} `json:"steps"`
	EstimatedTotalTime   float64                  `json:"estimated_total_time"`
	CanExecuteInParallel bool                     `json:"can_execute_in_parallel"`
	CreatedAt            int64                    `json:"created_at"`
}

func (s *ServerV2) handleListTools(c *gin.Context) {
	if s.ToolService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "tool service is not available"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"tools": s.ToolService.ListTools()})
}

func (s *ServerV2) handleCreateToolPlan(c *gin.Context) {
	if s.PlannerService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "planner service is not available"})
		return
	}

	var req toolPlanRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	plan, err := s.PlannerService.CreatePlan(req.Query)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, plan)
}

func (s *ServerV2) handleExecuteToolPlan(c *gin.Context) {
	if s.PlannerService == nil && s.ExecutePlanFunc == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "planner service is not available"})
		return
	}

	var req executeToolPlanRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	plan := &service.ToolCallingPlan{
		ID:                   req.PlanID,
		Query:                req.Query,
		EstimatedTotalTime:   req.EstimatedTotalTime,
		CanExecuteInParallel: req.CanExecuteInParallel,
		CreatedAt:            req.CreatedAt,
	}

	for index, rawStep := range req.Steps {
		step := service.PlanStep{
			ID:          stringValue(rawStep["id"]),
			Order:       intValue(rawStep["order"]),
			ToolName:    stringValue(rawStep["tool_name"]),
			Arguments:   mapValue(rawStep["arguments"]),
			Description: stringValue(rawStep["description"]),
			IsOptional:  boolValue(rawStep["is_optional"]),
		}
		if step.ID == "" {
			step.ID = fmt.Sprintf("step_%d", index+1)
		}
		if step.Order == 0 {
			step.Order = index + 1
		}
		if deps, ok := rawStep["depends_on"].([]interface{}); ok {
			for _, dep := range deps {
				if depStr, ok := dep.(string); ok && depStr != "" {
					step.DependsOn = append(step.DependsOn, depStr)
				}
			}
		}
		plan.Steps = append(plan.Steps, step)
	}

	var (
		result service.PlanExecutionResult
		err    error
	)
	if s.ExecutePlanFunc != nil {
		result, err = s.ExecutePlanFunc(plan)
	} else {
		result, err = s.PlannerService.ExecutePlan(plan)
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func stringValue(v interface{}) string {
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}

func intValue(v interface{}) int {
	switch n := v.(type) {
	case int:
		return n
	case int32:
		return int(n)
	case int64:
		return int(n)
	case float64:
		return int(n)
	default:
		return 0
	}
}

func boolValue(v interface{}) bool {
	if b, ok := v.(bool); ok {
		return b
	}
	return false
}

func mapValue(v interface{}) map[string]interface{} {
	if m, ok := v.(map[string]interface{}); ok {
		return m
	}
	return map[string]interface{}{}
}
