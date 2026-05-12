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

func TestHandleCommitmentResourceReasonUsesSurfaceHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)
	server := &ServerV2{}
	router := gin.New()
	router.POST("/v1/resources/commitment/reason", server.handleCommitmentResourceReason)

	body := map[string]interface{}{
		"decision_question": "Can we book the weekend trip?",
		"proposed_action": map[string]interface{}{
			"title":         "Weekend trip",
			"resource_type": "money",
			"amount":        200,
		},
		"resource_pools": []map[string]interface{}{
			{"type": "money", "label": "trip buffer", "amount": 250, "source": "user supplied"},
		},
	}
	payload, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/v1/resources/commitment/reason", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Ori-Context", "home")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d with body %s", rec.Code, rec.Body.String())
	}
	var response cognition.CommitmentResourceReasoningPlan
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if response.Surface != "home" || response.ResourceReality.ResourceType != "money" {
		t.Fatalf("unexpected response: %+v", response)
	}
}
