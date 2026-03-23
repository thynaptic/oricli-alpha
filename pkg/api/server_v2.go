package api

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/core/auth"
	"github.com/thynaptic/oricli-go/pkg/core/config"
	"github.com/thynaptic/oricli-go/pkg/core/model"
	"github.com/thynaptic/oricli-go/pkg/core/store"
	"github.com/thynaptic/oricli-go/pkg/reform"
	"github.com/thynaptic/oricli-go/pkg/safety"
	"github.com/thynaptic/oricli-go/pkg/service"
	"github.com/thynaptic/oricli-go/pkg/sovereign"
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
	GoalService  *service.GoalService
	GoalExecutor *service.GoalExecutor
	Metrics      *service.MetricsCollector
	RateLimiter  *safety.RateLimiter
	SovAuth      *sovereign.SovereignAuth
	ExecHandler  *sovereign.SovereignExecHandler
	ImageGen         *service.ImageGenManager
	MemoryBank       *service.MemoryBank
	DocumentIngestor *service.DocumentIngestor
	Skills           *service.SkillManager
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
		SovAuth:      sovereign.NewSovereignAuth(),
		ExecHandler:  sovereign.NewSovereignExecHandler(),
		ImageGen:     service.NewImageGenManager(),
	}

	// Bootstrap PocketBase long-term memory bank
	mb := service.NewMemoryBank()
	s.MemoryBank = mb
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if err := mb.Bootstrap(ctx); err != nil {
			log.Printf("[ServerV2] PocketBase bootstrap error: %v", err)
		}
	}()

	// Wire ActionRouter for trigger-word intent dispatch
	research := service.NewResearchOrchestrator(agent)
	curiosity := service.NewCuriosityDaemon(agent.SovEngine.Graph, agent.SovEngine.VDI, agent.GenService, hub)
	curiosity.MemoryBank = mb
	s.ActionRouter = service.NewActionRouter(research, curiosity, hub)

	// Wire MemoryBank to ExecHandler for PB audit trail on every !command
	s.ExecHandler.MemoryBank = mb

	// Restore this month's RunPod spend from PocketBase
	if rp := agent.GenService.RunPodMgr; rp != nil {
		rp.MemoryBank = mb
		go func() {
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()
			rp.LoadSpendFromBank(ctx)
		}()
	}

	// Inject SearXNG searcher into SovereignEngine (avoids import cycle)
	agent.SovEngine.SearXNG = service.NewSearXNGSearcher()

	// Load skills from oricli_core/skills/
	s.Skills = service.NewSkillManager("oricli_core/skills")
	log.Printf("[ServerV2] Loaded %d skills", len(s.Skills.ListSkills()))

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
		protected.POST("/images/generations", s.handleImageGenerations)
		protected.POST("/swarm/run", s.handleSwarmRun)
		protected.POST("/ingest", s.handleIngest)
		protected.POST("/ingest/web", s.handleIngestWeb)
		protected.POST("/telegram/webhook", s.handleTelegramWebhook)

		// DAG Goal Management
		protected.GET("/goals", s.handleListGoals)
		protected.POST("/goals", s.handleCreateGoal)
		protected.PUT("/goals/:id", s.handleUpdateGoal)
		protected.DELETE("/goals/:id", s.handleDeleteGoal)
		protected.GET("/daemons", s.handleDaemonHealth)

		protected.GET("/memories", s.handleListMemories)
		protected.GET("/memories/knowledge", s.handleListKnowledge)

		protected.POST("/documents/upload", s.handleDocumentUpload)
		protected.GET("/documents", s.handleListDocuments)

		protected.POST("/feedback", s.handleReactionFeedback)

		// Sovereign Identity — active .ori profile editor
		protected.GET("/sovereign/identity", s.handleGetSovereignIdentity)
		protected.PUT("/sovereign/identity", s.handlePutSovereignIdentity)
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
	if strings.HasPrefix(modelName, "oricli") || modelName == "default" || modelName == "" {
		modelName = ""
	}

	lastMsg := ""
	if len(req.Messages) > 0 {
		lastMsg = req.Messages[len(req.Messages)-1].Content
	}

	// Notify curiosity daemon of activity + seed from user message
	if cd := s.ActionRouter.CuriosityDaemon; cd != nil {
		cd.NotifyActivity()
		if lastMsg != "" {
			cd.SeedFromMessage(lastMsg)
		}
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

	// --- Sovereign auth command interception ---
	// /admin <key>  → Level 1 (elevated chat)
	// /exec <key>   → Level 2 (elevated chat + system commands)
	// /auth off     → end session (legacy alias kept)
	trimmedMsg := strings.TrimSpace(lastMsg)
	lowerMsg := strings.ToLower(trimmedMsg)
	if strings.HasPrefix(lowerMsg, "/admin") || strings.HasPrefix(lowerMsg, "/exec") || lowerMsg == "/auth off" {
		s.handleSovereignAuth(c, trimmedMsg, sessionKey)
		return
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

	// Attach sovereign level to context for ProcessInference
	sovLevel := s.SovAuth.GetSessionLevel(sessionKey)
	ctx := sovereign.WithSovereignLevel(c.Request.Context(), sovLevel)

	// Level 2: handle !exec commands before LLM inference
	if sovLevel >= sovereign.LevelExec && sovereign.IsExecCommand(lastMsg) {
		result := s.ExecHandler.Handle(lastMsg)
		if result == "__SOVEREIGN_MODULES__" {
			result = s.Agent.SovEngine.ListModulesSummary()
		}
		chatID := fmt.Sprintf("chatcmpl-%d", time.Now().Unix())
		c.JSON(http.StatusOK, gin.H{
			"id": chatID, "object": "chat.completion",
			"choices": []gin.H{{"index": 0, "message": gin.H{"role": "assistant", "content": result}, "finish_reason": "stop"}},
		})
		return
	}

	sovTrace, err := s.Agent.SovEngine.ProcessInference(ctx, lastMsg)
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

	// Inject relevant long-term memories as RAG context prefix
	if s.MemoryBank != nil && s.MemoryBank.IsEnabled() && lastMsg != "" {
		if frags, err := s.MemoryBank.QuerySimilar(c.Request.Context(), lastMsg, 5); err == nil && len(frags) > 0 {
			ragCtx := service.FormatRAGContext(frags, 1200)
			if ragCtx != "" {
				systemContent = ragCtx + "\n\n---\n\n" + systemContent
			}
		}
	}

	// Inject matched skill context — trigger-based, zero overhead when no match
	if s.Skills != nil && lastMsg != "" {
		if matched := s.Skills.MatchSkills(lastMsg); len(matched) > 0 {
			skill := matched[0] // take highest-priority match
			var sb strings.Builder
			sb.WriteString("### ACTIVE SKILL: " + skill.Name + "\n")
			if skill.Mindset != "" {
				sb.WriteString("\n#### Mindset:\n" + skill.Mindset + "\n")
			}
			if skill.Instructions != "" {
				sb.WriteString("\n#### Instructions:\n" + skill.Instructions + "\n")
			}
			systemContent = systemContent + "\n\n---\n\n" + sb.String()
			log.Printf("[Skills] Injected skill: %s", skill.Name)
		}
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
	isResearchAction := dispatch != nil && (dispatch.action == "research" || dispatch.action == "analyze")
	isCodeAction := dispatch != nil && dispatch.action == "create"

	switch {
	case isResearchAction:
		// Deep research / analysis — route to heavy model; user expects a wait
		streamOpts["use_research_model"] = true
	case isCanvasMode || isCodeAction:
		// Canvas generation or explicit code create — mid-tier model
		streamOpts["use_code_model"] = true
	}
	if isCanvasMode {
		// Unlock full context window for large-output canvas requests
		streamOpts["options"] = map[string]interface{}{
			"num_predict": -1,
			"num_ctx":     32768,
		}
	}

	// Inject Code Constitution into system prompt now that canvas/code mode is resolved.
	// Canvas gets the language-agnostic CanvasConstitution; code actions get the stricter
	// Go-scoped CodeConstitution. Must run before ChatStream to influence generation.
	if isCanvasMode {
		msgs[0]["content"] += "\n\n" + reform.NewCanvasConstitution().GetSystemPrompt()
	} else if isCodeAction {
		msgs[0]["content"] += "\n\n" + reform.NewCodeConstitution().GetSystemPrompt()
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
		modelTier := "chat"
		if isResearchAction {
			modelTier = "research"
		} else if isCanvasMode || isCodeAction {
			modelTier = "code"
		}
		dispatchEvt := map[string]interface{}{
			"type":        "agent_dispatch",
			"action":      dispatch.action,
			"subject":     dispatch.subject,
			"job_id":      dispatch.jobID,
			"prompt":      lastMsg, // full original message for canvas passthrough
			"model_tier":  modelTier,
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

	// SCAI Critique-Revision loop — fires in background to preserve streaming latency.
	// If a constitutional violation is detected, a scai_correction WS event is broadcast
	// so the UI can patch the last assistant message in-place with the revised text.
	// This also generates an RFAL DPO pair for every violation (learning signal).
	// Zero impact on the happy path (CLEAR critique → goroutine exits silently).
	sessionID := c.GetHeader("X-Session-ID")
	go func(query, response, sid string) {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		corrected, violated := s.Agent.SovEngine.SelfAlign(ctx, query, response)
		if !violated {
			return
		}
		s.Agent.SovEngine.WSHub.BroadcastEvent("scai_correction", map[string]interface{}{
			"session_id":       sid,
			"corrected":        corrected,
			"original_preview": response[:min(120, len(response))],
		})
	}(lastMsg, responseText, sessionID)

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

	// Conversation write-back: persist this exchange to PocketBase long-term memory.
	// Only when both sides have meaningful content. Fires in background, never blocks.
	if s.MemoryBank != nil && s.MemoryBank.IsEnabled() &&
		len(lastMsg) > 50 && len(responseText) > 50 {
		go func() {
			// Extract a short topic from the user's message (first 5 words)
			words := strings.Fields(lastMsg)
			if len(words) > 5 {
				words = words[:5]
			}
			topic := strings.Join(words, " ")

			// Combine user + assistant turn, cap response at 400 chars
			resp := responseText
			if len(resp) > 400 {
				resp = resp[:400] + "…"
			}
			combined := fmt.Sprintf("User: %s\n\nOricli: %s", lastMsg, resp)

			s.MemoryBank.Write(service.MemoryFragment{
				Content:      combined,
				Source:       "conversation",
				Topic:        topic,
				Importance:   0.4,
				Provenance:   service.ProvenanceConversation,
				Volatility:   service.InferVolatility(topic),
				LineageDepth: 0,
			})
		}()
	}
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

// handleImageGenerations is an OpenAI-compatible POST /v1/images/generations endpoint.
// It routes to the RunPod A1111 image gen pod (lazy spin-up on first request).
func (s *ServerV2) handleImageGenerations(c *gin.Context) {
	var req service.ImageGenRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Prompt == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "prompt is required"})
		return
	}

	if s.ImageGen == nil || !s.ImageGen.IsEnabled() {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":   "image generation is not enabled",
			"hint":    "Set RUNPOD_IMAGEGEN_ENABLED=true in .env and restart",
			"warming": false,
		})
		return
	}

	if s.ImageGen.WarmingUp() {
		c.JSON(http.StatusAccepted, gin.H{
			"error":   "image engine is warming up, retry in ~60s",
			"warming": true,
			"status":  s.ImageGen.Status(),
		})
		return
	}

	b64, err := s.ImageGen.GenerateImage(c.Request.Context(), req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error(), "warming": s.ImageGen.WarmingUp()})
		return
	}

	c.JSON(http.StatusOK, service.ImageGenResponse{
		Created: time.Now().Unix(),
		Data: []struct {
			B64JSON string `json:"b64_json"`
		}{{B64JSON: b64}},
	})
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

// handleSovereignAuth handles /admin <key>, /exec <key>, and /auth off.
// The raw key is scrubbed from all logs immediately.
func (s *ServerV2) handleSovereignAuth(c *gin.Context, rawMsg, sessionKey string) {
	scrubbed := sovereign.ScrubKey(rawMsg)
	log.Printf("[SovereignAuth] auth attempt from %s: %s", sessionKey, scrubbed)

	trimmed := strings.TrimSpace(rawMsg)
	lower := strings.ToLower(trimmed)

	chatID := fmt.Sprintf("chatcmpl-%d", time.Now().Unix())
	respond := func(msg string) {
		c.JSON(http.StatusOK, gin.H{
			"id": chatID, "object": "chat.completion",
			"choices": []gin.H{{"index": 0, "message": gin.H{"role": "assistant", "content": msg}, "finish_reason": "stop"}},
		})
	}

	if lower == "/auth off" {
		s.SovAuth.InvalidateSession(sessionKey)
		respond("🔒 Sovereign session ended.")
		return
	}

	// Extract key — everything after the command word (/admin or /exec)
	parts := strings.SplitN(trimmed, " ", 2)
	if len(parts) < 2 || strings.TrimSpace(parts[1]) == "" {
		respond("Usage: `/admin <key>` or `/exec <key>` — `/auth off` to end session.")
		return
	}
	rawKey := strings.TrimSpace(parts[1])

	level, err := s.SovAuth.Authenticate(rawKey, sessionKey)
	if err != nil {
		log.Printf("[SovereignAuth] failed auth from %s: %v", sessionKey, err)
		respond(fmt.Sprintf("❌ Authentication failed: %s", err.Error()))
		return
	}

	levelName := "ADMIN"
	capabilities := "elevated chat · full technical detail · no response softening"
	if level >= sovereign.LevelExec {
		levelName = "EXEC"
		capabilities = "elevated chat · full technical detail · system commands (!status, !logs, !df, !modules…)"
	}

	respond(fmt.Sprintf(
		"✅ **Sovereign session established — Level %d (%s)**\n\nCapabilities unlocked: %s\n\nSession expires in 1 hour of inactivity. Type `/auth off` to end.",
		level, levelName, capabilities,
	))
}

// --- DAG Goal Handlers ---

func (s *ServerV2) handleListGoals(c *gin.Context) {
	if s.GoalService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "goal service not available"})
		return
	}
	status := c.Query("status") // optional filter: pending | active | completed | failed
	goals, err := s.GoalService.ListObjectives(status)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"goals": goals, "count": len(goals)})
}

func (s *ServerV2) handleCreateGoal(c *gin.Context) {
	if s.GoalService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "goal service not available"})
		return
	}
	var body struct {
		Goal      string                 `json:"goal"`
		Priority  int                    `json:"priority"`
		DependsOn []string               `json:"depends_on"`
		Metadata  map[string]interface{} `json:"metadata"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || body.Goal == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "goal field required"})
		return
	}
	if body.Priority == 0 {
		body.Priority = 5 // default priority
	}
	meta := body.Metadata
	if meta == nil {
		meta = map[string]interface{}{}
	}
	if len(body.DependsOn) > 0 {
		meta["depends_on_raw"] = body.DependsOn
	}
	id, err := s.GoalService.AddObjectiveWithDeps(body.Goal, body.Priority, meta, body.DependsOn)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, gin.H{"id": id, "goal": body.Goal})
}

func (s *ServerV2) handleUpdateGoal(c *gin.Context) {
	if s.GoalService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "goal service not available"})
		return
	}
	id := c.Param("id")
	var updates map[string]interface{}
	if err := c.ShouldBindJSON(&updates); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	found, err := s.GoalService.UpdateObjective(id, updates)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if !found {
		c.JSON(http.StatusNotFound, gin.H{"error": "goal not found"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"updated": id})
}

func (s *ServerV2) handleDeleteGoal(c *gin.Context) {
	if s.GoalService == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "goal service not available"})
		return
	}
	id := c.Param("id")
	found, err := s.GoalService.DeleteObjective(id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if !found {
		c.JSON(http.StatusNotFound, gin.H{"error": "goal not found"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"deleted": id})
}

// handleListMemories proxies GET /v1/memories to PocketBase.
// Query params: source, author, topic, page (default 1), perPage (default 20, max 100).
func (s *ServerV2) handleListMemories(c *gin.Context) {
if s.MemoryBank == nil || !s.MemoryBank.IsEnabled() {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "memory bank not available"})
return
}

ctx := c.Request.Context()
source := c.DefaultQuery("source", "")
author := c.DefaultQuery("author", "")
topic := c.DefaultQuery("topic", "")
page := 1
perPage := 20
if v := c.Query("page"); v != "" {
if n, err := strconv.Atoi(v); err == nil && n > 0 {
page = n
}
}
if v := c.Query("perPage"); v != "" {
if n, err := strconv.Atoi(v); err == nil && n > 0 && n <= 100 {
perPage = n
}
}

items, total, err := s.MemoryBank.ListMemories(ctx, source, author, topic, page, perPage)
if err != nil {
c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
return
}
c.JSON(http.StatusOK, gin.H{
"items":   items,
"total":   total,
"page":    page,
"perPage": perPage,
})
}

// handleListKnowledge proxies GET /v1/memories/knowledge to PocketBase.
// Query params: topic, author, page (default 1), perPage (default 20, max 100).
func (s *ServerV2) handleListKnowledge(c *gin.Context) {
if s.MemoryBank == nil || !s.MemoryBank.IsEnabled() {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "memory bank not available"})
return
}

ctx := c.Request.Context()
topic := c.DefaultQuery("topic", "")
author := c.DefaultQuery("author", "")
page := 1
perPage := 20
if v := c.Query("page"); v != "" {
if n, err := strconv.Atoi(v); err == nil && n > 0 {
page = n
}
}
if v := c.Query("perPage"); v != "" {
if n, err := strconv.Atoi(v); err == nil && n > 0 && n <= 100 {
perPage = n
}
}

items, total, err := s.MemoryBank.ListKnowledgeFragments(ctx, topic, author, page, perPage)
if err != nil {
c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
return
}
c.JSON(http.StatusOK, gin.H{
"items":   items,
"total":   total,
"page":    page,
"perPage": perPage,
})
}

// handleDaemonHealth returns live status of all autonomous background daemons.
// Used by the Goals UI mission control panel to show what Oricli is currently doing.
func (s *ServerV2) handleDaemonHealth(c *gin.Context) {
type DaemonStatus struct {
Name      string `json:"name"`
Status    string `json:"status"`
Detail    string `json:"detail,omitempty"`
}

var daemons []DaemonStatus

// CuriosityDaemon
if cd := s.ActionRouter.CuriosityDaemon; cd != nil {
idle := cd.IdleSince()
qDepth := cd.SeedQueueDepth()
status := "idle"
detail := fmt.Sprintf("idle for %s | %d seeds queued", idle.Round(time.Second), qDepth)
if idle < 30*time.Second {
status = "active"
}
daemons = append(daemons, DaemonStatus{Name: "CuriosityDaemon", Status: status, Detail: detail})
}

// GoalExecutor
if s.GoalExecutor != nil {
goals, _ := s.GoalService.ListObjectives("active")
status := "idle"
detail := "no active objectives"
if len(goals) > 0 {
status = "active"
detail = fmt.Sprintf("executing: %q", goals[0].Goal)
}
daemons = append(daemons, DaemonStatus{Name: "GoalExecutor", Status: status, Detail: detail})
}

// ReformDaemon — always running (Reform is on SovEngine)
daemons = append(daemons, DaemonStatus{Name: "ReformDaemon", Status: "running", Detail: "self-modification audit loop"})

// DreamDaemon — always running
daemons = append(daemons, DaemonStatus{Name: "DreamDaemon", Status: "running", Detail: "memory consolidation loop"})

c.JSON(http.StatusOK, gin.H{"daemons": daemons})
}

// handleDocumentUpload accepts a multipart file upload and ingests it into MemoryBank.
func (s *ServerV2) handleDocumentUpload(c *gin.Context) {
	if err := c.Request.ParseMultipartForm(32 << 20); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "failed to parse form: " + err.Error()})
		return
	}

	file, header, err := c.Request.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "missing 'file' field"})
		return
	}
	defer file.Close()

	filename := header.Filename
	ext := strings.ToLower(filepath.Ext(filename))
	allowed := map[string]string{
		".txt": "text/plain",
		".md":  "text/markdown",
		".csv": "text/csv",
		".pdf": "application/pdf",
	}
	mimeType, ok := allowed[ext]
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unsupported file type: " + ext})
		return
	}

	data, err := io.ReadAll(file)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to read file"})
		return
	}

	if s.DocumentIngestor == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "document ingestor not available"})
		return
	}

	n, err := s.DocumentIngestor.Ingest(c.Request.Context(), filename, data, mimeType)
	if err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{"error": err.Error()})
		return
	}

	docs := s.DocumentIngestor.ListDocs()
	var id string
	for _, d := range docs {
		if d.Filename == filename {
			id = d.ID
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"filename": filename,
		"chunks":   n,
		"id":       id,
	})
}

// handleListDocuments returns all previously ingested documents.
func (s *ServerV2) handleListDocuments(c *gin.Context) {
	if s.DocumentIngestor == nil {
		c.JSON(http.StatusOK, gin.H{"documents": []interface{}{}})
		return
	}
	c.JSON(http.StatusOK, gin.H{"documents": s.DocumentIngestor.ListDocs()})
}

// ─── Reaction Feedback ────────────────────────────────────────────────────────

// handleReactionFeedback stores a user's emoji reaction to an assistant message
// as a MemoryFragment so it influences future RAG recall and sentiment weighting.
func (s *ServerV2) handleReactionFeedback(c *gin.Context) {
var req struct {
MessageID   string  `json:"message_id"`
Reaction    string  `json:"reaction"`    // e.g. "thumbs_up", "heart", "fire"
IsPositive  bool    `json:"is_positive"`
MsgPreview  string  `json:"message_preview"` // first 200 chars of assistant message
SessionID   string  `json:"session_id"`
}
if err := c.ShouldBindJSON(&req); err != nil || req.Reaction == "" {
c.JSON(http.StatusBadRequest, gin.H{"error": "reaction and message_id required"})
return
}

feedbackType := "positive"
importance := 0.8
if !req.IsPositive {
feedbackType = "negative"
importance = 0.9 // negative feedback is a sharper learning signal
}

content := fmt.Sprintf(
"User reacted with %s (%s) to message: %q",
req.Reaction, feedbackType, req.MsgPreview,
)

keywords := extractFeedbackKeywords(req.MsgPreview)
topic := "feedback:" + feedbackType
if len(keywords) > 0 {
topic = "feedback:" + keywords[0]
}

frag := service.MemoryFragment{
ID:         "fb-" + req.MessageID,
Content:    content,
Source:     "feedback",
Topic:      topic,
SessionID:  req.SessionID,
Importance: importance,
Provenance: service.ProvenanceUserStated, // user explicitly rated — highest trust
Volatility: service.VolatilityStable,
}

if s.MemoryBank != nil {
s.MemoryBank.Write(frag)
}

c.JSON(http.StatusOK, gin.H{
"ok":          true,
"feedback":    feedbackType,
"reaction":    req.Reaction,
"importance":  importance,
"keywords":    keywords,
})
}

// handleGetSovereignIdentity returns the active sovereign .ori profile as JSON.
func (s *ServerV2) handleGetSovereignIdentity(c *gin.Context) {
	p := s.Agent.SovEngine.ActiveProfile
	if p == nil {
		c.JSON(http.StatusOK, gin.H{
			"name": "oricli", "description": "", "archetype": "friend",
			"sass_factor": 0.65, "energy": "moderate",
			"instructions": []string{}, "rules": []string{},
		})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"name":         p.Name,
		"description":  p.Description,
		"archetype":    p.Archetype,
		"sass_factor":  p.SassFactor,
		"energy":       p.Energy,
		"instructions": p.Instructions,
		"rules":        p.Rules,
	})
}

// handlePutSovereignIdentity writes an updated .ori profile to disk,
// reloads the registry, and hot-swaps the active profile without a restart.
func (s *ServerV2) handlePutSovereignIdentity(c *gin.Context) {
	var req struct {
		Name         string   `json:"name"`
		Description  string   `json:"description"`
		Archetype    string   `json:"archetype"`
		SassFactor   float64  `json:"sass_factor"`
		Energy       string   `json:"energy"`
		Instructions []string `json:"instructions"`
		Rules        []string `json:"rules"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Name == "" {
		req.Name = "oricli"
	}

	// Build .ori file content
	var b strings.Builder
	b.WriteString("# Sovereign Identity Profile — auto-saved from UI\n\n")
	b.WriteString("@profile_name: " + req.Name + "\n")
	b.WriteString("@description: " + req.Description + "\n")
	b.WriteString("@archetype: " + req.Archetype + "\n")
	b.WriteString(fmt.Sprintf("@sass_factor: %.2f\n", req.SassFactor))
	b.WriteString("@energy: " + req.Energy + "\n\n")

	if len(req.Instructions) > 0 {
		b.WriteString("<instructions>\n")
		for _, line := range req.Instructions {
			if strings.TrimSpace(line) != "" {
				b.WriteString("- " + strings.TrimSpace(line) + "\n")
			}
		}
		b.WriteString("</instructions>\n\n")
	}

	if len(req.Rules) > 0 {
		b.WriteString("<rules>\n")
		for _, line := range req.Rules {
			if strings.TrimSpace(line) != "" {
				b.WriteString("- " + strings.TrimSpace(line) + "\n")
			}
		}
		b.WriteString("</rules>\n")
	}

	oriPath := filepath.Join(s.Agent.SovEngine.Profiles.Dir, req.Name+".ori")
	if err := os.WriteFile(oriPath, []byte(b.String()), 0644); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to write profile: " + err.Error()})
		return
	}

	// Hot-reload registry and swap active profile — no restart needed
	s.Agent.SovEngine.Profiles.Reload()
	if p, ok := s.Agent.SovEngine.Profiles.GetProfile(req.Name); ok {
		s.Agent.SovEngine.ActiveProfile = p
		log.Printf("[API] Sovereign identity updated and hot-swapped: %s", req.Name)
	}

	c.JSON(http.StatusOK, gin.H{"ok": true, "saved": req.Name + ".ori"})
}

// extractFeedbackKeywords pulls the top-5 meaningful words from a message preview.
func extractFeedbackKeywords(text string) []string {
stopWords := map[string]bool{
"this": true, "that": true, "with": true, "from": true, "have": true,
"about": true, "there": true, "their": true, "which": true, "while": true,
"where": true, "what": true, "when": true, "your": true, "into": true,
"over": true, "under": true, "through": true, "many": true, "some": true,
"really": true, "just": true, "like": true, "them": true, "they": true,
"you": true, "here": true, "the": true, "and": true, "for": true,
"are": true, "was": true, "were": true, "been": true, "being": true,
}

words := strings.Fields(strings.ToLower(text))
counts := map[string]int{}
for _, w := range words {
// strip punctuation
clean := strings.Trim(w, `.,!?;:"'()[]`)
if len(clean) > 3 && !stopWords[clean] {
counts[clean]++
}
}

type wc struct{ w string; c int }
var ranked []wc
for w, c := range counts {
ranked = append(ranked, wc{w, c})
}
sort.Slice(ranked, func(i, j int) bool { return ranked[i].c > ranked[j].c })

out := make([]string, 0, 5)
for i, r := range ranked {
if i >= 5 { break }
out = append(out, r.w)
}
return out
}
