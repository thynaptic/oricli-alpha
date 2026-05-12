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

func TestHandleConversationHarvestUsesSurfaceHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)
	server := &ServerV2{}
	router := gin.New()
	router.POST("/v1/conversation/harvest", server.handleConversationHarvest)

	body := map[string]interface{}{
		"title": "launch sync",
		"messages": []map[string]interface{}{
			{"speaker": "Mike", "text": "We decided to ship Friday."},
		},
	}
	payload, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/v1/conversation/harvest", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Ori-Context", "studio")
	rec := httptest.NewRecorder()

	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d body=%s", rec.Code, rec.Body.String())
	}
	var response cognition.ConversationContextHarvest
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}
	if response.Surface != "studio" {
		t.Fatalf("expected studio surface from header, got %+v", response)
	}
	if len(response.Decisions) != 1 {
		t.Fatalf("expected harvested decision, got %+v", response)
	}
}
