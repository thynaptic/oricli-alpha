package api

import (
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/ori-capsule/internal/byok"
	"github.com/thynaptic/ori-capsule/internal/config"
	"github.com/thynaptic/ori-capsule/internal/safety"
)

type Server struct {
	cfg      config.Config
	router   *gin.Engine
	pipeline *safety.Pipeline
}

func New(cfg config.Config) *Server {
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	pipe := safety.NewPipeline()
	r.Use(gin.Recovery(), gin.Logger())
	s := &Server{cfg: cfg, router: r, pipeline: pipe}
	s.routes()
	return s
}

func (s *Server) routes() {
	v1 := s.router.Group("/v1")
	v1.GET("/health", s.handleHealth)

	protected := v1.Group("/", s.pipeline.RateLimiter.GinMiddleware())
	protected.GET("/models", s.resolveCreds, s.handleModels)
	protected.POST("/chat/completions", s.resolveCreds, s.handleChat)
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
	if sessionID == "" {
		sessionID = c.ClientIP()
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

	if blocked, refusal := s.pipeline.CheckInputWithHistory(turns, sessionID, codeCtx); blocked {
		s.pipeline.RateLimiter.RecordBlock(sessionID, "injection")
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

	surface := c.GetHeader("X-Ori-Surface")
	if surface == "" {
		surface = "default"
	}
	sysExtra := s.pipeline.ConstraintPrompt(lastUser, safety.ConstraintOptions{
		Surface:     surface,
		CodeContext: codeCtx,
		CanvasMode:  canvasMode,
	})
	req.Messages = injectSystem(req.Messages, sysExtra)

	ctx := c.Request.Context()
	if req.Stream {
		// Input gates + constraint prompt applied; SSE output sanitization is
		// deferred (buffering) — see SAFETY_SIDE.md.
		c.Header("Content-Type", "text/event-stream")
		c.Header("Cache-Control", "no-cache")
		c.Header("Connection", "keep-alive")
		c.Status(http.StatusOK)
		if err := byok.ChatStream(ctx, cred, req, c.Writer); err != nil {
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
	}
	c.JSON(http.StatusOK, out)
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
