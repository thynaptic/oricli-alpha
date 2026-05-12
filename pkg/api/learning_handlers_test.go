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

func TestHandleLearningMasteryCompileUsesSurfaceHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)
	server := &ServerV2{}
	router := gin.New()
	router.POST("/v1/learning/mastery/compile", server.handleLearningMasteryCompile)

	body := map[string]interface{}{
		"objective": "learn the support SOP",
		"sources": []map[string]interface{}{{
			"id":      "sop_1",
			"kind":    "manual",
			"title":   "Support SOP",
			"content": "Triage urgent customer issues first. Escalate billing disputes after collecting account context.",
		}},
	}
	payload, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/v1/learning/mastery/compile", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Ori-Context", "studio")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d with body %s", rec.Code, rec.Body.String())
	}

	var response cognition.MaterialToMasterySystem
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if len(response.ConceptGraph) == 0 {
		t.Fatalf("expected concept graph")
	}
	foundDev := false
	for _, item := range response.Reinforcement {
		if item.Surface == "dev" {
			foundDev = true
			break
		}
	}
	if !foundDev {
		t.Fatalf("expected cross-surface reinforcement to include dev, got %#v", response.Reinforcement)
	}
}
