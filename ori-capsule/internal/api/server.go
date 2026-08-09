package api

import (
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/ori-capsule/internal/byok"
	"github.com/thynaptic/ori-capsule/internal/config"
	"github.com/thynaptic/ori-capsule/internal/gosh"
	"github.com/thynaptic/ori-capsule/internal/memory"
	"github.com/thynaptic/ori-capsule/internal/safety"
)

type Server struct {
	cfg      config.Config
	router   *gin.Engine
	pipeline *safety.Pipeline
	mem      *memory.Runtime
	gosh     *gosh.Manager
}

func New(cfg config.Config) *Server {
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	pipe := safety.NewPipeline()
	mem, err := memory.Open(memory.OpenOptions{
		Dir:             cfg.MemoryDir,
		EncryptionKey:   cfg.MemoryKey,
		MaxSessionTurns: cfg.MaxSessionTurns,
	})
	if err != nil {
		panic(fmt.Sprintf("memory init: %v", err))
	}
	goshMgr := gosh.NewManager(gosh.Config{
		Enabled:     cfg.GoshEnabled,
		Workspace:   cfg.GoshWorkspace,
		ForceMem:    cfg.GoshForceMem,
		ExecTimeout: cfg.GoshExecTimeout,
	})
	r.Use(gin.Recovery(), gin.Logger())
	s := &Server{cfg: cfg, router: r, pipeline: pipe, mem: mem, gosh: goshMgr}
	s.routes()
	return s
}

func (s *Server) routes() {
	v1 := s.router.Group("/v1")
	v1.GET("/health", s.handleHealth)

	protected := v1.Group("/", s.pipeline.RateLimiter.GinMiddleware())
	protected.GET("/models", s.resolveCreds, s.handleModels)
	protected.POST("/chat/completions", s.resolveCreds, s.handleChat)

	// Consumer memory surfaces (local only — no enterprise RAG)
	protected.GET("/spaces", s.resolveCreds, s.handleSpacesList)
	protected.POST("/spaces", s.resolveCreds, s.handleSpacesUpsert)
	protected.GET("/tasks", s.resolveCreds, s.handleTasksList)
	protected.POST("/tasks", s.resolveCreds, s.handleTasksAdd)
	protected.PATCH("/tasks/:id", s.resolveCreds, s.handleTasksDone)

	// GOSH — per-request docker-friendly sandbox (no shared daemon state)
	protected.GET("/gosh", s.resolveCreds, s.handleGoshInfo)
	protected.POST("/gosh/run", s.resolveCreds, s.handleGoshRun)
}

func (s *Server) Run() error {
	addr := fmt.Sprintf(":%d", s.cfg.Port)
	return s.router.Run(addr)
}

func (s *Server) handleHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":    "ready",
		"system":    "ori-capsule",
		"byok":      true,
		"safety":    true,
		"memory":    true,
		"gosh":      s.gosh.Info(),
		"stream":    "sanitize",
		"providers": []string{"openai", "anthropic", "opencode"},
	})
}

func (s *Server) resolveCreds(c *gin.Context) {
	auth := c.GetHeader("Authorization")
	token := strings.TrimSpace(strings.TrimPrefix(auth, "Bearer"))
	if token == auth {
		token = strings.TrimSpace(strings.TrimPrefix(auth, "bearer"))
	}

	var llmKey string
	if s.cfg.CapsuleKey != "" {
		if token == "" || token != s.cfg.CapsuleKey {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "invalid capsule key"})
			return
		}
		llmKey = strings.TrimSpace(c.GetHeader("X-API-Key"))
		if llmKey == "" {
			llmKey = strings.TrimSpace(c.GetHeader("X-Api-Key"))
		}
		if llmKey == "" {
			c.AbortWithStatusJSON(http.StatusBadRequest, gin.H{"error": "X-API-Key required when ORI_CAPSULE_KEY is set"})
			return
		}
	} else {
		if token == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Authorization: Bearer <provider-api-key> required"})
			return
		}
		llmKey = token
	}

	provHdr := c.GetHeader("X-Provider")
	if provHdr == "" {
		provHdr = s.cfg.DefaultProvider
	}
	prov, err := byok.ParseProvider(provHdr)
	if err != nil {
		c.AbortWithStatusJSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	base := strings.TrimSpace(c.GetHeader("X-Base-URL"))
	if base == "" {
		base = strings.TrimSpace(c.GetHeader("X-Base-Url"))
	}
	if prov == byok.ProviderOpenCode && base == "" {
		base = s.cfg.OpenCodeBaseURL
	}

	c.Set("byok", byok.Credentials{Provider: prov, APIKey: llmKey, BaseURL: base})
	c.Next()
}

func (s *Server) handleModels(c *gin.Context) {
	cred := c.MustGet("byok").(byok.Credentials)
	c.JSON(http.StatusOK, gin.H{
		"object": "list",
		"data": []gin.H{
			{"id": "passthrough", "object": "model", "owned_by": string(cred.Provider)},
		},
		"note": "ori-capsule is BYOK — pass the upstream model id on chat/completions",
	})
}

func (s *Server) handleChat(c *gin.Context) {
	cred := c.MustGet("byok").(byok.Credentials)
	var req byok.ChatRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Model == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "model is required"})
		return
	}
	if len(req.Messages) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "messages is required"})
		return
	}

	sessionID := c.GetHeader("X-Session-ID")
	safetyKey := sessionID
	if safetyKey == "" {
		safetyKey = c.ClientIP()
	}

	turns := make([]safety.ChatTurn, 0, len(req.Messages))
	var lastUser string
	for _, m := range req.Messages {
		turns = append(turns, safety.ChatTurn{Role: m.Role, Content: m.Content})
		if m.Role == "user" {
			lastUser = m.Content
		}
	}

	canvasMode := strings.EqualFold(c.GetHeader("X-Ori-Surface"), "canvas") ||
		strings.Contains(strings.ToLower(lastUser), "canvas")
	codeCtx := canvasMode || strings.EqualFold(c.GetHeader("X-Ori-Surface"), "dev")

	if blocked, refusal := s.pipeline.CheckInputWithHistory(turns, safetyKey, codeCtx); blocked {
		s.pipeline.RateLimiter.RecordBlock(safetyKey, "injection")
		if req.Stream {
			s.writeSSEHeaders(c)
			_ = byok.WriteChatSSE(c.Writer,
				fmt.Sprintf("chatcmpl-blocked-%d", time.Now().UnixNano()),
				req.Model, refusal, "stop")
			return
		}
		c.JSON(http.StatusOK, gin.H{
			"id":      fmt.Sprintf("chatcmpl-blocked-%d", time.Now().UnixNano()),
			"object":  "chat.completion",
			"created": time.Now().Unix(),
			"model":   req.Model,
			"choices": []gin.H{{
				"index":         0,
				"finish_reason": "stop",
				"message":       gin.H{"role": "assistant", "content": refusal},
			}},
		})
		return
	}

	// Memory prepare: session merge + belief/clock/graph (no embeds).
	memMsgs := make([]memory.ChatMessage, len(req.Messages))
	for i, m := range req.Messages {
		memMsgs[i] = memory.ChatMessage{Role: m.Role, Content: m.Content}
	}
	expanded, memExtras, cacheHit := s.mem.PrepareChat(sessionID, memMsgs)
	if cacheHit != "" && !req.Stream {
		c.JSON(http.StatusOK, gin.H{
			"id":      fmt.Sprintf("chatcmpl-cache-%d", time.Now().UnixNano()),
			"object":  "chat.completion",
			"created": time.Now().Unix(),
			"model":   req.Model,
			"choices": []gin.H{{
				"index":         0,
				"finish_reason": "stop",
				"message":       gin.H{"role": "assistant", "content": cacheHit},
			}},
			"ori_cache": "l1",
		})
		return
	}
	if cacheHit != "" && req.Stream {
		s.writeSSEHeaders(c)
		_ = byok.WriteChatSSE(c.Writer,
			fmt.Sprintf("chatcmpl-cache-%d", time.Now().UnixNano()),
			req.Model, cacheHit, "stop")
		return
	}

	req.Messages = make([]byok.Message, len(expanded))
	for i, m := range expanded {
		req.Messages[i] = byok.Message{Role: m.Role, Content: m.Content}
	}

	surface := c.GetHeader("X-Ori-Surface")
	if surface == "" {
		surface = "default"
	}
	sysExtra := s.pipeline.ConstraintPrompt(lastUser, safety.ConstraintOptions{
		Surface:     surface,
		CodeContext: codeCtx,
		CanvasMode:  canvasMode,
	})
	if memExtras != "" {
		sysExtra = memExtras + "\n\n" + sysExtra
	}
	req.Messages = injectSystem(req.Messages, sysExtra)

	ctx := c.Request.Context()
	if req.Stream {
		s.writeSSEHeaders(c)
		collected, err := byok.CollectStream(ctx, cred, req)
		if err != nil {
			fmt.Fprintf(c.Writer, "data: {\"error\":%q}\n\n", err.Error())
			fmt.Fprintf(c.Writer, "data: [DONE]\n\n")
			return
		}
		sanitized, hardBlock := s.pipeline.SanitizeOutput(collected.Content, canvasMode)
		finish := collected.FinishReason
		if hardBlock {
			finish = "stop"
		}
		s.mem.AfterReply(sessionID, lastUser, sanitized)
		if err := byok.WriteChatSSE(c.Writer, collected.ID, collected.Model, sanitized, finish); err != nil {
			fmt.Fprintf(c.Writer, "data: {\"error\":%q}\n\n", err.Error())
		}
		return
	}

	out, err := byok.ChatNonStream(ctx, cred, req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	if out.Created == 0 {
		out.Created = time.Now().Unix()
	}
	if out.Object == "" {
		out.Object = "chat.completion"
	}
	if len(out.Choices) > 0 {
		sanitized, hardBlock := s.pipeline.SanitizeOutput(out.Choices[0].Message.Content, canvasMode)
		out.Choices[0].Message.Content = sanitized
		if hardBlock {
			out.Choices[0].FinishReason = "stop"
		}
		s.mem.AfterReply(sessionID, lastUser, sanitized)
	}
	c.JSON(http.StatusOK, out)
}

func (s *Server) writeSSEHeaders(c *gin.Context) {
	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("X-Accel-Buffering", "no")
	c.Status(http.StatusOK)
}

func injectSystem(msgs []byok.Message, extra string) []byok.Message {
	if strings.TrimSpace(extra) == "" {
		return msgs
	}
	out := make([]byok.Message, 0, len(msgs)+1)
	if len(msgs) > 0 && msgs[0].Role == "system" {
		out = append(out, byok.Message{Role: "system", Content: msgs[0].Content + "\n\n" + extra})
		out = append(out, msgs[1:]...)
		return out
	}
	out = append(out, byok.Message{Role: "system", Content: extra})
	out = append(out, msgs...)
	return out
}

func (s *Server) handleSpacesList(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"spaces": s.mem.Spaces.List()})
}

func (s *Server) handleSpacesUpsert(c *gin.Context) {
	var req struct {
		ID   string `json:"id"`
		Name string `json:"name"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || req.ID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "id required"})
		return
	}
	c.JSON(http.StatusOK, s.mem.Spaces.Upsert(req.ID, req.Name))
}

func (s *Server) handleTasksList(c *gin.Context) {
	tasks, err := s.mem.Tasks.List(50)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"tasks": tasks})
}

func (s *Server) handleTasksAdd(c *gin.Context) {
	var req struct {
		Title string `json:"title"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || strings.TrimSpace(req.Title) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "title required"})
		return
	}
	task, err := s.mem.Tasks.Add(strings.TrimSpace(req.Title))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, task)
}

func (s *Server) handleTasksDone(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}
	var req struct {
		Done bool `json:"done"`
	}
	_ = c.ShouldBindJSON(&req)
	if err := s.mem.Tasks.SetDone(id, req.Done); err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"id": id, "done": req.Done})
}

func (s *Server) handleGoshInfo(c *gin.Context) {
	c.JSON(http.StatusOK, s.gosh.Info())
}

func (s *Server) handleGoshRun(c *gin.Context) {
	if !s.gosh.Enabled() {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "gosh disabled"})
		return
	}
	var req gosh.RunRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if strings.TrimSpace(req.Script) == "" && strings.TrimSpace(req.Source) == "" &&
		len(req.Files) == 0 && len(req.Tools) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "script, source, files, or tools required"})
		return
	}
	res := s.gosh.Run(c.Request.Context(), req)
	status := http.StatusOK
	if !res.ExitOK {
		status = http.StatusUnprocessableEntity
	}
	c.JSON(status, res)
}
