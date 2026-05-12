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

func TestHandleWorkflowGrammarCompileUsesSurfaceHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)
	server := &ServerV2{}
	router := gin.New()
	router.POST("/v1/workflow/grammar/compile", server.handleWorkflowGrammarCompile)

	body := map[string]interface{}{
		"intent":        "draft a customer follow-up when a quote request arrives",
		"specification": "When a quote email arrives then review the request then draft a follow-up email.",
		"available_tools": []map[string]interface{}{
			{"name": "email", "kind": "inbox", "actions": []string{"email", "draft"}},
		},
	}
	payload, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/v1/workflow/grammar/compile", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Ori-Context", "studio")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d with body %s", rec.Code, rec.Body.String())
	}

	var response cognition.CompiledWorkflowGrammar
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if response.Surface != "studio" {
		t.Fatalf("expected studio surface from header, got %+v", response)
	}
	if response.Trigger.Kind != "event" || len(response.Nodes) == 0 {
		t.Fatalf("expected compiled workflow grammar, got %+v", response)
	}
}
