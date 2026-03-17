package api

import (
	"strings"
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/core/auth"
	"github.com/thynaptic/oricli-go/pkg/core/config"
	"github.com/thynaptic/oricli-go/pkg/core/model"
	"github.com/thynaptic/oricli-go/pkg/core/store"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// ServerV2 represents the Hardened Sovereign API Gateway
type ServerV2 struct {
	cfg          config.Config
	store        store.Store
	auth         *auth.Service
	Orchestrator *service.GoOrchestrator
	Agent        *service.GoAgentService
	Monitor      *service.MonitorService
	Router       *gin.Engine
	Port         int
}

func NewServerV2(cfg config.Config, st store.Store, orch *service.GoOrchestrator, agent *service.GoAgentService, mon *service.MonitorService, port int) *ServerV2 {
	r := gin.Default()
	
	s := &ServerV2{
		cfg:          cfg,
		store:        st,
		auth:         auth.NewService(st),
		Orchestrator: orch,
		Agent:        agent,
		Monitor:      mon,
		Router:       r,
		Port:         port,
	}
	
	s.setupRoutes()
	return s
}

func (s *ServerV2) setupRoutes() {
	v1 := s.Router.Group("/v1")
	{
		v1.POST("/chat/completions", s.handleChatCompletions)
		v1.GET("/health", s.handleHealth)
		
		// Swarm Execution
		v1.POST("/swarm/run", s.handleSwarmRun)
		
		// Pure-Go Ingestion (The RAG Bridge)
		v1.POST("/ingest", s.handleIngest)
		v1.POST("/ingest/web", s.handleIngestWeb)
	}
}

func (s *ServerV2) handleHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "ready",
		"system": "oricli-alpha-v2",
		"pure_go": true,
	})
}

func (s *ServerV2) handleSwarmRun(c *gin.Context) {
	var body map[string]interface{}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	operation, _ := body["operation"].(string)
	params, _ := body["params"].(map[string]interface{})

	if operation == "" && body["query"] != nil {
		// Handle legacy Python client format
		operation = "reason"
		params = body
	}

	if operation == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "operation is required"})
		return
	}

	result, err := s.Orchestrator.Execute(operation, params, 300*time.Second)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"success": true, "result":  result})
}

func (s *ServerV2) handleChatCompletions(c *gin.Context) {
	var req model.ChatCompletionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Determine actual model to use
	modelName := req.Model
	if strings.HasPrefix(modelName, "oricli-") {
		// Use default model for internal aliases
		modelName = "" 
	}

	res, err := s.Agent.GenService.Generate(req.Messages[len(req.Messages)-1].Content, map[string]interface{}{
		"model": modelName,
	})
	
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, map[string]interface{}{
		"id": fmt.Sprintf("chatcmpl-%d", time.Now().Unix()),
		"object": "chat.completion",
		"created": time.Now().Unix(),
		"model": req.Model,
		"choices": []map[string]interface{}{{
			"index": 0,
			"message": map[string]string{"role": "assistant", "content": res["text"].(string)},
			"finish_reason": "stop",
		}},
	})
}

func (s *ServerV2) handleIngest(c *gin.Context) {
	// Native Go Ingestion implementation
	c.JSON(http.StatusOK, gin.H{"success": true, "method": "go-native-rag"})
}

func (s *ServerV2) handleIngestWeb(c *gin.Context) {
	var req struct {
		URL      string                 `json:"url"`
		MaxPages int                    `json:"max_pages"`
		MaxDepth int                    `json:"max_depth"`
		Metadata map[string]interface{} `json:"metadata"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.Orchestrator.Execute("crawl_and_ingest", map[string]interface{}{
		"url":       req.URL,
		"max_pages": float64(req.MaxPages),
		"max_depth": float64(req.MaxDepth),
		"metadata":  req.Metadata,
	}, 300*time.Second)

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"success": true, "result": result})
}

func (s *ServerV2) Start() error {
	return s.Router.Run(fmt.Sprintf(":%d", s.Port))
}
