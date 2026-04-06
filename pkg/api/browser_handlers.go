package api

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/service"
)

type browserCreateSessionRequest struct {
	Headless bool `json:"headless"`
	Viewport struct {
		Width  int `json:"width"`
		Height int `json:"height"`
	} `json:"viewport"`
}

type browserOpenRequest struct {
	SessionID string `json:"session_id"`
	URL       string `json:"url"`
	WaitUntil string `json:"wait_until"`
}

type browserActionRequest struct {
	SessionID  string `json:"session_id"`
	Action     string `json:"action"`
	Ref        string `json:"ref"`
	Selector   string `json:"selector"`
	Text       string `json:"text"`
	TextQuery  string `json:"text_query"`
	Label      string `json:"label"`
	Role       string `json:"role"`
	Name       string `json:"name"`
	URLPattern string `json:"url_pattern"`
	Key        string `json:"key"`
	TimeoutMs  int    `json:"timeout_ms"`
}

type browserScreenshotRequest struct {
	SessionID string `json:"session_id"`
	FullPage  bool   `json:"full_page"`
}

type browserCloseRequest struct {
	SessionID string `json:"session_id"`
}

type browserSaveStateRequest struct {
	SessionID string `json:"session_id"`
	StateName string `json:"state_name"`
}

type browserLoadStateRequest struct {
	StateName string `json:"state_name"`
	Headless  bool   `json:"headless"`
	Viewport  struct {
		Width  int `json:"width"`
		Height int `json:"height"`
	} `json:"viewport"`
}

func (s *ServerV2) browserContext(c *gin.Context) (context.Context, context.CancelFunc, bool) {
	if s.Browser == nil || !s.Browser.Enabled() {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "browser automation is disabled"})
		return nil, nil, false
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 45*time.Second)
	return ctx, cancel, true
}

func (s *ServerV2) handleBrowserHealth(c *gin.Context) {
	ctx, cancel, ok := s.browserContext(c)
	if !ok {
		return
	}
	defer cancel()

	healthy, sessions, err := s.Browser.Health(ctx)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"ok": false, "error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"ok": healthy, "sessions": sessions})
}

func (s *ServerV2) handleBrowserCreateSession(c *gin.Context) {
	ctx, cancel, ok := s.browserContext(c)
	if !ok {
		return
	}
	defer cancel()

	var req browserCreateSessionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	input := service.BrowserCreateSessionRequest{
		Headless: req.Headless,
	}
	input.Viewport.Width = req.Viewport.Width
	input.Viewport.Height = req.Viewport.Height

	resp, err := s.Browser.CreateSession(ctx, input)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, resp)
}

func (s *ServerV2) handleBrowserOpen(c *gin.Context) {
	ctx, cancel, ok := s.browserContext(c)
	if !ok {
		return
	}
	defer cancel()

	var req browserOpenRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	resp, err := s.Browser.Open(ctx, req.SessionID, service.BrowserOpenRequest{
		URL:       req.URL,
		WaitUntil: req.WaitUntil,
	})
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, resp)
}

func (s *ServerV2) handleBrowserSnapshot(c *gin.Context) {
	ctx, cancel, ok := s.browserContext(c)
	if !ok {
		return
	}
	defer cancel()

	sessionID := c.Query("session_id")
	if sessionID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "session_id is required"})
		return
	}

	resp, err := s.Browser.Snapshot(ctx, sessionID)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, resp)
}

func (s *ServerV2) handleBrowserAction(c *gin.Context) {
	ctx, cancel, ok := s.browserContext(c)
	if !ok {
		return
	}
	defer cancel()

	var req browserActionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	resp, err := s.Browser.Action(ctx, req.SessionID, service.BrowserActionRequest{
		Action:     req.Action,
		Ref:        req.Ref,
		Selector:   req.Selector,
		Text:       req.Text,
		TextQuery:  req.TextQuery,
		Label:      req.Label,
		Role:       req.Role,
		Name:       req.Name,
		URLPattern: req.URLPattern,
		Key:        req.Key,
		TimeoutMs:  req.TimeoutMs,
	})
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, resp)
}

func (s *ServerV2) handleBrowserScreenshot(c *gin.Context) {
	ctx, cancel, ok := s.browserContext(c)
	if !ok {
		return
	}
	defer cancel()

	var req browserScreenshotRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	resp, err := s.Browser.Screenshot(ctx, req.SessionID, req.FullPage)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, resp)
}

func (s *ServerV2) handleBrowserClose(c *gin.Context) {
	ctx, cancel, ok := s.browserContext(c)
	if !ok {
		return
	}
	defer cancel()

	var req browserCloseRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := s.Browser.CloseSession(ctx, req.SessionID); err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"ok": true})
}

func (s *ServerV2) handleBrowserSaveState(c *gin.Context) {
	ctx, cancel, ok := s.browserContext(c)
	if !ok {
		return
	}
	defer cancel()

	var req browserSaveStateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	resp, err := s.Browser.SaveState(ctx, req.SessionID, req.StateName)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, resp)
}

func (s *ServerV2) handleBrowserLoadState(c *gin.Context) {
	ctx, cancel, ok := s.browserContext(c)
	if !ok {
		return
	}
	defer cancel()

	var req browserLoadStateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	input := service.BrowserLoadStateRequest{
		StateName: req.StateName,
		Headless:  req.Headless,
	}
	input.Viewport.Width = req.Viewport.Width
	input.Viewport.Height = req.Viewport.Height

	resp, err := s.Browser.LoadState(ctx, input)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, resp)
}
