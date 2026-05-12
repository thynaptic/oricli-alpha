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

func TestHandleContextMomentumUsesSurfaceHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)
	server := &ServerV2{}
	router := gin.New()
	router.POST("/v1/context/momentum", server.handleContextMomentum)

	body := map[string]interface{}{
		"current_project": "sales follow-up system",
		"items": []map[string]interface{}{
			{"title": "Client reply template draft", "kind": "note", "project_hint": "sales follow-up system"},
			{"title": "Interesting objection-handling article", "kind": "link"},
		},
		"user_state": map[string]interface{}{"energy": "low"},
	}
	payload, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/v1/context/momentum", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Ori-Context", "studio")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 OK, got %d with body %s", rec.Code, rec.Body.String())
	}

	var response cognition.ContextMomentumSystem
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if response.Surface != "studio" {
		t.Fatalf("expected studio surface from header, got %+v", response)
	}
	if response.NextFiveMinute.Title == "" || len(response.Actionability.ActiveProjects) == 0 {
		t.Fatalf("expected project packetizer response, got %+v", response)
	}
}
