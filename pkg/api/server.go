package api

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// Server represents the Go API Gateway
type Server struct {
	Router       *gin.Engine
	Orchestrator *service.GoOrchestrator
	Agent        *service.GoAgentService
	Monitor      *service.MonitorService
	Port         int
}

func NewServer(orch *service.GoOrchestrator, agent *service.GoAgentService, mon *service.MonitorService, port int) *Server {
	// Set Gin to release mode if not in development
	if os.Getenv("GO_ENV") == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.Default()

	// Middleware for logging and recovery
	r.Use(gin.Logger())
	r.Use(gin.Recovery())

	s := &Server{
		Router:       r,
		Orchestrator: orch,
		Agent:        agent,
		Monitor:      mon,
		Port:         port,
	}

	s.setupRoutes()
	return s
}

func (s *Server) setupRoutes() {
	v1 := s.Router.Group("/v1")
	{
		// OpenAI Compatible Endpoints
		v1.POST("/chat/completions", s.handleChatCompletions)
		v1.GET("/models", s.handleListModels)

		// Sovereign Hive Endpoints
		v1.POST("/swarm/run", s.handleSwarmRun)
		v1.POST("/swarm/inject", s.handleSwarmInject)
		
		// Health Checks
		v1.GET("/health", func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{"status": "ready", "system": "oricli-go-gateway"})
		})
		v1.GET("/health/modules", func(c *gin.Context) {
			c.JSON(http.StatusOK, s.Monitor.ListStatuses())
		})
	}
}

// handleChatCompletions handles OpenAI-compatible chat requests
func (s *Server) handleChatCompletions(c *gin.Context) {
	var req map[string]interface{}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	log.Printf("[API] Received ChatCompletion request")

	// Extract query from last user message
	query := ""
	msgs, ok := req["messages"].([]interface{})
	if ok && len(msgs) > 0 {
		lastMsg, ok := msgs[len(msgs)-1].(map[string]interface{})
		if ok {
			query, _ = lastMsg["content"].(string)
		}
	}

	// 1. Run the Go Agent Loop
	answer, err := s.Agent.Run(query, nil)
	if err != nil {
		log.Printf("[API] Agent execution failed: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Clean up reasoning/JSON if the agent included it in the final string
	finalContent := answer
	if strings.Contains(answer, "}") {
		// If the agent returned raw JSON at the end, try to extract the thought
		var decision struct {
			Thought string `json:"thought"`
		}
		jsonStr := answer
		if strings.Contains(answer, "```json") {
			parts := strings.Split(answer, "```json")
			if len(parts) > 1 {
				jsonStr = strings.Split(parts[1], "```")[0]
			}
		}
		if err := json.Unmarshal([]byte(jsonStr), &decision); err == nil && decision.Thought != "" {
			finalContent = decision.Thought
		}
	}

	model, _ := req["model"].(string)
	if model == "" {
		model = "oricli-swarm"
	}

	openAIResp := map[string]interface{}{
		"id":      fmt.Sprintf("chatcmpl-%d", time.Now().Unix()),
		"object":  "chat.completion",
		"created": time.Now().Unix(),
		"model":   model,
		"choices": []map[string]interface{}{
			{
				"index": 0,
				"message": map[string]string{
					"role":    "assistant",
					"content": finalContent,
				},
				"finish_reason": "stop",
			},
		},
		"usage": map[string]int{
			"prompt_tokens":     0,
			"completion_tokens": 0,
			"total_tokens":      0,
		},
	}

	c.JSON(http.StatusOK, openAIResp)
}

// handleSwarmRun triggers a multi-agent swarm deliberation
func (s *Server) handleSwarmRun(c *gin.Context) {
	var req map[string]interface{}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	query, _ := req["query"].(string)
	log.Printf("[API] Triggering Swarm Run for: %s", query)

	// Route to the Hive Orchestrator
	result, err := s.Orchestrator.Execute("swarm_run", req, 300*time.Second)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (s *Server) handleSwarmInject(c *gin.Context) {
	var req struct {
		Topic    string                 `json:"topic"`
		Payload  map[string]interface{} `json:"payload"`
		Protocol string                 `json:"protocol"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	s.Orchestrator.Bus.Publish(bus.Message{
		Protocol: bus.Protocol(req.Protocol),
		Topic:    req.Topic,
		SenderID: "python_bridge",
		Payload:  req.Payload,
	})

	c.JSON(http.StatusOK, gin.H{"success": true})
}

func (s *Server) handleListModels(c *gin.Context) {
	// Simple static list for now, can be dynamic later
	models := []map[string]interface{}{
		{"id": "oricli-swarm", "object": "model", "owned_by": "thynaptic"},
		{"id": "cognitive_generator", "object": "model", "owned_by": "thynaptic"},
	}
	c.JSON(http.StatusOK, gin.H{"object": "list", "data": models})
}

func (s *Server) Start() error {
	addr := fmt.Sprintf(":%d", s.Port)
	log.Printf("[API] Gateway starting on %s", addr)
	return s.Router.Run(addr)
}
