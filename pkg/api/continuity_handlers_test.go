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

func TestHandleContinuityRecoverUsesSurfaceHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)
	server := &ServerV2{}
	router := gin.New()
	router.POST("/v1/continuity/recover", server.handleContinuityRecover)

	body := map[string]interface{}{
		"intent":  "resume cognition primitive work",
		"project": "ORI primitives",
		"previous_sessions": []map[string]interface{}{
			{"id": "s1", "title": "SaaS scan implementation", "summary": "Shipped two primitives"},
		},
	}
	payload, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/v1/continuity/recover", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Ori-Context", "dev")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d with body %s", rec.Code, rec.Body.String())
	}

	var response cognition.ContinuityRecoveryPlan
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if response.Surface != "dev" {
		t.Fatalf("expected dev surface from header, got %+v", response)
	}
	if response.SuggestedContinuation.Title == "" {
		t.Fatalf("expected continuation, got %+v", response)
	}
}
