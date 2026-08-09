package api

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/ori-capsule/internal/agents"
	"github.com/thynaptic/ori-capsule/internal/byok"
	"github.com/thynaptic/ori-capsule/internal/config"
	"github.com/thynaptic/ori-capsule/internal/forge"
	"github.com/thynaptic/ori-capsule/internal/gosh"
	"github.com/thynaptic/ori-capsule/internal/memory"
	"github.com/thynaptic/ori-capsule/internal/rag"
	"github.com/thynaptic/ori-capsule/internal/reasoning"
	"github.com/thynaptic/ori-capsule/internal/reform"
	"github.com/thynaptic/ori-capsule/internal/safety"
	"github.com/thynaptic/ori-capsule/internal/skills"
	"github.com/thynaptic/ori-capsule/internal/tools"
)

type Server struct {
	cfg      config.Config
	router   *gin.Engine
	pipeline *safety.Pipeline
	mem      *memory.Runtime
	gosh     *gosh.Manager
	rag      *rag.Store
	skills   *skills.Library
	agents   *agents.Library
	tools    *tools.Registry
	forgeLib *forge.MemoryLibrary
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
	skillLib := skills.Open(cfg.SkillsDirs...)
	agentLib := agents.Open(cfg.AgentsDirs...)
	forgeLib := forge.NewMemoryLibrary(cfg.ForgeMaxTools, cfg.ForgeTTL)
	reg := tools.NewRegistry()
	tools.RegisterBuiltins(reg, tools.Deps{Mem: mem, Gosh: goshMgr, RAG: ragStore, Skills: skillLib})
	reg.SetDynamic(
		func(name string) (byok.ToolDefinition, tools.Handler, bool) {
			tool, ok := forgeLib.Get(name)
			if !ok {
				return byok.ToolDefinition{}, nil, false
			}
			params := tool.Parameters
			if params == nil {
				params = map[string]any{"type": "object", "properties": map[string]any{
					"input": map[string]any{"type": "string"},
				}}
			}
			def := byok.ToolDefinition{
				Type: "function",
				Function: byok.ToolFunction{
					Name:        tool.Name,
					Description: tool.Description,
					Parameters:  params,
				},
			}
			handler := func(args map[string]any) (string, error) {
				return tools.InvokeJIT(nil, goshMgr, tool, args)
			}
			return def, handler, true
		},
		func() []byok.ToolDefinition {
			list := forgeLib.List()
			out := make([]byok.ToolDefinition, 0, len(list))
			for _, tool := range list {
				params := tool.Parameters
				if params == nil {
					params = map[string]any{"type": "object", "properties": map[string]any{}}
				}
				out = append(out, byok.ToolDefinition{
					Type: "function",
					Function: byok.ToolFunction{
						Name: tool.Name, Description: tool.Description, Parameters: params,
					},
				})
			}
			return out
		},
	)
	r.Use(gin.Recovery(), gin.Logger())
	if len(cfg.CORSOrigins) > 0 {
		r.Use(corsMiddleware(cfg.CORSOrigins))
	}
	s := &Server{
		cfg: cfg, router: r, pipeline: pipe, mem: mem, gosh: goshMgr, rag: ragStore,
		skills: skillLib, agents: agentLib, tools: reg, forgeLib: forgeLib,
	}
	s.routes()
	return s
}

func corsMiddleware(origins []string) gin.HandlerFunc {
	allowAll := false
	set := map[string]bool{}
	for _, o := range origins {
		o = strings.TrimSpace(o)
		if o == "*" {
			allowAll = true
		}
		if o != "" {
			set[o] = true
		}
	}
	return func(c *gin.Context) {
		origin := c.GetHeader("Origin")
		allow := ""
		switch {
		case allowAll && origin != "":
			allow = origin
		case set[origin]:
			allow = origin
		case allowAll:
			allow = "*"
		}
		if allow != "" {
			c.Header("Access-Control-Allow-Origin", allow)
			c.Header("Vary", "Origin")
			c.Header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-API-Key, X-Provider, X-Base-URL, X-Session-ID, X-Ori-Surface, X-Ori-RAG, X-Ori-Tools, X-Ori-Agent, X-Ori-Model")
			c.Header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
			c.Header("Access-Control-Allow-Credentials", "true")
		}
		if c.Request.Method == http.MethodOptions {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		c.Next()
	}
}

func (s *Server) routes() {
	v1 := s.router.Group("/v1")
	v1.GET("/health", s.handleHealth)
	v1.GET("/ready", s.handleReady)
	v1.GET("/capabilities", s.handleCapabilities)

	protected := v1.Group("/", s.pipeline.RateLimiter.GinMiddleware())
	protected.GET("/models", s.resolveCreds, s.handleModels)
	protected.POST("/chat/completions", s.resolveCreds, s.handleChat)
	protected.GET("/tools", s.resolveCreds, s.handleToolsList)

	// Consumer memory surfaces (local only — no enterprise RAG)
	protected.GET("/spaces", s.resolveCreds, s.handleSpacesList)
	protected.POST("/spaces", s.resolveCreds, s.handleSpacesUpsert)
	protected.GET("/tasks", s.resolveCreds, s.handleTasksList)
	protected.POST("/tasks", s.resolveCreds, s.handleTasksAdd)
	protected.GET("/tasks/:id", s.resolveCreds, s.handleTasksGet)
	protected.PATCH("/tasks/:id", s.resolveCreds, s.handleTasksPatch)
	protected.POST("/tasks/:id/steps", s.resolveCreds, s.handleTasksAddStep)
	protected.PATCH("/tasks/:id/steps/:sid", s.resolveCreds, s.handleTasksPatchStep)
	protected.GET("/tasks/:id/ready", s.resolveCreds, s.handleTasksReady)

	// GOSH — per-request docker-friendly sandbox (no shared daemon state)
	protected.GET("/gosh", s.resolveCreds, s.handleGoshInfo)
	protected.GET("/gosh/lessons", s.resolveCreds, s.handleGoshLessons)
	protected.POST("/gosh/verify", s.resolveCreds, s.handleGoshVerify)
	protected.POST("/gosh/run", s.resolveCreds, s.handleGoshRun)

	// Skill / agent overlays — mount-only prompt inject
	protected.GET("/skills", s.resolveCreds, s.handleSkillsList)
	protected.GET("/agents", s.resolveCreds, s.handleAgentsList)

	// Light in-memory JIT forge (no PB / no go build)
	protected.GET("/forge/tools", s.resolveCreds, s.handleForgeList)
	protected.POST("/forge/propose", s.resolveCreds, s.handleForgePropose)
	protected.POST("/forge/register", s.resolveCreds, s.handleForgeRegister)
	protected.POST("/forge/tools/:name/invoke", s.resolveCreds, s.handleForgeInvoke)
	protected.DELETE("/forge/tools/:name", s.resolveCreds, s.handleForgeDelete)

	// Local BM25 RAG (no embeds / chromem / PB) — see RAG.md
	protected.GET("/rag", s.resolveCreds, s.handleRagInfo)
	protected.POST("/rag/ingest", s.resolveCreds, s.handleRagIngest)
	protected.POST("/rag/ingest/file", s.resolveCreds, s.handleRagIngestFile)
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
	c.JSON(http.StatusOK, s.capabilitiesPayload())
}

func (s *Server) handleReady(c *gin.Context) {
	dir := s.cfg.MemoryDir
	if err := os.MkdirAll(dir, 0o755); err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"status": "not_ready", "error": err.Error()})
		return
	}
	probe := filepath.Join(dir, ".ready")
	if err := os.WriteFile(probe, []byte(time.Now().UTC().Format(time.RFC3339)), 0o600); err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"status": "not_ready", "error": "memory dir not writable: " + err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"status":     "ready",
		"memory_dir": dir,
		"persistence": gin.H{
			"memory_tasks_rag": "volume (" + dir + ")",
			"jit_tools":        "ephemeral (process memory, TTL)",
			"skills_agents":    "mount read-only",
		},
	})
}

func (s *Server) handleCapabilities(c *gin.Context) {
	c.JSON(http.StatusOK, s.capabilitiesPayload())
}

func (s *Server) capabilitiesPayload() gin.H {
	return gin.H{
		"status":    "ready",
		"system":    "ori-capsule",
		"byok":      true,
		"safety":    true,
		"memory":    true,
		"gosh":      s.gosh.Info(),
		"rag":       s.rag.Stats(),
		"reasoning": true,
		"reform":    true,
		"skills":    s.skills.Stats(),
		"agents":    s.agents.Stats(),
		"tools":     s.tools.Names(),
		"forge":     s.forgeLib.Stats(),
		"stream":    "sanitize",
		"providers": []string{"openai", "anthropic", "opencode"},
		"headers": gin.H{
			"X-Provider":    "openai|anthropic|opencode",
			"X-Session-ID":  "session memory + gosh lessons",
			"X-Ori-Surface": "canvas|dev",
			"X-Ori-RAG":     "bm25",
			"X-Ori-Tools":   "passthrough|auto",
			"X-Ori-Agent":   "agent profile name",
		},
		"persistence": gin.H{
			"durable":   []string{"memory", "tasks", "spaces", "rag"},
			"ephemeral": []string{"forge_jit", "gosh_action_tracker"},
			"mounted":   []string{"skills", "agents", "gosh_workspace"},
		},
		"endpoints": []string{
			"/v1/health", "/v1/ready", "/v1/capabilities",
			"/v1/models", "/v1/chat/completions", "/v1/tools",
			"/v1/tasks", "/v1/spaces", "/v1/gosh", "/v1/rag",
			"/v1/skills", "/v1/agents", "/v1/forge/tools", "/v1/reasoning",
		},
	}
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
	list, err := byok.ListModels(c.Request.Context(), cred)
	if err != nil {
		if byok.IsCanceled(err) {
			c.Status(http.StatusRequestTimeout)
			return
		}
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, list)
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

	// Preserve client tools / tool history — prepare must not strip tool_calls.
	savedTools := req.Tools
	savedChoice := req.ToolChoice
	toolMode := strings.ToLower(strings.TrimSpace(c.GetHeader("X-Ori-Tools")))
	autoTools := toolMode == "auto"
	hasToolPayload := byok.HasToolPayload(req) || autoTools

	// Zero-extra-LLM reasoning prepare (may trim elevated load; never retries).
	reasonMsgs := make([]reasoning.ChatMessage, len(expanded))
	for i, m := range expanded {
		reasonMsgs[i] = reasoning.ChatMessage{Role: m.Role, Content: m.Content}
	}
	prepared := reasoning.Prepare(reasonMsgs, lastUser)
	if hasToolPayload {
		// Keep original tool-bearing transcript; only expand via memory already applied
		// to text turns is skipped here so tool_call_id chains stay valid.
		req.Messages = append([]byok.Message(nil), req.Messages...)
	} else {
		req.Messages = make([]byok.Message, len(prepared.Messages))
		for i, m := range prepared.Messages {
			req.Messages[i] = byok.Message{Role: m.Role, Content: m.Content}
		}
	}
	req.Tools = savedTools
	req.ToolChoice = savedChoice

	surface := c.GetHeader("X-Ori-Surface")
	if surface == "" {
		surface = "default"
	}
	sysExtra := s.pipeline.ConstraintPrompt(lastUser, safety.ConstraintOptions{
		Surface:     surface,
		CodeContext: codeCtx,
		CanvasMode:  canvasMode,
	})
	// Agent profile — X-Ori-Agent explicit, else default ori-chat-fast when mounted.
	if agent, ok := s.agents.Resolve(c.GetHeader("X-Ori-Agent")); ok {
		if block := agents.PromptBlock(agent); block != "" {
			sysExtra = block + "\n\n" + sysExtra
			c.Header("X-Ori-Agent", agent.Name)
		}
	}
	// Reform constitutions (prompt inject only — no ReformDaemon).
	if reformExtra := reform.PromptForSurface(canvasMode, codeCtx); reformExtra != "" {
		sysExtra = reformExtra + "\n\n" + sysExtra
	}
	// Skill overlays — first trigger match only (no extra LLM).
	if skillExtra := s.skills.Match(lastUser); skillExtra != "" {
		sysExtra = skillExtra + "\n\n" + sysExtra
	}
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
	if autoTools {
		c.Header("X-Ori-Tools", "auto")
	} else if len(req.Tools) > 0 || hasToolPayload {
		c.Header("X-Ori-Tools", "passthrough")
	}

	ctx := c.Request.Context()

	// Auto tool loop is non-stream (executes allowlisted tools server-side).
	if autoTools {
		out, err := tools.RunAutoLoop(ctx, cred, req, s.tools, tools.LoopOptions{
			MaxRounds:     tools.DefaultMaxRounds,
			InjectSchemas: true,
		})
		if err != nil {
			if byok.IsCanceled(err) {
				c.Status(499) // client closed request
				return
			}
			c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
			return
		}
		s.finalizeChatResponse(c, out, sessionID, lastUser, canvasMode)
		return
	}

	if req.Stream {
		s.writeSSEHeaders(c)
		collected, err := byok.CollectStream(ctx, cred, req)
		if err != nil {
			if byok.IsCanceled(err) || ctx.Err() != nil {
				return // client gone — stop quietly
			}
			fmt.Fprintf(c.Writer, "data: {\"error\":%q}\n\n", err.Error())
			fmt.Fprintf(c.Writer, "data: [DONE]\n\n")
			return
		}
		if ctx.Err() != nil {
			return
		}
		sanitized, hardBlock := s.pipeline.SanitizeOutput(collected.Content, canvasMode)
		finish := collected.FinishReason
		msg := byok.Message{Role: "assistant", Content: sanitized, ToolCalls: collected.ToolCalls}
		if hardBlock {
			finish = "stop"
			msg.ToolCalls = nil
		}
		if finish != "tool_calls" {
			s.mem.AfterReply(sessionID, lastUser, sanitized)
		}
		if err := byok.WriteChatSSEMessage(c.Writer, collected.ID, collected.Model, msg, finish); err != nil {
			if byok.IsCanceled(err) || ctx.Err() != nil {
				return
			}
			fmt.Fprintf(c.Writer, "data: {\"error\":%q}\n\n", err.Error())
		}
		return
	}

	out, err := byok.ChatNonStream(ctx, cred, req)
	if err != nil {
		if byok.IsCanceled(err) {
			c.Status(499)
			return
		}
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	s.finalizeChatResponse(c, out, sessionID, lastUser, canvasMode)
}

func (s *Server) finalizeChatResponse(c *gin.Context, out *byok.ChatResponse, sessionID, lastUser string, canvasMode bool) {
	if out.Created == 0 {
		out.Created = time.Now().Unix()
	}
	if out.Object == "" {
		out.Object = "chat.completion"
	}
	if len(out.Choices) > 0 {
		msg := &out.Choices[0].Message
		sanitized, hardBlock := s.pipeline.SanitizeOutput(msg.Content, canvasMode)
		msg.Content = sanitized
		if hardBlock {
			out.Choices[0].FinishReason = "stop"
			msg.ToolCalls = nil
		}
		if out.Choices[0].FinishReason != "tool_calls" {
			s.mem.AfterReply(sessionID, lastUser, sanitized)
		}
	}
	c.JSON(http.StatusOK, out)
}

func (s *Server) handleToolsList(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"mode": map[string]string{
			"passthrough": "default — forward tools/tool_calls to BYOK model; client executes",
			"auto":        "X-Ori-Tools: auto — server executes allowlisted tools and loops",
		},
		"tools": s.tools.Schemas(),
		"names": s.tools.Names(),
	})
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
	status := strings.TrimSpace(c.Query("status"))
	tasks, err := s.mem.Tasks.ListFilter(50, status)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"tasks": tasks})
}

func (s *Server) handleTasksAdd(c *gin.Context) {
	var req struct {
		Title       string             `json:"title"`
		Description string             `json:"description"`
		Priority    int                `json:"priority"`
		Steps       []memory.StepInput `json:"steps"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || strings.TrimSpace(req.Title) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "title required"})
		return
	}
	task, err := s.mem.Tasks.AddFull(strings.TrimSpace(req.Title), req.Description, req.Priority, req.Steps)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, task)
}

func (s *Server) handleTasksGet(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}
	task, err := s.mem.Tasks.Get(id, true)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, task)
}

func (s *Server) handleTasksPatch(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}
	var req struct {
		Done   *bool   `json:"done"`
		Status *string `json:"status"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	switch {
	case req.Status != nil:
		if err := s.mem.Tasks.SetStatus(id, memory.TaskStatus(*req.Status)); err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
			return
		}
	case req.Done != nil:
		if err := s.mem.Tasks.SetDone(id, *req.Done); err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
			return
		}
	default:
		c.JSON(http.StatusBadRequest, gin.H{"error": "done or status required"})
		return
	}
	task, _ := s.mem.Tasks.Get(id, true)
	c.JSON(http.StatusOK, task)
}

func (s *Server) handleTasksAddStep(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}
	var req memory.StepInput
	if err := c.ShouldBindJSON(&req); err != nil || strings.TrimSpace(req.Title) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "title required"})
		return
	}
	step, err := s.mem.Tasks.AddStep(id, req)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, step)
}

func (s *Server) handleTasksPatchStep(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}
	var req struct {
		Status string `json:"status"`
		Result string `json:"result"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || req.Status == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "status required"})
		return
	}
	step, err := s.mem.Tasks.SetStepStatus(id, c.Param("sid"), memory.TaskStatus(req.Status), req.Result)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, step)
}

func (s *Server) handleTasksReady(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}
	ready, err := s.mem.Tasks.ReadySteps(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"task_id": id, "ready": ready})
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

func (s *Server) handleGoshVerify(c *gin.Context) {
	var req struct {
		Script     string         `json:"script"`
		Source     string         `json:"source"`
		Tools      []gosh.ToolDef `json:"tools"`
		StrictTool bool           `json:"strict_tool"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	toolSrcs := make([]string, 0, len(req.Tools))
	for _, t := range req.Tools {
		toolSrcs = append(toolSrcs, t.Source)
	}
	res := forge.VerifyStatic(forge.VerifyRequest{
		Script:      req.Script,
		Source:      req.Source,
		ToolSources: toolSrcs,
		StrictTool:  req.StrictTool,
	})
	status := http.StatusOK
	if !res.OK {
		status = http.StatusUnprocessableEntity
	}
	c.JSON(status, res)
}

func (s *Server) handleSkillsList(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"stats":  s.skills.Stats(),
		"skills": s.skills.List(),
	})
}

func (s *Server) handleAgentsList(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"stats":  s.agents.Stats(),
		"agents": s.agents.List(),
	})
}

func (s *Server) handleForgeList(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"stats": s.forgeLib.Stats(),
		"tools": s.forgeLib.List(),
	})
}

func (s *Server) handleForgePropose(c *gin.Context) {
	cred := c.MustGet("byok").(byok.Credentials)
	var req forge.ProposeRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	model := strings.TrimSpace(req.Model)
	if model == "" {
		model = strings.TrimSpace(c.GetHeader("X-Ori-Model"))
	}
	if model == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "model required (body.model or X-Ori-Model)"})
		return
	}
	res, err := forge.Propose(c.Request.Context(), cred, model, req, s.forgeLib)
	if err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{"error": err.Error(), "result": res})
		return
	}
	c.JSON(http.StatusOK, res)
}

func (s *Server) handleForgeRegister(c *gin.Context) {
	var tool forge.JITTool
	if err := c.ShouldBindJSON(&tool); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	stored, err := s.forgeLib.Put(tool)
	if err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, stored)
}

func (s *Server) handleForgeInvoke(c *gin.Context) {
	name := c.Param("name")
	tool, ok := s.forgeLib.Get(name)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "tool not found or expired"})
		return
	}
	var args map[string]any
	_ = c.ShouldBindJSON(&args)
	out, err := tools.InvokeJIT(c.Request.Context(), s.gosh, tool, args)
	if err != nil {
		c.JSON(http.StatusUnprocessableEntity, gin.H{"error": err.Error(), "result": out})
		return
	}
	c.Data(http.StatusOK, "application/json", []byte(out))
}

func (s *Server) handleForgeDelete(c *gin.Context) {
	if !s.forgeLib.Delete(c.Param("name")) {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"deleted": c.Param("name")})
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
		"mode":   "bm25",
		"embeds": false,
		"opt_in": "X-Ori-RAG: bm25",
		"stats":  s.rag.Stats(),
		"ingest": "POST /v1/rag/ingest",
		"query":  "POST /v1/rag/query",
		"note":   "VPS MemoryBank/chromem/PB sync RAG stays on the host — not ported",
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

// handleRagIngestFile accepts multipart file upload → BM25 (no embeds).
// Form fields: file (required), source (optional), metadata JSON (optional).
func (s *Server) handleRagIngestFile(c *gin.Context) {
	fh, err := c.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "multipart field 'file' required"})
		return
	}
	const maxUpload = 2 << 20 // 2 MiB
	if fh.Size > maxUpload {
		c.JSON(http.StatusRequestEntityTooLarge, gin.H{"error": "file exceeds 2 MiB limit"})
		return
	}
	f, err := fh.Open()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	defer f.Close()
	data, err := io.ReadAll(io.LimitReader(f, maxUpload+1))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if len(data) > maxUpload {
		c.JSON(http.StatusRequestEntityTooLarge, gin.H{"error": "file exceeds 2 MiB limit"})
		return
	}
	src := strings.TrimSpace(c.PostForm("source"))
	if src == "" {
		src = fh.Filename
	}
	meta := map[string]string{"filename": fh.Filename}
	if raw := strings.TrimSpace(c.PostForm("metadata")); raw != "" {
		var extra map[string]string
		if jsonErr := json.Unmarshal([]byte(raw), &extra); jsonErr == nil {
			for k, v := range extra {
				meta[k] = v
			}
		}
	}
	n, err := s.rag.IngestText(src, string(data), meta)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"added": n, "source": src, "stats": s.rag.Stats()})
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
		"mode": "zero_extra_llm",
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
