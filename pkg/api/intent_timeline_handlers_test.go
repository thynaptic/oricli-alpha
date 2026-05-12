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

func TestHandleIntentTimelineBuildUsesSurfaceHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)
	server := &ServerV2{}
	router := gin.New()
	router.POST("/v1/intent/timeline", server.handleIntentTimelineBuild)

	body := map[string]interface{}{
		"project":   "ORI primitives",
		"objective": "preserve rationale",
		"events": []map[string]interface{}{
			{"action": "read canvas", "intent": "extract primitive", "rationale": "less bookkeeping retains users"},
		},
	}
	payload, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/v1/intent/timeline", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Ori-Context", "dev")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d with body %s", rec.Code, rec.Body.String())
	}
	var response cognition.IntentTimeline
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if response.Surface != "dev" || response.CurrentIntent.Goal == "" {
		t.Fatalf("unexpected response: %+v", response)
	}
}
