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

func TestHandleProcedureCompileUsesSurfaceHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)
	server := &ServerV2{}
	router := gin.New()
	router.POST("/v1/procedure/compile", server.handleProcedureCompile)

	body := map[string]interface{}{
		"title":          "support refund triage",
		"actor":          "support operator",
		"inputs":         []string{"customer message", "order record"},
		"outputs":        []string{"refund decision"},
		"outcome_signal": "customer receives a correct next step",
		"observations": []map[string]interface{}{
			{"title": "Review customer message", "tool": "inbox"},
			{"title": "Check order record", "tool": "crm"},
			{"title": "Draft refund decision", "tool": "email"},
		},
	}
	payload, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/v1/procedure/compile", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Ori-Context", "studio")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d with body %s", rec.Code, rec.Body.String())
	}

	var response cognition.CompiledProcedure
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if response.Surface != "studio" {
		t.Fatalf("expected studio surface from header, got %+v", response)
	}
	if response.SCLSeed.Tier != "skills" || len(response.Checklist) == 0 {
		t.Fatalf("expected compiled procedure, got %+v", response)
	}
}
