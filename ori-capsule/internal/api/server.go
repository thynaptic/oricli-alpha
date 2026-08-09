package api

import (
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/ori-capsule/internal/byok"
	"github.com/thynaptic/ori-capsule/internal/config"
)

type Server struct {
	cfg    config.Config
	router *gin.Engine
}

func New(cfg config.Config) *Server {
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Recovery(), gin.Logger())
	s := &Server{cfg: cfg, router: r}
	s.routes()
	return s
}

func (s *Server) routes() {
	v1 := s.router.Group("/v1")
	v1.GET("/health", s.handleHealth)
	v1.GET("/models", s.resolveCreds, s.handleModels)
	v1.POST("/chat/completions", s.resolveCreds, s.handleChat)
}

func (s *Server) Run() error {
	addr := fmt.Sprintf(":%d", s.cfg.Port)
	return s.router.Run(addr)
}

func (s *Server) handleHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":   "ready",
		"system":   "ori-capsule",
		"byok":     true,
		"providers": []string{"openai", "anthropic", "opencode"},
	})
}

// resolveCreds implements BYOK:
//   - If ORI_CAPSULE_KEY is set, Authorization must be that key; LLM key from X-API-Key.
//   - Otherwise Authorization Bearer is the LLM provider key.
// Provider from X-Provider (default ORI_DEFAULT_PROVIDER). Base URL from X-Base-URL.
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
	_ = sessionID // reserved for future capsule-side session memory

	ctx := c.Request.Context()
	if req.Stream {
		c.Header("Content-Type", "text/event-stream")
		c.Header("Cache-Control", "no-cache")
		c.Header("Connection", "keep-alive")
		c.Status(http.StatusOK)
		if err := byok.ChatStream(ctx, cred, req, c.Writer); err != nil {
			// headers may already be sent
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
	c.JSON(http.StatusOK, out)
}
