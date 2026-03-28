package api

import (
	"bufio"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/cache"
	"github.com/thynaptic/oricli-go/pkg/cognition"
	"github.com/thynaptic/oricli-go/pkg/connectors/runpod"
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
	ResponseCache    *cache.ResponseCache
	SignalProcessor  *service.SignalProcessor
	Constitution     *service.LivingConstitution
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

	// Bootstrap semantic response cache — L1 (hash) + L2 (chromem-go vectors).
	// Cache misses fall through to LLM normally. Zero impact on latency on miss.
	s.ResponseCache = cache.New(".memory", service.NewEmbedder())

	// Bootstrap Living Constitution and Signal Processor for The Imprint learning loop.
	lc := service.NewLivingConstitution()
	s.Constitution = lc
	s.SignalProcessor = service.NewSignalProcessor(mb, lc)
	agent.SovEngine.Constitution = lc

	// Inject MemoryBank into SovereignEngine via adapter (avoids cognition→service import cycle).
	adapter := &memoryBankAdapter{mb: mb}
	agent.SovEngine.MemoryBankRef = adapter
	agent.SovEngine.CertaintyUpdaterRef = adapter
	// VisionRef: route to RunPod GPU pod when enabled, fall back to local Ollama stub.
	if os.Getenv("RUNPOD_VISION_ENABLED") == "true" {
		apiKey := os.Getenv("RUNPOD_API_KEY")
		if apiKey == "" {
			apiKey = os.Getenv("OricliAlpha_Key")
		}
		agent.SovEngine.VisionRef = service.NewRunPodVisionManager(runpod.NewClient(apiKey))
	} else {
		agent.SovEngine.VisionRef = &visionAdapter{ollamaURL: ollamaBaseURL()}
	}

	s.setupRoutes()

	// Seed API key from env — allows scripts/benchmark tools to auth without
	// a database round-trip to generate keys. Set ORICLI_SEED_API_KEY=glm.<prefix>.<secret>
	// in .env or the systemd service file. The key is registered (or re-registered)
	// every startup so it survives DB wipes.
	if seedKey := os.Getenv("ORICLI_SEED_API_KEY"); seedKey != "" {
		go func() {
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()
			if _, err := s.auth.RegisterAPIKey(ctx, seedKey, "default", []string{"chat", "read", "write"}, nil); err != nil {
				log.Printf("[ServerV2] seed key register error (may already exist): %v", err)
			} else {
				log.Printf("[ServerV2] seed API key registered")
			}
		}()
	}

	// Pre-warm Ollama model in the background so the first user request
	// doesn't pay the cold-load penalty (~60-90s on CPU-only VPS).
	go func() {
		time.Sleep(5 * time.Second) // let backbone fully initialize first
		log.Printf("[ServerV2] Pre-warming Ollama model...")
		warmCtx, warmCancel := context.WithTimeout(context.Background(), 120*time.Second)
		defer warmCancel()
		warmMsgs := []map[string]string{{"role": "user", "content": "hi"}}
		ch, err := s.Agent.GenService.ChatStream(warmCtx, warmMsgs, map[string]interface{}{
			"options": map[string]interface{}{"num_predict": 3, "num_ctx": 4096},
		})
		if err != nil {
			log.Printf("[ServerV2] Model warmup failed: %v", err)
			return
		}
		for range ch { /* drain */ }
		log.Printf("[ServerV2] Model warmup complete — first request will be fast")
	}()

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
	// Public share route — no auth, serves HTML/code/markdown directly
	s.Router.GET("/share/:id", s.handleGetShare)

	v1 := s.Router.Group("/v1")

	// Public
	v1.GET("/health", s.handleHealth)
	v1.GET("/eri", s.handleERI)
	v1.GET("/ws", s.handleWS)
	v1.GET("/traces", s.handleGetTraces)
	v1.GET("/loglines", s.handleLogLines)
	v1.GET("/modules", s.handleListModules)
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

		// Canvas shares — create a permanent public share link
		protected.POST("/share", s.handleCreateShare)

		// Agent Vibe Studio — natural language agent creation
		protected.POST("/agents/vibe", s.handleAgentVibe)

		// Vision — image analysis via moondream (CPU-safe, local Ollama)
		protected.POST("/vision/analyze", s.handleVisionAnalyze)

		// Sovereign Identity — active .ori profile editor
		protected.GET("/sovereign/identity", s.handleGetSovereignIdentity)
		protected.PUT("/sovereign/identity", s.handlePutSovereignIdentity)
	}
}

func (s *ServerV2) handleHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ready", "system": "oricli-alpha-v2", "pure_go": true})
}

// handleERI returns the current Ecospheric Resonance Index and swarm state.
// This is a public endpoint — no auth required — polled by the ORI Studio UI
// to drive real-time accent color and surface tone shifts.
func (s *ServerV2) handleERI(c *gin.Context) {
	res := s.Agent.SovEngine.Resonance.Current
	c.JSON(http.StatusOK, gin.H{
		"eri":        res.ERI,
		"ers":        res.ERS,
		"pacing":     res.Pacing,
		"volatility": res.Volatility,
		"coherence":  res.Coherence,
		"musical_key": res.MusicalKey,
		"bpm":        res.BPM,
		"state":      s.Agent.SovEngine.Resonance.GetStateDescription(),
	})
}

// handleListModules returns the live skills + registered Go modules.
// Public endpoint — used by ORI Studio's Hive panel for node labelling.
func (s *ServerV2) handleListModules(c *gin.Context) {
	type moduleEntry struct {
		ID          string   `json:"id"`
		Name        string   `json:"name"`
		Description string   `json:"description,omitempty"`
		Kind        string   `json:"kind"`
		Triggers    []string `json:"triggers,omitempty"`
		Status      string   `json:"status"`
	}

	var entries []moduleEntry

	// Skills loaded from .ori skill files
	if s.Skills != nil {
		for _, sk := range s.Skills.ListSkills() {
			entries = append(entries, moduleEntry{
				ID:          sk.Name,
				Name:        sk.Name,
				Description: sk.Description,
				Kind:        "skill",
				Triggers:    sk.Triggers,
				Status:      "active",
			})
		}
	}

	c.JSON(http.StatusOK, gin.H{"modules": entries, "count": len(entries)})
}

func (s *ServerV2) handleChatCompletions(c *gin.Context) {
	var req model.ChatCompletionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Studio requests (ORI Studio vibe chat) must NOT pollute general memory — DSL workflow
	// responses written to MemoryBank would bleed into identity/capability RAG recalls.
	isStudioContext := c.GetHeader("X-Ori-Context") == "studio"

	// Session ID used by BeliefStateTracker (fog-of-war) and downstream session scoping.
	sessionID := c.GetHeader("X-Session-ID")

	modelName := req.Model
	// oricli-bench: benchmark/direct mode — no sovereign pipeline, no mutex, just Ollama
	isBenchMode := modelName == "oricli-bench" || c.GetHeader("X-Benchmark-Mode") == "true"
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

	// Detect canvas/code context early — needed for safety gate tuning.
	// Canvas: large token budget or explicit header. ORI Studio IDE sets X-Canvas-Mode.
	// The /v1/studio/vibe endpoint also sets X-Canvas-Mode via its own handler.
	isCodeCtx := (req.MaxTokens != nil && *req.MaxTokens >= 8192) ||
		c.GetHeader("X-Canvas-Mode") == "true" ||
		c.GetHeader("X-Code-Context") == "true"

	if blocked, refusal := s.Agent.SovEngine.CheckInputSafetyWithHistory(history, sessionKey, isCodeCtx); blocked {
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

	// useSSE: stream:true (or default for UI) → SSE; stream:false → buffer + return JSON.
	// Non-streaming clients (LiveBench, curl, SDK callers) must send stream:false.
	// The UI always sends stream:true (or omits it, defaulting to SSE via request header).
	useSSE := req.Stream
	log.Printf("[DEBUG] handleChatCompletions: stream=%v useSSE=%v model=%s", req.Stream, useSSE, req.Model)
	// ── Semantic response cache check ────────────────────────────────────────
	// L1 (exact hash) is always checked. L2 (vector) only when model is idle.
	// On hit: stream the cached response as SSE (or return JSON for non-streaming).
	if s.ResponseCache != nil && lastMsg != "" {
		if cached, hit := s.ResponseCache.Get(c.Request.Context(), lastMsg); hit {
			chatID := fmt.Sprintf("chatcmpl-%d", time.Now().Unix())
			if !useSSE {
				c.JSON(http.StatusOK, gin.H{
					"id": chatID, "object": "chat.completion",
					"choices": []gin.H{{"index": 0, "message": gin.H{"role": "assistant", "content": cached}, "finish_reason": "stop"}},
					"usage": gin.H{"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
				})
				return
			}
			c.Header("Content-Type", "text/event-stream")
			c.Header("Cache-Control", "no-cache")
			c.Header("X-Accel-Buffering", "no")
			c.Header("X-Cache", "HIT")
			c.Writer.WriteString(": keep-alive\n\n")
			chunk := map[string]interface{}{
				"id":     chatID,
				"object": "chat.completion.chunk",
				"choices": []map[string]interface{}{
					{"index": 0, "delta": map[string]interface{}{"role": "assistant", "content": cached}, "finish_reason": nil},
				},
			}
			data, _ := json.Marshal(chunk)
			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
			doneChunk := map[string]interface{}{
				"id":     chatID,
				"object": "chat.completion.chunk",
				"choices": []map[string]interface{}{
					{"index": 0, "delta": map[string]interface{}{}, "finish_reason": "stop"},
				},
			}
			data, _ = json.Marshal(doneChunk)
			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
			c.Writer.Flush()
			return
		}
	}

	chatID := fmt.Sprintf("chatcmpl-%d", time.Now().Unix())

	heartbeatDone := make(chan struct{})
	if useSSE {
		// Commit to SSE NOW — before any blocking I/O (ProcessInference, Ollama warm-up).
		// Cloudflare's idle timeout clock starts from the TCP handshake. Without this,
		// ProcessInference (~3s) + Ollama model-load (up to 60s) + first-token latency
		// can easily exceed 100s before a single byte is written, triggering a 524.
		c.Header("Content-Type", "text/event-stream")
		c.Header("Cache-Control", "no-cache")
		c.Header("X-Accel-Buffering", "no")
		c.Writer.WriteString(": keep-alive\n\n")
		c.Writer.Flush()

		// Pipeline heartbeat — keeps the CF/browser connection alive during the
		// blocking pipeline stages (ProcessInference + RAG embed, up to 90s).
		// The main token-stream ticker takes over once ChatStream starts.
		go func() {
			t := time.NewTicker(15 * time.Second)
			defer t.Stop()
			for {
				select {
				case <-t.C:
					c.Writer.WriteString(": keep-alive\n\n")
					c.Writer.Flush()
				case <-heartbeatDone:
					return
				case <-ctx.Done():
					return
				}
			}
		}()
	}

	// Helper to emit an error — SSE chunk when streaming, JSON otherwise.
	sseError := func(msg string) {
		if !useSSE {
			c.JSON(http.StatusInternalServerError, gin.H{"error": msg})
			return
		}
		errChunk := map[string]interface{}{
			"id":     chatID,
			"object": "chat.completion.chunk",
			"choices": []map[string]interface{}{
				{"index": 0, "delta": map[string]interface{}{"role": "assistant", "content": "\n\n[Error: " + msg + "]"}, "finish_reason": "stop"},
			},
		}
		data, _ := json.Marshal(errChunk)
		c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
		c.Writer.Flush()
	}

	// Mark chat model as active — prevents Embed() from cold-loading all-minilm
	// and evicting qwen3 from Ollama's single memory slot during the pipeline.
	service.SetChatModelActive(true)
	defer service.SetChatModelActive(false)

	// ── Benchmark / direct mode ──────────────────────────────────────────────
	// oricli-bench or X-Benchmark-Mode:true skips ProcessInference entirely.
	// No sovereign pipeline, no mutex contention, no reasoning mode LLM calls.
	// Pure direct: minimal system prompt + Ollama ChatStream.
	if isBenchMode {
		benchMsgs := []map[string]string{
			{"role": "system", "content": "You are ORI, a helpful and accurate AI assistant. Answer concisely and correctly."},
		}
		for _, m := range req.Messages {
			benchMsgs = append(benchMsgs, map[string]string{"role": m.Role, "content": m.Content})
		}
		benchOpts := map[string]interface{}{
			"options": map[string]interface{}{"num_predict": 512, "num_ctx": 4096},
		}
		benchCh, benchErr := s.Agent.GenService.ChatStream(c.Request.Context(), benchMsgs, benchOpts)
		if benchErr != nil {
			sseError(benchErr.Error())
			return
		}
		if useSSE { close(heartbeatDone) }
		var benchBuf strings.Builder
		for tok := range benchCh {
			benchBuf.WriteString(tok)
			if useSSE {
				chunk := map[string]interface{}{
					"id": chatID, "object": "chat.completion.chunk",
					"choices": []map[string]interface{}{
						{"index": 0, "delta": map[string]interface{}{"role": "assistant", "content": tok}, "finish_reason": nil},
					},
				}
				data, _ := json.Marshal(chunk)
				c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
				c.Writer.Flush()
			}
		}
		if useSSE {
			doneChunk := map[string]interface{}{
				"id": chatID, "object": "chat.completion.chunk",
				"choices": []map[string]interface{}{{"index": 0, "delta": map[string]interface{}{}, "finish_reason": "stop"}},
			}
			data, _ := json.Marshal(doneChunk)
			c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
			c.Writer.Flush()
		} else {
			c.JSON(http.StatusOK, gin.H{
				"id": chatID, "object": "chat.completion", "model": "oricli-bench",
				"choices": []gin.H{{"index": 0, "message": gin.H{"role": "assistant", "content": benchBuf.String()}, "finish_reason": "stop"}},
				"usage": gin.H{"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
			})
		}
		return
	}


	// For clearly multi-step prompts (research + compare + save chains), build
	// a Task DAG and execute it deterministically before the main LLM call.
	// The accumulated results are injected as rich context into the system prompt.
	// Single-step prompts fall through without any overhead.
	var taskContext string
	if cognition.IsMultiStep(lastMsg) {
		if tasks := cognition.DecomposePrompt(lastMsg); len(tasks) > 0 {
			sseEmitter := func(eventType string, payload interface{}) {
				data, err := json.Marshal(map[string]interface{}{
					"event":   eventType,
					"payload": payload,
				})
				if err != nil {
					return
				}
				c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
				c.Writer.Flush()
			}
			svc := cognition.TaskServices{
				Searcher: s.Agent.SovEngine.SearXNG,
				MemoryBank: s.MemoryBank,
				Generator:  s.Agent.GenService,
			}
			exec := cognition.NewTaskExecutor(svc, sseEmitter)
			taskContext, _ = exec.Run(c.Request.Context(), tasks)
		}
	}

	// Set per-request session ID so BeliefStateTracker can maintain per-session fog-of-war state.
	s.Agent.SovEngine.CurrentSessionID = sessionID

	sovTrace, err := s.Agent.SovEngine.ProcessInference(ctx, lastMsg)
	if err != nil {
		sseError("sovereign engine failure")
		return
	}

	// SELF-DISCOVER plan persistence: if a new plan was discovered this request,
	// write it to MemoryBank as ProvenanceSolved so DreamDaemon can consolidate
	// effective reasoning structures into the Living Constitution.
	if !isStudioContext && s.MemoryBank != nil && s.MemoryBank.IsEnabled() {
		fp := cognition.GetLastDiscoveredFingerprint()
		if fp != "" {
			go func(fingerprint, query string) {
				plan, ok := cognition.GetCachedPlan(fingerprint)
				if !ok {
					return
				}
				s.MemoryBank.Write(service.MemoryFragment{
					Content:    fmt.Sprintf("SELF-DISCOVER plan for [%s]: %s", fingerprint, plan.RawJSON),
					Source:     "self_discover",
					Topic:      "reasoning_plan:" + fingerprint,
					Importance: 0.8,
					Provenance: service.ProvenanceSolved,
				})
			}(fp, lastMsg)
		}
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
	if taskContext != "" {
		systemContent = sovTrace + "\n\n--- TASK RESEARCH CONTEXT ---\n" + taskContext
	}
	if clientSystem != "" {
		systemContent = sovTrace + "\n\n---\n\n" + clientSystem
	}

	// Inject relevant long-term memories as RAG context prefix.
	// Use a short deadline — if the embedder is cold (model evicted), we skip RAG
	// rather than blocking the user for 90s waiting for all-minilm to reload.
	if s.MemoryBank != nil && s.MemoryBank.IsEnabled() && lastMsg != "" {
		ragCtx_ctx, ragCancel := context.WithTimeout(c.Request.Context(), 8*time.Second)
		frags, ragErr := s.MemoryBank.QuerySimilar(ragCtx_ctx, lastMsg, 5)
		ragCancel()
		if ragErr == nil && len(frags) > 0 {
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
		// Cap at 4096 — covers full landing pages, Python scripts, and multi-section docs.
		// The 524 fix is the keep-alive flush above, not this cap — CF resets its timer
		// on every streaming chunk, so mid-generation timeouts aren't the concern.
		streamOpts["options"] = map[string]interface{}{
			"num_predict": 4096,
			"num_ctx":     16384,
		}
	} else {
		// Inference-time compute scaling (Gemini Deep Think law): scale num_predict
		// with query complexity so high-complexity queries get deeper reasoning depth.
		// Complexity is computed once in DetermineBudget — free, < 1ms.
		budget := cognition.DetermineBudget(lastMsg)
		scaledPredict := budget.ScaledNumPredict()
		streamOpts["options"] = map[string]interface{}{
			"num_predict": scaledPredict,
			"num_ctx":     4096,
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
		if useSSE { close(heartbeatDone) }
		sseError(err.Error())
		return
	}
	// Stop pipeline heartbeat — token-stream ticker takes over from here.
	if useSSE { close(heartbeatDone) }

	// Emit agent_dispatch SSE event before the first token so the UI renders
	// the dispatch card immediately
	if dispatch != nil && useSSE {
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
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()
	streamDone := false
	for !streamDone {
		select {
		case token, ok := <-tokenCh:
			if !ok {
				streamDone = true
				if useSSE {
					doneChunk := map[string]interface{}{
						"id":     chatID,
						"object": "chat.completion.chunk",
						"choices": []map[string]interface{}{
							{"index": 0, "delta": map[string]interface{}{}, "finish_reason": "stop"},
						},
					}
					data, _ := json.Marshal(doneChunk)
					c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
					c.Writer.Flush()
				}
			} else {
				ticker.Reset(15 * time.Second)
				responseBuilder.WriteString(token)
				if useSSE {
					chunk := map[string]interface{}{
						"id":     chatID,
						"object": "chat.completion.chunk",
						"choices": []map[string]interface{}{
							{"index": 0, "delta": map[string]interface{}{"role": "assistant", "content": token}, "finish_reason": nil},
						},
					}
					data, _ := json.Marshal(chunk)
					c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", string(data)))
					c.Writer.Flush()
				}
			}
		case <-ticker.C:
			if useSSE {
				// No token in 15s — punch through Cloudflare's idle timer
				c.Writer.WriteString(": keep-alive\n\n")
				c.Writer.Flush()
			}
		case <-c.Request.Context().Done():
			streamDone = true
		}
	}

	// Post-stream: async jobs on the full assembled response
	responseText := responseBuilder.String()
	if isCanvasMode {
		responseText, _ = s.Agent.SovEngine.AuditCanvasOutput(responseText)
	} else {
		responseText, _ = s.Agent.SovEngine.AuditOutput(responseText)
	}

	// Non-streaming response — return buffered result as plain JSON now that we have it.
	if !useSSE {
		c.JSON(http.StatusOK, gin.H{
			"id":     chatID,
			"object": "chat.completion",
			"model":  modelName,
			"choices": []gin.H{{
				"index":         0,
				"message":       gin.H{"role": "assistant", "content": responseText},
				"finish_reason": "stop",
			}},
			"usage": gin.H{"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
		})
		return
	}
	// Store in semantic cache — async, never blocks. Skips canvas/code outputs
	// (too context-specific to be reusable) and action-dispatched responses.
	if s.ResponseCache != nil && lastMsg != "" && !isCanvasMode && dispatch == nil {
		s.ResponseCache.Put(lastMsg, responseText)
	}

	// SCAI Critique-Revision loop — fires in background to preserve streaming latency.
	// If a constitutional violation is detected, a scai_correction WS event is broadcast
	// so the UI can patch the last assistant message in-place with the revised text.
	// This also generates an RFAL DPO pair for every violation (learning signal).
	// Zero impact on the happy path (CLEAR critique → goroutine exits silently).
	go func(query, response, sid string) {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		corrected, violated := s.Agent.SovEngine.SelfAlign(ctx, query, response)
		if !violated {
			// Clean response — write as ProvenanceSolved for CBR future use.
			// This teaches Oricli what a good answer looks like for this class of problem.
			if s.MemoryBank != nil && s.MemoryBank.IsEnabled() && len(query) > 20 && len(response) > 50 {
				words := strings.Fields(query)
				if len(words) > 5 { words = words[:5] }
				go s.MemoryBank.Write(service.MemoryFragment{
					Content:    fmt.Sprintf("Q: %s\n\nA: %s", query, truncateStr(response, 600)),
					Source:     "solved",
					Topic:      strings.Join(words, " "),
					Importance: 0.75,
					Provenance: service.ProvenanceSolved,
				})
			}
			return
		}
		s.Agent.SovEngine.WSHub.BroadcastEvent("scai_correction", map[string]interface{}{
			"session_id":       sid,
			"corrected":        corrected,
			"original_preview": response[:min(120, len(response))],
		})
	}(lastMsg, responseText, sessionID)

	// ExploiterLeague — 3 async specialists audit every response post-stream (AlphaStar League).
	// FactChecker, LogicAuditor, ClarityProbe each fire a ≤128-token LLM probe.
	// Medium/High findings land on the LeagueBlackboard for DreamDaemon consolidation.
	if !isStudioContext {
		cognition.RunLeagueWithConsensus(s.Agent.GenService, lastMsg, responseText)
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

	// Conversation write-back: persist this exchange to PocketBase long-term memory.
	// Only when both sides have meaningful content. Fires in background, never blocks.
	// Skip for studio context — DSL workflow responses must not pollute general RAG.
	if !isStudioContext && s.MemoryBank != nil && s.MemoryBank.IsEnabled() &&
		len(lastMsg) > 50 && len(responseText) > 50 {
		go func() {
			// Strip HTML tags before storing — prevents <span class="ori-kw"> and similar
			// UI syntax-highlighted content from polluting RAG recall.
			cleanMsg := stripHTML(lastMsg)
			cleanResp := stripHTML(responseText)

			// Extract a short topic from the user's message (first 5 words)
			words := strings.Fields(cleanMsg)
			if len(words) > 5 {
				words = words[:5]
			}
			topic := strings.Join(words, " ")

			// Combine user + assistant turn, cap response at 400 chars
			resp := cleanResp
			if len(resp) > 400 {
				resp = resp[:400] + "…"
			}
			combined := fmt.Sprintf("User: %s\n\nOricli: %s", cleanMsg, resp)

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

	// Signal detection: scan user message for learning signals (corrections, explicit teaches).
	// Fires async — never blocks the response. Sub-millisecond on cache hit.
	// Skip for studio context — DSL prompts would be misclassified as behavioral teaches.
	if !isStudioContext && s.SignalProcessor != nil && len(lastMsg) > 10 {
		go func(msg string) {
			sig := s.SignalProcessor.Detect(msg)
			s.SignalProcessor.Process(sig)
		}(lastMsg)
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

// 📌 Gold bookmark: pin reaction elevates the Q→A pair to ProvenanceGold tier.
	// Gold memories are never recycled, get 1.6x RAG weight, DreamDaemon consolidates them first.
	isPin := req.Reaction == "📌" || req.Reaction == "pin" || req.Reaction == "bookmark"
	if isPin && req.IsPositive && s.MemoryBank != nil && s.MemoryBank.IsEnabled() && len(req.MsgPreview) > 20 {
		goldFrag := service.MemoryFragment{
			ID:         "gold-" + req.MessageID,
			Content:    "GOLD: " + req.MsgPreview,
			Source:     "user_bookmark",
			Topic:      "gold:" + topic,
			SessionID:  req.SessionID,
			Importance: 1.0,
			Provenance: service.ProvenanceGold,
			Volatility: service.VolatilityStable,
		}
		s.MemoryBank.Write(goldFrag)
	}

	if s.MemoryBank != nil {
	s.MemoryBank.Write(frag)
}

	// Contrastive pair: store ACCEPTED/REJECTED alongside the standard feedback fragment.
	// This gives RAG a paired view of what worked and what didn't on each topic.
	if s.SignalProcessor != nil {
		go s.SignalProcessor.ProcessContrastivePair(req.IsPositive, topic, req.MsgPreview)
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

// reHTML strips HTML tags and decodes common entities.
// Used to sanitize content before writing to MemoryBank so highlighted
// UI output (e.g. <span class="ori-kw">workflow</span>) never poisons RAG.
var reHTMLTag = regexp.MustCompile(`<[^>]+>`)

func stripHTML(s string) string {
	s = reHTMLTag.ReplaceAllString(s, "")
	s = strings.ReplaceAll(s, "&amp;", "&")
	s = strings.ReplaceAll(s, "&lt;", "<")
	s = strings.ReplaceAll(s, "&gt;", ">")
	s = strings.ReplaceAll(s, "&quot;", `"`)
	s = strings.ReplaceAll(s, "&#39;", "'")
	return s
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

// ─── MemoryBank adapter (cognition.MemoryQuerier) ─────────────────────────────
// Bridges *service.MemoryBank to the cognition.MemoryQuerier interface without
// creating an import cycle. Converts service.MemoryFragment → cognition.MemFrag.
// Certainty is derived from provenance tier per AI-Supervisor uncertainty model
// (arXiv:2603.24402): U=0 (verified, Certainty≥0.80) vs U=1 (unverified, <0.80).

type memoryBankAdapter struct {
mb *service.MemoryBank
}

// provenanceCertainty maps service provenance tiers to AI-Supervisor factual confidence floors.
// Gold/Solved/UserStated are empirically verified (U=0); Synthetic tiers are unverified (U=1).
// This sets the Belief.Factual floor before access-bonus reinforcement is applied.
func provenanceCertainty(prov service.Provenance) float64 {
	switch prov {
	case service.ProvenanceGold:
		return 0.95
	case service.ProvenanceSolved, service.ProvenanceUserStated:
		return 0.90
	case service.ProvenanceWebVerified:
		return 0.85
	case service.ProvenanceSeen: // image-derived — reliable but vision models hallucinate details
		return 0.70
	case service.ProvenanceContrastive:
		return 0.75
	case service.ProvenanceConversation:
		return 0.65
	case service.ProvenanceSyntheticL1:
		return 0.55
	default: // SyntheticL2+, unknown
		return 0.45
	}
}

func (a *memoryBankAdapter) QuerySimilarWeighted(ctx context.Context, query string, topN int, weights cognition.BeliefWeights) ([]cognition.MemFrag, error) {
	// Oversample 3× from PB so the re-ranker has a meaningful candidate pool.
	// PB pre-sorts by cosine+provenance; we then re-rank by the caller's weight vector.
	oversample := topN * 3
	if oversample < 9 {
		oversample = 9
	}
	frags, err := a.mb.QuerySimilar(ctx, query, oversample)
	if err != nil {
		return nil, err
	}

	// Build MemFrag slice with full Belief axes populated.
	candidates := make([]cognition.MemFrag, len(frags))
	for i, f := range frags {
		mf := cognition.MemFrag{
			ID:            f.ID,
			Content:       f.Content,
			Source:        f.Source,
			Topic:         f.Topic,
			Importance:    f.Importance,
			CausalScore:   f.CausalScore,
			AccessCount:   f.AccessCount,
			Volatility:    string(f.Volatility),
			CreatedAt:     f.CreatedAt,
			SemanticScore: f.SemanticScore,
			Belief:        cognition.Belief{Factual: provenanceCertainty(f.Provenance)},
		}
		mf.Belief = cognition.ComputeBelief(mf)
		candidates[i] = mf
	}

	// Re-rank by caller's multi-objective weight vector.
	nw := weights.Normalize()
	type scored struct {
		frag  cognition.MemFrag
		score float64
	}
	ranked := make([]scored, len(candidates))
	for i, c := range candidates {
		ranked[i] = scored{frag: c, score: nw.WeightedScore(c)}
	}
	// Insertion sort — candidate pool is small (≤27), no need for stdlib sort import.
	for i := 1; i < len(ranked); i++ {
		for j := i; j > 0 && ranked[j].score > ranked[j-1].score; j-- {
			ranked[j], ranked[j-1] = ranked[j-1], ranked[j]
		}
	}

	// Trim to topN.
	if topN > len(ranked) {
		topN = len(ranked)
	}
	out := make([]cognition.MemFrag, topN)
	for i := range out {
		out[i] = ranked[i].frag
	}

	// ── Retrieval audit log (benchmark observability) ─────────────────────────
	// One DEBUG line per retrieval: weights label + top-3 frag scores.
	// Allows per-mode retrieval quality analysis without extra infrastructure.
	if topN > 0 {
		label := beliefWeightsLabel(weights)
		n := 3
		if n > topN {
			n = topN
		}
		var sb strings.Builder
		for i := 0; i < n; i++ {
			f := out[i]
			fmt.Fprintf(&sb, "(F:%.2f C:%.2f R:%.2f s:%.2f) ",
				f.Belief.Factual, f.Belief.Causal, f.Belief.Recency, ranked[i].score)
		}
		log.Printf("[MemRetrieval] mode=%s top%d=%s", label, n, strings.TrimSpace(sb.String()))
	}

	return out, nil
}

// beliefWeightsLabel returns a human-readable label for a BeliefWeights vector
// by matching against the known presets. Falls back to "custom".
func beliefWeightsLabel(w cognition.BeliefWeights) string {
	type preset struct {
		name string
		w    cognition.BeliefWeights
	}
	presets := []preset{
		{"aletheia", cognition.WeightsAletheia},
		{"fivewhy", cognition.WeightsFiveWhy},
		{"react", cognition.WeightsReAct},
		{"cbr", cognition.WeightsCBR},
		{"standard", cognition.WeightsStandard},
	}
	for _, p := range presets {
		if math.Abs(p.w.Factual-w.Factual) < 0.01 &&
			math.Abs(p.w.Causal-w.Causal) < 0.01 &&
			math.Abs(p.w.Recency-w.Recency) < 0.01 {
			return p.name
		}
	}
	return fmt.Sprintf("custom(F:%.2f C:%.2f R:%.2f S:%.2f)", w.Factual, w.Causal, w.Recency, w.Semantic)
}

func (a *memoryBankAdapter) QuerySolved(ctx context.Context, topic string, limit int) ([]cognition.MemFrag, error) {
	frags, err := a.mb.QuerySolved(ctx, topic, limit)
	if err != nil {
		return nil, err
	}
	out := make([]cognition.MemFrag, len(frags))
	for i, f := range frags {
		mf := cognition.MemFrag{
			ID:          f.ID,
			Content:     f.Content,
			Source:      f.Source,
			Topic:       f.Topic,
			Importance:  f.Importance,
			CausalScore: f.CausalScore,
			AccessCount: f.AccessCount,
			Volatility:  string(f.Volatility),
			CreatedAt:   f.CreatedAt,
			Belief:      cognition.Belief{Factual: provenanceCertainty(f.Provenance)},
		}
		mf.Belief = cognition.ComputeBelief(mf)
		out[i] = mf
	}
	return out, nil
}

// BumpBelief implements cognition.CertaintyUpdater.
// Routes axis-specific belief mutations to the correct PB field.
// "factual"  → importance field (evidence quality, corroboration signal)
// "causal"   → causal_score field (mechanism depth, 5-WHY signal)
// "recency"  → no-op (always computed from age, never stored)
// Fires async via goroutine in Aletheia/5-WHY so it never blocks the generation path.
func (a *memoryBankAdapter) BumpBelief(ctx context.Context, fragID string, axis string, delta float64) {
	switch axis {
	case "factual":
		a.mb.BumpImportance(ctx, fragID, delta)
	case "causal":
		a.mb.BumpCausalScore(ctx, fragID, delta)
	// "recency" is intentionally a no-op — computed at query time from age
	}
}

func truncateStr(s string, n int) string {
if len(s) <= n { return s }
return s[:n] + "…"
}

// ─── Vision Adapter ───────────────────────────────────────────────────────────

// ollamaBaseURL returns the Ollama API base URL from env or default.
func ollamaBaseURL() string {
if u := os.Getenv("OLLAMA_URL"); u != "" {
return u
}
return "http://127.0.0.1:11434"
}

// visionAdapter implements cognition.VisionAnalyzer using moondream via Ollama.
// CPU-safe: moondream is 1.7GB and runs on EPYC in ~5-8s per image.
type visionAdapter struct {
ollamaURL string
}

func (v *visionAdapter) Analyze(input cognition.VisionInput) (cognition.VisionResult, error) {
// Resolve image to base64
var b64 string
switch {
case input.Base64 != "":
b64 = input.Base64
case input.FilePath != "":
data, err := os.ReadFile(input.FilePath)
if err != nil {
return cognition.VisionResult{}, fmt.Errorf("vision: read file: %w", err)
}
b64 = base64.StdEncoding.EncodeToString(data)
case input.URL != "":
resp, err := http.Get(input.URL) //nolint:gosec — URL provided by authenticated caller
if err != nil {
return cognition.VisionResult{}, fmt.Errorf("vision: fetch url: %w", err)
}
defer resp.Body.Close()
data, err := io.ReadAll(resp.Body)
if err != nil {
return cognition.VisionResult{}, fmt.Errorf("vision: read url body: %w", err)
}
b64 = base64.StdEncoding.EncodeToString(data)
default:
return cognition.VisionResult{}, fmt.Errorf("vision: no image source provided")
}

prompt := input.Prompt
if prompt == "" {
prompt = cognition.DefaultVisionPrompt
}

// Call Ollama /api/generate with images array
reqBody, _ := json.Marshal(map[string]any{
"model":       "moondream:latest",
"prompt":      prompt,
"images":      []string{b64},
"stream":      false,
"num_predict": 256,
"options": map[string]any{
"temperature": 0.1,
"num_ctx":     4096,
},
})

ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
defer cancel()

req, _ := http.NewRequestWithContext(ctx, http.MethodPost,
v.ollamaURL+"/api/generate", strings.NewReader(string(reqBody)))
req.Header.Set("Content-Type", "application/json")

httpResp, err := http.DefaultClient.Do(req)
if err != nil {
return cognition.VisionResult{}, fmt.Errorf("vision: ollama call: %w", err)
}
defer httpResp.Body.Close()

var ollamaResp struct {
Response string `json:"response"`
Done     bool   `json:"done"`
}
if err := json.NewDecoder(httpResp.Body).Decode(&ollamaResp); err != nil {
return cognition.VisionResult{}, fmt.Errorf("vision: decode response: %w", err)
}

description := strings.TrimSpace(ollamaResp.Response)
tags := extractVisionTags(description)

return cognition.VisionResult{
Description: description,
Tags:        tags,
Model:       "moondream:latest",
RawResponse: ollamaResp.Response,
}, nil
}

// extractVisionTags derives a small set of concept tags from a description
// by pulling capitalised nouns and key technical terms (heuristic, no LLM call).
func extractVisionTags(description string) []string {
words := strings.Fields(description)
seen := map[string]bool{}
var tags []string
for _, w := range words {
w = strings.Trim(w, ".,;:!?\"'()")
if len(w) < 4 {
continue
}
lower := strings.ToLower(w)
if seen[lower] {
continue
}
// Keep words that start with a capital (proper nouns / concepts) or are technical
if w[0] >= 'A' && w[0] <= 'Z' {
seen[lower] = true
tags = append(tags, lower)
}
if len(tags) >= 8 {
break
}
}
return tags
}

// handleVisionAnalyze handles POST /v1/vision/analyze.
// Accepts image_url, image_base64, or image_path + optional prompt.
// Optionally writes result to MemoryBank with ProvenanceSeen tier.
func (s *ServerV2) handleVisionAnalyze(c *gin.Context) {
var req struct {
ImageURL    string `json:"image_url"`
ImageBase64 string `json:"image_base64"`
ImagePath   string `json:"image_path"`
Prompt      string `json:"prompt"`
SaveMemory  bool   `json:"save_memory"`
}
if err := c.ShouldBindJSON(&req); err != nil {
c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
return
}

va := s.Agent.SovEngine.VisionRef
if va == nil {
c.JSON(http.StatusServiceUnavailable, gin.H{"error": "vision module not available"})
return
}

result, err := va.Analyze(cognition.VisionInput{
URL:      req.ImageURL,
FilePath: req.ImagePath,
Base64:   req.ImageBase64,
Prompt:   req.Prompt,
})
if err != nil {
log.Printf("[Vision] Analysis error: %v", err)
c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
return
}

resp := gin.H{
"description": result.Description,
"tags":        result.Tags,
"model":       result.Model,
}

// Optional memory write-back with ProvenanceSeen tier
if req.SaveMemory && s.MemoryBank != nil && s.MemoryBank.IsEnabled() {
topic := "visual_input"
if len(result.Tags) > 0 {
topic = result.Tags[0]
}
source := req.ImageURL
if source == "" {
source = req.ImagePath
}
s.MemoryBank.Write(service.MemoryFragment{
Content:    result.Description,
Source:     "vision",
Topic:      topic,
Importance: 0.65,
Provenance: service.ProvenanceSeen,
Volatility: service.VolatilityCurrent,
})
resp["memory_saved"] = true
resp["memory_topic"] = topic
}

c.JSON(http.StatusOK, resp)
}
