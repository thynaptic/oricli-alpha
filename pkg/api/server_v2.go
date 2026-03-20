package api

import (
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
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
	Monitor      *service.ModuleMonitorService
	WSHub        *Hub
	Router       *gin.Engine
	Port         int
}

func NewServerV2(cfg config.Config, st store.Store, orch *service.GoOrchestrator, agent *service.GoAgentService, mon *service.ModuleMonitorService, port int) *ServerV2 {
	r := gin.Default()
	hub := NewHub()
	go hub.Run()

	// CORS & Cache-Control Middleware
	r.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS, PUT, DELETE")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, X-Tenant-ID")
		
		if !strings.HasPrefix(c.Request.URL.Path, "/v1") {
			c.Writer.Header().Set("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0")
			c.Writer.Header().Set("Pragma", "no-cache")
			c.Writer.Header().Set("Expires", "0")
		}

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	})

	// Serve Flutter UI Static Files
	webDir := "/home/mike/Mavaia/oricli_ui/build/web"
	r.Static("/portal", webDir)
	r.Static("/assets", webDir+"/assets")
	r.Static("/canvaskit", webDir+"/canvaskit")
	r.Static("/icons", webDir+"/icons")

	r.GET("/", func(c *gin.Context) {
		c.Redirect(http.StatusMovedPermanently, "/portal/")
	})

	r.NoRoute(func(c *gin.Context) {
		if strings.HasPrefix(c.Request.URL.Path, "/portal") {
			c.File(webDir + "/index.html")
			return
		}
		if !strings.HasPrefix(c.Request.URL.Path, "/v1") {
			c.Redirect(http.StatusTemporaryRedirect, "/portal/")
			return
		}
		c.JSON(404, gin.H{"error": "not found"})
	})

	s := &ServerV2{
		cfg:          cfg,
		store:        st,
		auth:         auth.NewService(st),
		Orchestrator: orch,
		Agent:        agent,
		Monitor:      mon,
		WSHub:        hub,
		Router:       r,
		Port:         port,
	}

	s.setupRoutes()
	return s
}

func (s *ServerV2) authMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		raw := c.GetHeader("Authorization")
		if raw == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "missing Authorization header"})
			return
		}
		ctx, err := s.auth.Authenticate(c.Request.Context(), raw)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "invalid or expired API key"})
			return
		}
		c.Request = c.Request.WithContext(ctx)
		c.Next()
	}
}

func (s *ServerV2) setupRoutes() {
	v1 := s.Router.Group("/v1")

	// Public
	v1.GET("/health", s.handleHealth)
	v1.GET("/ws", s.handleWS)

	// Protected
	protected := v1.Group("/", s.authMiddleware())
	{
		protected.POST("/chat/completions", s.handleChatCompletions)
		protected.POST("/swarm/run", s.handleSwarmRun)
		protected.POST("/ingest", s.handleIngest)
		protected.POST("/ingest/web", s.handleIngestWeb)
		protected.POST("/telegram/webhook", s.handleTelegramWebhook)
	}
}

func (s *ServerV2) handleHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ready", "system": "oricli-alpha-v2", "pure_go": true})
}

func (s *ServerV2) handleChatCompletions(c *gin.Context) {
	var req model.ChatCompletionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	modelName := req.Model
	if strings.HasPrefix(modelName, "oricli-") {
		modelName = ""
	}

	lastMsg := ""
	if len(req.Messages) > 0 {
		lastMsg = req.Messages[len(req.Messages)-1].Content
	}

	if req.Profile != "" {
		if p, ok := s.Agent.SovEngine.Profiles.GetProfile(req.Profile); ok {
			s.Agent.SovEngine.ActiveProfile = p
			log.Printf("[API] Applied profile: %s", req.Profile)
		}
	}
	
	sovTrace, err := s.Agent.SovEngine.ProcessInference(c.Request.Context(), lastMsg)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "sovereign engine failure"})
		return
	}

	msgs := make([]map[string]string, len(req.Messages)+1)
	msgs[0] = map[string]string{"role": "system", "content": sovTrace}

	for i, m := range req.Messages {
		role := m.Role
		if role == "analyst" { role = "princess" }
		if role == "commander" { role = "daddy" }
		msgs[i+1] = map[string]string{"role": role, "content": m.Content}
	}

	res, err := s.Agent.GenService.Chat(msgs, map[string]interface{}{"model": modelName})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	responseText := res["text"].(string)
	responseText, _ = s.Agent.SovEngine.SelfAlign(c.Request.Context(), lastMsg, responseText)
	responseText, _ = s.Agent.SovEngine.AuditOutput(responseText)

	// Trigger Voice Synthesis (Async)
	if s.Agent.SovEngine.Voice != nil {
		go s.Agent.SovEngine.Voice.Synthesize(responseText, s.Agent.SovEngine.Resonance.Current.ERI, 0.5, s.Agent.SovEngine.Resonance.Current.MusicalKey)
	}

	s.Orchestrator.Execute("record_event", map[string]interface{}{
		"type":        "chat_interaction",
		"description": fmt.Sprintf("User: %s | Assistant: %s", lastMsg, responseText),
		"metadata": map[string]interface{}{
			"model": req.Model,
			"eri":   s.Agent.SovEngine.Resonance.Current.ERI,
			"key":   s.Agent.SovEngine.Resonance.Current.MusicalKey,
		},
	}, 5*time.Second)

	c.JSON(http.StatusOK, map[string]interface{}{
		"id":      fmt.Sprintf("chatcmpl-%d", time.Now().Unix()),
		"object":  "chat.completion",
		"created": time.Now().Unix(),
		"model":   req.Model,
		"choices": []map[string]interface{}{{
			"index":         0,
			"message":       map[string]string{"role": "assistant", "content": responseText},
			"finish_reason": "stop",
		}},
		"usage": map[string]interface{}{
			"resonance": s.Agent.SovEngine.Resonance.Current.ERI,
			"mode":      s.Agent.SovEngine.Resonance.Current.MusicalKey,
			"sensory":   s.Agent.SovEngine.CurrentSensory.ToJSONMap(),
		},
	})
}

func (s *ServerV2) handleTelegramWebhook(c *gin.Context) {
	var update struct {
		UpdateID int `json:"update_id"`
		Message  *struct {
			Chat struct { ID int64 `json:"id"` } `json:"chat"`
			Text string `json:"text"`
			From struct { Username string `json:"username"` } `json:"from"`
		} `json:"message"`
	}

	if err := c.ShouldBindJSON(&update); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if update.Message == nil || update.Message.Text == "" {
		c.JSON(http.StatusOK, gin.H{"status": "ignored"})
		return
	}

	if update.Message.Chat.ID != s.Agent.SovEngine.Telegram.ChatID {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized chat id"})
		return
	}

	_, err := s.Agent.SovEngine.ProcessInference(c.Request.Context(), update.Message.Text)
	if err != nil {
		s.Agent.SovEngine.Telegram.SendMessage(update.Message.Chat.ID, "Cognitive error. Retry.", "HTML")
		return
	}

	responseText := "I am here. " + update.Message.Text
	responseText, _ = s.Agent.SovEngine.SelfAlign(c.Request.Context(), update.Message.Text, responseText)
	responseText, _ = s.Agent.SovEngine.AuditOutput(responseText)

	// Trigger Voice Synthesis (Async)
	if s.Agent.SovEngine.Voice != nil {
		go s.Agent.SovEngine.Voice.Synthesize(responseText, s.Agent.SovEngine.Resonance.Current.ERI, 0.5, s.Agent.SovEngine.Resonance.Current.MusicalKey)
	}

	s.Agent.SovEngine.Telegram.SendMessage(update.Message.Chat.ID, responseText, "HTML")
	c.JSON(http.StatusOK, gin.H{"status": "success"})
}

func (s *ServerV2) handleSwarmRun(c *gin.Context) {
	var body map[string]interface{}
	if err := c.ShouldBindJSON(&body); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	op, _ := body["operation"].(string)
	params, _ := body["params"].(map[string]interface{})
	res, err := s.Orchestrator.Execute(op, params, 300*time.Second)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"success": true, "result": res})
}

func (s *ServerV2) handleIngest(c *gin.Context) {
	file, err := c.FormFile("file")
	if err == nil {
		f, _ := file.Open()
		data, _ := io.ReadAll(f)
		params := map[string]interface{}{"file_data": data, "file_name": file.Filename}
		res, err := s.Orchestrator.Execute("ingest_file", params, 60*time.Second)
		if err != nil { c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()}); return }
		c.JSON(http.StatusOK, res)
	} else {
		var req map[string]interface{}
		c.ShouldBindJSON(&req)
		res, err := s.Orchestrator.Execute("ingest_text", req, 60*time.Second)
		if err != nil { c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()}); return }
		c.JSON(http.StatusOK, res)
	}
}

func (s *ServerV2) handleIngestWeb(c *gin.Context) {
	var req map[string]interface{}
	c.ShouldBindJSON(&req)
	res, err := s.Orchestrator.Execute("crawl_and_ingest", req, 300*time.Second)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, res)
}

func (s *ServerV2) Start() error {
	addr := fmt.Sprintf(":%d", s.Port)
	log.Printf("[API] Gateway starting on %s", addr)
	return s.Router.Run(addr)
}
