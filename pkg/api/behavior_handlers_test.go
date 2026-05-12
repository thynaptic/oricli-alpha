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

func TestHandleBehaviorCreateUsesSurfaceHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)
	server := &ServerV2{}
	router := gin.New()
	router.POST("/v1/behavior/create", server.handleBehaviorCreate)

	payload := []byte(`{"type":"daily","title":"clear client approvals"}`)
	req := httptest.NewRequest(http.MethodPost, "/v1/behavior/create", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Ori-Context", "studio")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d with body %s", rec.Code, rec.Body.String())
	}
	var response cognition.BehaviorObject
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if response.Surface != "studio" {
		t.Fatalf("expected studio surface, got %+v", response)
	}
	if response.FeedbackModel.StateLabel != "Workflow health" {
		t.Fatalf("expected studio feedback label, got %+v", response.FeedbackModel)
	}
}

func TestHandleBehaviorEventReturnsRecoveryFeedback(t *testing.T) {
	gin.SetMode(gin.TestMode)
	server := &ServerV2{}
	router := gin.New()
	router.POST("/v1/behavior/event", server.handleBehaviorEvent)

	body := map[string]interface{}{
		"behavior": map[string]interface{}{
			"type":  "daily",
			"title": "walk for 20 minutes",
		},
		"event": "missed",
		"context": map[string]interface{}{
			"energy": "low",
		},
	}
	payload, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}
	req := httptest.NewRequest(http.MethodPost, "/v1/behavior/event", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Ori-Context", "home")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d with body %s", rec.Code, rec.Body.String())
	}
	var response cognition.BehaviorEventFeedback
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if len(response.Recovery) == 0 {
		t.Fatalf("expected recovery feedback, got %+v", response)
	}
}
