package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/cognition"
)

func TestHandleCodebaseTaskPlanUsesSurfaceHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)
	server := &ServerV2{}
	router := gin.New()
	router.POST("/v1/codebase/task/plan", server.handleCodebaseTaskPlan)

	body := map[string]interface{}{
		"intent":       "add a cognition endpoint",
		"repo":         "/home/mike/Mavaia",
		"current_area": "pkg/api",
		"files": []map[string]interface{}{
			{"path": "pkg/api/server_v2.go", "role": "api", "can_modify": true},
		},
		"test_commands": []string{"go test ./pkg/api"},
	}
	payload, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/v1/codebase/task/plan", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Ori-Context", "dev")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d with body %s", rec.Code, rec.Body.String())
	}

	var response cognition.CodebaseResidentTaskPlan
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if response.Surface != "dev" {
		t.Fatalf("expected dev surface from header, got %+v", response)
	}
	if len(response.WorkPackets) == 0 {
		t.Fatalf("expected work packets, got %+v", response)
	}
}
