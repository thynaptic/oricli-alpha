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

func TestHandleActionGatewayPlanUsesSurfaceHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)
	server := &ServerV2{}
	router := gin.New()
	router.POST("/v1/actions/plan", server.handleActionGatewayPlan)

	body := map[string]any{
		"intent": "send a follow-up email to a new quote lead",
		"action_hints": []map[string]any{{
			"title":    "Send quote follow-up email",
			"tool":     "email",
			"external": true,
			"effects":  []string{"customer email"},
		}},
		"available_providers": []map[string]any{{
			"id":           "native_email",
			"name":         "Native Email",
			"kind":         "native",
			"capabilities": []string{"email", "send"},
			"scopes":       []string{"email:send"},
			"reliability":  "high",
			"available":    true,
		}},
		"approval_policy": map[string]any{"require_for_external_writes": true},
	}
	payload, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/v1/actions/plan", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Ori-Context", "studio")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d with body %s", rec.Code, rec.Body.String())
	}

	var response cognition.ActionGatewayPlan
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if response.Surface != "studio" {
		t.Fatalf("expected studio surface from header, got %+v", response)
	}
	if response.Recommended.ProviderID != "native_email" || !response.ApprovalGate.Required {
		t.Fatalf("expected planned native action behind approval, got %+v", response)
	}
}
