package api

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/core/auth"
	"github.com/thynaptic/oricli-go/pkg/core/config"
	"github.com/thynaptic/oricli-go/pkg/core/model"
	"github.com/thynaptic/oricli-go/pkg/core/store"
	"github.com/thynaptic/oricli-go/pkg/safety"
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
	Traces       *service.TraceStore
	WSHub        *Hub
	Router       *gin.Engine
	Port         int
	ActionRouter *service.ActionRouter
	Metrics      *service.MetricsCollector
	RateLimiter  *safety.RateLimiter
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
		Traces:       service.NewTraceStore(nil),
		WSHub:        hub,
		Router:       r,
		Port:         port,
		Metrics:      service.NewMetricsCollector(),
		RateLimiter:  safety.NewRateLimiter(),
	}

	// Wire ActionRouter for trigger-word intent dispatch
	research := service.NewResearchOrchestrator(agent)
	curiosity := service.NewCuriosityDaemon(agent.SovEngine.Graph, agent.SovEngine.VDI, agent.GenService, hub)
	s.ActionRouter = service.NewActionRouter(research, curiosity, hub)

	// Inject SearXNG searcher into SovereignEngine (avoids import cycle)
	agent.SovEngine.SearXNG = service.NewSearXNGSearcher()

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
	v1.GET("/traces", s.handleGetTraces)
	v1.GET("/loglines", s.handleLogLines)
	// Prometheus metrics endpoint — scraped by local Prometheus container
	v1.GET("/metrics", func(c *gin.Context) {
		s.Metrics.PrometheusHandler().ServeHTTP(c.Writer, c.Request)
	})

	// Protected
	protected := v1.Group("/", s.authMiddleware(), s.RateLimiter.GinMiddleware())
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
	if strings.HasPrefix(modelName, "oricli-") || modelName == "default" || modelName == "" {
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

	// --- Safety Pre-Flight (runs BEFORE Ollama is ever called) ---
	// Builds full multi-turn history for context poisoning analysis, then runs per-message gates.
	clientIP, _ := c.Get("client_ip")
	sessionKey := fmt.Sprintf("%v", clientIP)

	// Convert request messages to ChatTurn slice for multi-turn analysis
	var history []safety.ChatTurn
	for _, m := range req.Messages {
		history = append(history, safety.ChatTurn{Role: m.Role, Content: m.Content})
	}

	if blocked, refusal := s.Agent.SovEngine.CheckInputSafetyWithHistory(history, sessionKey); blocked {
		// Record the block with the rate limiter for probe trip-wire
		s.RateLimiter.RecordBlock(sessionKey, "injection")
		chatID := fmt.Sprintf("chatcmpl-%d", time.Now().Unix())
		c.JSON(http.StatusOK, gin.H{
			"id":     chatID,
			"object": "chat.completion",
			"choices": []gin.H{{
				"index": 0,
				"message": gin.H{
					"role":    "assistant",
					"content": refusal,
				},
				"finish_reason": "stop",
			}},
		})
		return
	}

	// Check session-level suspicion — hard-blocked sessions get a 429
	if s.Agent.SovEngine.Suspicion.IsHardBlocked(sessionKey) {
		remaining := s.Agent.SovEngine.Suspicion.BlockTimeRemaining(sessionKey)
		c.Header("Retry-After", remaining.String())
		c.JSON(http.StatusTooManyRequests, gin.H{
			"error":       "session suspended due to repeated policy violations",
			"retry_after": remaining.Seconds(),
		})
		return
	}

	sovTrace, err := s.Agent.SovEngine.ProcessInference(c.Request.Context(), lastMsg)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "sovereign engine failure"})
		return
	}

	// Merge client-provided system message (if any) with the sovereign trace
	// so Ollama sees a single authoritative system prompt.
	clientSystem := ""
	msgStart := 0
	if len(req.Messages) > 0 && req.Messages[0].Role == "system" {
		clientSystem = req.Messages[0].Content
		msgStart = 1
	}
	systemContent := sovTrace
	if clientSystem != "" {
		systemContent = sovTrace + "\n\n---\n\n" + clientSystem
	}

	msgs := make([]map[string]string, len(req.Messages)-msgStart+1)
	msgs[0] = map[string]string{"role": "system", "content": systemContent}
	for i, m := range req.Messages[msgStart:] {
		role := m.Role
		if role == "analyst" {
			role = "princess"
		}
		if role == "commander" {
			role = "daddy"
		}
		msgs[i+1] = map[string]string{"role": role, "content": m.Content}
	}

	chatID := fmt.Sprintf("chatcmpl-%d", time.Now().Unix())

	// Detect trigger-word action intent and dispatch async agent task
	type dispatchMeta struct {
		jobID   string
		action  string
		subject string
	}
	var dispatch *dispatchMeta
	if s.ActionRouter != nil {
		if act := service.DetectAction(lastMsg); act != nil {
			jid := fmt.Sprintf("job-%d", time.Now().UnixNano())
			dispatch = &dispatchMeta{jobID: jid, action: string(act.Type), subject: act.Subject}
			s.ActionRouter.Dispatch(c.Request.Context(), jid, act)
		}
	}

	// Stream tokens via SSE so the UI renders progressively
	streamOpts := map[string]interface{}{"model": modelName}
	isCanvasMode := (req.MaxTokens != nil && *req.MaxTokens >= 8192) || c.GetHeader("X-Canvas-Mode") == "true"
	if isCanvasMode {
		// Canvas / large-output request — unlock full context window
		streamOpts["options"] = map[string]interface{}{
			"num_predict": -1,
			"num_ctx":     32768,
		}
	}
	tokenCh, err := s.Agent.GenService.ChatStream(c.Request.Context(), msgs, streamOpts)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("X-Accel-Buffering", "no")

	// Emit agent_dispatch SSE event before the first token so the UI renders
	// the dispatch card immediately
	if dispatch != nil {
		dispatchEvt := map[string]interface{}{
			"type":    "agent_dispatch",
			"action":  dispatch.action,
			"subject": dispatch.subject,
			"job_id":  dispatch.jobID,
			"prompt":  lastMsg, // full original message for canvas passthrough
		}
		data, _ := json.Marshal(dispatchEvt)
		c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
		c.Writer.Flush()
	}

	var responseBuilder strings.Builder
	c.Stream(func(w io.Writer) bool {
		token, ok := <-tokenCh
		if !ok {
			// Stream complete — send finish chunk
			doneChunk := map[string]interface{}{
				"id":     chatID,
				"object": "chat.completion.chunk",
				"choices": []map[string]interface{}{
					{"index": 0, "delta": map[string]interface{}{}, "finish_reason": "stop"},
				},
			}
			data, _ := json.Marshal(doneChunk)
			fmt.Fprintf(w, "data: %s\n\n", string(data))
			return false
		}
		responseBuilder.WriteString(token)
		chunk := map[string]interface{}{
			"id":     chatID,
			"object": "chat.completion.chunk",
			"choices": []map[string]interface{}{
				{"index": 0, "delta": map[string]interface{}{"role": "assistant", "content": token}, "finish_reason": nil},
			},
		}
		data, _ := json.Marshal(chunk)
		fmt.Fprintf(w, "data: %s\n\n", string(data))
		return true
	})

	// Post-stream: async jobs on the full assembled response
	responseText := responseBuilder.String()
	if isCanvasMode {
		responseText, _ = s.Agent.SovEngine.AuditCanvasOutput(responseText)
	} else {
		responseText, _ = s.Agent.SovEngine.AuditOutput(responseText)
	}

	if s.Agent.SovEngine.Voice != nil {
		go s.Agent.SovEngine.Voice.Synthesize(responseText, s.Agent.SovEngine.Resonance.Current.ERI, 0.5, s.Agent.SovEngine.Resonance.Current.MusicalKey)
	}

	go s.Orchestrator.Execute("record_event", map[string]interface{}{
		"type":        "chat_interaction",
		"description": fmt.Sprintf("User: %s | Assistant: %s", lastMsg, responseText),
		"metadata": map[string]interface{}{
			"model": req.Model,
			"eri":   s.Agent.SovEngine.Resonance.Current.ERI,
			"key":   s.Agent.SovEngine.Resonance.Current.MusicalKey,
		},
	}, 5*time.Second)
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

	// Scan any provided content/url payload for indirect injection before ingesting
	if content, ok := req["content"].(string); ok && content != "" {
		scanRes := s.Agent.SovEngine.RagGuard.ScanScrapedContent(content)
		if scanRes.Flagged {
			log.Printf("[Safety:RAGGuard] Flagged web ingest content: %v", scanRes.Detections)
			req["content"] = scanRes.Sanitized
		}
	}

	res, err := s.Orchestrator.Execute("crawl_and_ingest", req, 300*time.Second)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, res)
}

func (s *ServerV2) handleGetTraces(c *gin.Context) {
	limitStr := c.DefaultQuery("limit", "50")
	limit, _ := strconv.Atoi(limitStr)
	if limit < 1 || limit > 500 {
		limit = 50
	}
	traces := s.Traces.ListRecent(limit)
	c.JSON(http.StatusOK, gin.H{"success": true, "traces": traces, "count": len(traces)})
}

func (s *ServerV2) handleLogLines(c *gin.Context) {
	nStr := c.DefaultQuery("n", "200")
	n, _ := strconv.Atoi(nStr)
	if n < 1 || n > 2000 {
		n = 200
	}
	logPath := "/home/mike/Mavaia/go_backbone.log"
	f, err := os.Open(logPath)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"lines": []string{}, "error": err.Error()})
		return
	}
	defer f.Close()

	var lines []string
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	// Return last n lines
	if len(lines) > n {
		lines = lines[len(lines)-n:]
	}
	c.JSON(http.StatusOK, gin.H{"lines": lines, "total": len(lines)})
}

func (s *ServerV2) Start() error {
	addr := fmt.Sprintf(":%d", s.Port)
	log.Printf("[API] Gateway starting on %s", addr)
	return s.Router.Run(addr)
}
