package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/service"
)

func TestHandleExecuteToolPlanReturnsBrowserSpecificFields(t *testing.T) {
	gin.SetMode(gin.TestMode)

	server := &ServerV2{
		ExecutePlanFunc: func(plan *service.ToolCallingPlan) (service.PlanExecutionResult, error) {
			if plan.Query != "remember this login" {
				t.Fatalf("expected query to round-trip, got %q", plan.Query)
			}
			if len(plan.Steps) != 1 || plan.Steps[0].ToolName != "browser_save_state" {
				t.Fatalf("expected browser_save_state step, got %#v", plan.Steps)
			}
			return service.PlanExecutionResult{
				PlanID:              plan.ID,
				CompletedSteps:      []string{"step_1"},
				Bindings:            map[string]interface{}{"state_name": "app_example_com_login", "session_id": "sess_keep"},
				SavedStateName:      "app_example_com_login",
				ActiveSessionID:     "sess_keep",
				AutoClosedSessionID: "sess_closed",
				FinalResponse:       `Executed in 1.00s; saved state "app_example_com_login"`,
				StepResults:         map[string]interface{}{"step_1": `{"ok":true,"state_name":"app_example_com_login"}`},
			}, nil
		},
	}

	router := gin.New()
	router.POST("/v1/tools/execute-plan", server.handleExecuteToolPlan)

	body := map[string]interface{}{
		"plan_id":                 "plan_test",
		"query":                   "remember this login",
		"estimated_total_time":    4,
		"can_execute_in_parallel": false,
		"created_at":              1775502261,
		"steps": []map[string]interface{}{
			{
				"id":          "step_1",
				"order":       1,
				"tool_name":   "browser_save_state",
				"arguments":   map[string]interface{}{"session_id": "$session_id", "state_name": "app_example_com_login"},
				"description": "Persist the current browser storage state for reuse.",
			},
		},
	}

	payload, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/v1/tools/execute-plan", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d with body %s", rec.Code, rec.Body.String())
	}

	var response service.PlanExecutionResult
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}

	if response.SavedStateName != "app_example_com_login" {
		t.Fatalf("expected saved_state_name, got %q", response.SavedStateName)
	}
	if response.ActiveSessionID != "sess_keep" {
		t.Fatalf("expected active_session_id, got %q", response.ActiveSessionID)
	}
	if response.AutoClosedSessionID != "sess_closed" {
		t.Fatalf("expected auto_closed_session_id, got %q", response.AutoClosedSessionID)
	}
	if response.Bindings["state_name"] != "app_example_com_login" {
		t.Fatalf("expected bindings.state_name, got %#v", response.Bindings["state_name"])
	}
}

func TestHandleCreateToolPlanBuildsRememberedLoginSaveStateStep(t *testing.T) {
	gin.SetMode(gin.TestMode)

	toolSvc := service.NewToolService(nil)
	service.RegisterBrowserTools(toolSvc)

	server := &ServerV2{
		PlannerService: service.NewPlannerService(nil, toolSvc, nil),
	}

	router := gin.New()
	router.POST("/v1/tools/plan", server.handleCreateToolPlan)

	body := map[string]interface{}{
		"query": `Open https://app.example.com/login, fill "Email" with "bro@ori.test", click "Sign in" button, and remember this login for reuse later`,
	}

	payload, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/v1/tools/plan", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d with body %s", rec.Code, rec.Body.String())
	}

	var response service.ToolCallingPlan
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}

	if len(response.Steps) == 0 {
		t.Fatalf("expected planned steps, got none")
	}

	last := response.Steps[len(response.Steps)-1]
	if last.ToolName != "browser_save_state" {
		t.Fatalf("expected final step browser_save_state, got %s", last.ToolName)
	}
	if got := last.Arguments["state_name"]; got != "app_example_com_login" {
		t.Fatalf("expected inferred state_name app_example_com_login, got %#v", got)
	}
}
