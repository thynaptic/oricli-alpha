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
	"github.com/thynaptic/ori-capsule/internal/rag"
	"github.com/thynaptic/ori-capsule/internal/reasoning"
	"github.com/thynaptic/ori-capsule/internal/safety"
)

type Server struct {
	cfg      config.Config
	router   *gin.Engine
	pipeline *safety.Pipeline
	mem      *memory.Runtime
	gosh     *gosh.Manager
	rag      *rag.Store
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
	ragStore, err := rag.Open(cfg.MemoryDir)
	if err != nil {
		panic(fmt.Sprintf("rag init: %v", err))
	}
	r.Use(gin.Recovery(), gin.Logger())
	s := &Server{cfg: cfg, router: r, pipeline: pipe, mem: mem, gosh: goshMgr, rag: ragStore}
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
	protected.GET("/gosh/lessons", s.resolveCreds, s.handleGoshLessons)
	protected.POST("/gosh/run", s.resolveCreds, s.handleGoshRun)

	// Local BM25 RAG (no embeds / chromem / PB) — see RAG.md
	protected.GET("/rag", s.resolveCreds, s.handleRagInfo)
	protected.POST("/rag/ingest", s.resolveCreds, s.handleRagIngest)
	protected.POST("/rag/query", s.resolveCreds, s.handleRagQuery)

	// Zero-extra-LLM reasoning pack — see REASONING.md
	protected.GET("/reasoning", s.resolveCreds, s.handleReasoningInfo)
	protected.POST("/reasoning/plan", s.resolveCreds, s.handleReasoningPlan)
	protected.POST("/reasoning/pins", s.resolveCreds, s.handleReasoningPins)
	protected.POST("/reasoning/resources", s.resolveCreds, s.handleReasoningResources)
	protected.POST("/reasoning/filter", s.resolveCreds, s.handleReasoningFilter)
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
		"rag":       s.rag.Stats(),
		"reasoning": true,
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

	// Zero-extra-LLM reasoning prepare (may trim elevated load; never retries).
	reasonMsgs := make([]reasoning.ChatMessage, len(expanded))
	for i, m := range expanded {
		reasonMsgs[i] = reasoning.ChatMessage{Role: m.Role, Content: m.Content}
	}
	prepared := reasoning.Prepare(reasonMsgs, lastUser)
	req.Messages = make([]byok.Message, len(prepared.Messages))
	for i, m := range prepared.Messages {
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
	if prepared.SystemExtra != "" {
		sysExtra = prepared.SystemExtra + "\n\n" + sysExtra
	}
	// GOSH action lessons (ActionTracker) — keyed by X-Session-ID; empty if none.
	if sessionID != "" {
		if lessons := s.gosh.LessonsFor(sessionID); lessons != "" {
			sysExtra = lessons + "\n\n" + sysExtra
		}
	}
	// Opt-in BM25 context only — default chat path stays free of RAG latency.
	if strings.EqualFold(strings.TrimSpace(c.GetHeader("X-Ori-RAG")), "bm25") && lastUser != "" {
		if ctx := s.rag.FormatContext(lastUser, rag.DefaultTopK, rag.DefaultMaxContextRunes); ctx != "" {
			sysExtra = ctx + "\n\n" + sysExtra
		}
	}
	req.Messages = injectSystem(req.Messages, sysExtra)
	c.Header("X-Ori-Reasoning-Hint", fmt.Sprint(prepared.Meta["reasoning_hint"]))
	c.Header("X-Ori-Process-Tier", fmt.Sprint(prepared.Meta["process_tier"]))
	c.Header("X-Ori-Search-Intent", fmt.Sprint(prepared.Meta["search_intent"]))
	if prepared.Meta["needs_search"] == true {
		c.Header("X-Ori-Needs-Search", "1")
	}

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

func (s *Server) handleGoshLessons(c *gin.Context) {
	sessionID := strings.TrimSpace(c.GetHeader("X-Session-ID"))
	if sessionID == "" {
		sessionID = strings.TrimSpace(c.Query("session_id"))
	}
	lessons := s.gosh.LessonsFor(sessionID)
	c.JSON(http.StatusOK, gin.H{
		"session_id": sessionID,
		"lessons":    lessons,
		"stats":      s.gosh.Actions().Stats(),
	})
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
	// Prefer body session_id; fall back to X-Session-ID so chat lessons align.
	if strings.TrimSpace(req.SessionID) == "" {
		req.SessionID = strings.TrimSpace(c.GetHeader("X-Session-ID"))
	}
	res := s.gosh.Run(c.Request.Context(), req)
	status := http.StatusOK
	if !res.ExitOK {
		status = http.StatusUnprocessableEntity
	}
	c.JSON(status, res)
}

func (s *Server) handleRagInfo(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"mode":    "bm25",
		"embeds":  false,
		"opt_in":  "X-Ori-RAG: bm25",
		"stats":   s.rag.Stats(),
		"ingest":  "POST /v1/rag/ingest",
		"query":   "POST /v1/rag/query",
		"note":    "VPS MemoryBank/chromem/PB sync RAG stays on the host — not ported",
	})
}

func (s *Server) handleRagIngest(c *gin.Context) {
	var req struct {
		Source   string            `json:"source"`
		Text     string            `json:"text"`
		Path     string            `json:"path"`
		Metadata map[string]string `json:"metadata"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	var (
		n   int
		err error
	)
	switch {
	case strings.TrimSpace(req.Text) != "":
		src := req.Source
		if src == "" {
			src = "inline"
		}
		n, err = s.rag.IngestText(src, req.Text, req.Metadata)
	case strings.TrimSpace(req.Path) != "":
		n, err = s.rag.IngestFile(req.Path, req.Metadata)
	default:
		c.JSON(http.StatusBadRequest, gin.H{"error": "text or path required"})
		return
	}
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"added": n, "stats": s.rag.Stats()})
}

func (s *Server) handleRagQuery(c *gin.Context) {
	var req struct {
		Query string `json:"query"`
		TopK  int    `json:"top_k"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || strings.TrimSpace(req.Query) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "query required"})
		return
	}
	hits := s.rag.Query(req.Query, req.TopK)
	out := make([]gin.H, 0, len(hits))
	for _, h := range hits {
		out = append(out, gin.H{
			"id":       h.ID,
			"score":    h.Score,
			"content":  h.Content,
			"metadata": h.Metadata,
		})
	}
	c.JSON(http.StatusOK, gin.H{
		"hits":    out,
		"context": s.rag.FormatContext(req.Query, req.TopK, rag.DefaultMaxContextRunes),
	})
}

func (s *Server) handleReasoningInfo(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"mode":    "zero_extra_llm",
		"on_chat": []string{
			"precompute", "trapcheck", "response_plan", "dualprocess_classify", "cogload_trim",
			"reframe_inject", "rumination_inject", "mindset_inject", "search_intent", "uncertainty_caution",
		},
		"apis": []string{
			"POST /v1/reasoning/plan",
			"POST /v1/reasoning/pins",
			"POST /v1/reasoning/resources",
			"POST /v1/reasoning/filter",
		},
		"skipped": []string{"epistemics_multi_pass", "cot_tot_mcts", "debate_are_retry", "therapy", "searxng_fetch"},
		"note":    "Heuristics + single system inject only — no chat-path retries, multi-gen, or live web fetch",
	})
}

func (s *Server) handleReasoningPlan(c *gin.Context) {
	var req reasoning.PlanningRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if strings.TrimSpace(req.Goal) == "" && strings.TrimSpace(req.Notes) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "goal or notes required"})
		return
	}
	c.JSON(http.StatusOK, reasoning.BuildPlanningPlan(req))
}

func (s *Server) handleReasoningPins(c *gin.Context) {
	var req struct {
		Source      string                             `json:"source"`
		Now         string                             `json:"now"`
		Preferences reasoning.HomeLogisticsPreferences `json:"preferences"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || strings.TrimSpace(req.Source) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "source required"})
		return
	}
	planReq := reasoning.HomeLogisticsRequest{
		Source:      req.Source,
		Preferences: req.Preferences,
	}
	if ts := strings.TrimSpace(req.Now); ts != "" {
		if t, err := time.Parse(time.RFC3339, ts); err == nil {
			planReq.Now = t
		}
	}
	c.JSON(http.StatusOK, reasoning.BuildHomeLogisticsPlan(planReq))
}

func (s *Server) handleReasoningResources(c *gin.Context) {
	var req reasoning.CommitmentResourceRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, reasoning.ReasonAboutCommitmentResources(req))
}

func (s *Server) handleReasoningFilter(c *gin.Context) {
	var req struct {
		Topic string `json:"topic"`
		Text  string `json:"text"`
		URL   string `json:"url"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || strings.TrimSpace(req.Text) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "text required"})
		return
	}
	c.JSON(http.StatusOK, reasoning.EpistemicFilter(req.Topic, req.Text, req.URL))
}
