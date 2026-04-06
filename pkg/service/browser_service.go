package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/thynaptic/oricli-go/pkg/core/config"
)

type BrowserService struct {
	enabled        bool
	baseURL        string
	apiKey         string
	allowedDomains []string
	client         *http.Client
}

type BrowserCreateSessionRequest struct {
	Headless bool `json:"headless"`
	Viewport struct {
		Width  int `json:"width,omitempty"`
		Height int `json:"height,omitempty"`
	} `json:"viewport,omitempty"`
}

type BrowserOpenRequest struct {
	URL       string `json:"url"`
	WaitUntil string `json:"wait_until,omitempty"`
}

type BrowserActionRequest struct {
	Action     string `json:"action"`
	Ref        string `json:"ref,omitempty"`
	Selector   string `json:"selector,omitempty"`
	Text       string `json:"text,omitempty"`
	TextQuery  string `json:"text_query,omitempty"`
	Label      string `json:"label,omitempty"`
	Role       string `json:"role,omitempty"`
	Name       string `json:"name,omitempty"`
	URLPattern string `json:"url_pattern,omitempty"`
	Key        string `json:"key,omitempty"`
	TimeoutMs  int    `json:"timeout_ms,omitempty"`
}

type BrowserSnapshotElement struct {
	Ref         string `json:"ref"`
	Tag         string `json:"tag"`
	Role        string `json:"role"`
	Text        string `json:"text"`
	Selector    string `json:"selector"`
	Href        string `json:"href,omitempty"`
	InputType   string `json:"inputType,omitempty"`
	Placeholder string `json:"placeholder,omitempty"`
	Enabled     bool   `json:"enabled"`
	Visible     bool   `json:"visible"`
}

type BrowserSnapshot struct {
	URL        string                   `json:"url"`
	Title      string                   `json:"title"`
	CapturedAt string                   `json:"capturedAt"`
	Elements   []BrowserSnapshotElement `json:"elements"`
}

type BrowserSessionResponse struct {
	OK        bool            `json:"ok"`
	SessionID string          `json:"session_id,omitempty"`
	URL       string          `json:"url,omitempty"`
	Title     string          `json:"title,omitempty"`
	Snapshot  BrowserSnapshot `json:"snapshot,omitempty"`
	Error     string          `json:"error,omitempty"`
}

type BrowserActionResponse struct {
	OK       bool            `json:"ok"`
	Action   string          `json:"action,omitempty"`
	URL      string          `json:"url,omitempty"`
	Title    string          `json:"title,omitempty"`
	Value    string          `json:"value,omitempty"`
	Snapshot BrowserSnapshot `json:"snapshot,omitempty"`
	Error    string          `json:"error,omitempty"`
}

type BrowserScreenshotResponse struct {
	OK    bool   `json:"ok"`
	Path  string `json:"path,omitempty"`
	URL   string `json:"url,omitempty"`
	Title string `json:"title,omitempty"`
	Error string `json:"error,omitempty"`
}

type BrowserStateRequest struct {
	StateName string `json:"state_name"`
}

type BrowserLoadStateRequest struct {
	StateName string `json:"state_name"`
	Headless  bool   `json:"headless"`
	Viewport  struct {
		Width  int `json:"width,omitempty"`
		Height int `json:"height,omitempty"`
	} `json:"viewport,omitempty"`
}

type BrowserStateResponse struct {
	OK        bool   `json:"ok"`
	SessionID string `json:"session_id,omitempty"`
	StateName string `json:"state_name,omitempty"`
	Path      string `json:"path,omitempty"`
	Error     string `json:"error,omitempty"`
}

type browserHealthResponse struct {
	OK       bool   `json:"ok"`
	Sessions int    `json:"sessions"`
	Error    string `json:"error,omitempty"`
}

func NewBrowserService(cfg config.Config) *BrowserService {
	timeout := time.Duration(cfg.BrowserRequestTimeoutSeconds) * time.Second
	if timeout <= 0 {
		timeout = 45 * time.Second
	}

	return &BrowserService{
		enabled:        cfg.BrowserAutomationEnabled,
		baseURL:        strings.TrimRight(cfg.BrowserServiceBaseURL, "/"),
		apiKey:         cfg.BrowserServiceAPIKey,
		allowedDomains: cfg.BrowserAllowedDomains,
		client: &http.Client{
			Timeout: timeout,
		},
	}
}

func (s *BrowserService) Enabled() bool {
	return s != nil && s.enabled
}

func (s *BrowserService) Health(ctx context.Context) (bool, int, error) {
	if err := s.ensureEnabled(); err != nil {
		return false, 0, err
	}
	var resp browserHealthResponse
	if err := s.doJSON(ctx, http.MethodGet, "/health", nil, &resp); err != nil {
		return false, 0, err
	}
	if !resp.OK {
		return false, resp.Sessions, fmt.Errorf("%s", resp.Error)
	}
	return true, resp.Sessions, nil
}

func (s *BrowserService) CreateSession(ctx context.Context, req BrowserCreateSessionRequest) (*BrowserSessionResponse, error) {
	if err := s.ensureEnabled(); err != nil {
		return nil, err
	}
	var resp BrowserSessionResponse
	if err := s.doJSON(ctx, http.MethodPost, "/sessions", req, &resp); err != nil {
		return nil, err
	}
	if !resp.OK {
		return nil, fmt.Errorf("%s", resp.Error)
	}
	return &resp, nil
}

func (s *BrowserService) Open(ctx context.Context, sessionID string, req BrowserOpenRequest) (*BrowserSessionResponse, error) {
	if err := s.ensureEnabled(); err != nil {
		return nil, err
	}
	if err := s.validateURL(req.URL); err != nil {
		return nil, err
	}
	var resp BrowserSessionResponse
	if err := s.doJSON(ctx, http.MethodPost, fmt.Sprintf("/sessions/%s/open", url.PathEscape(sessionID)), req, &resp); err != nil {
		return nil, err
	}
	if !resp.OK {
		return nil, fmt.Errorf("%s", resp.Error)
	}
	return &resp, nil
}

func (s *BrowserService) Snapshot(ctx context.Context, sessionID string) (*BrowserSessionResponse, error) {
	if err := s.ensureEnabled(); err != nil {
		return nil, err
	}
	var resp BrowserSessionResponse
	if err := s.doJSON(ctx, http.MethodGet, fmt.Sprintf("/sessions/%s/snapshot", url.PathEscape(sessionID)), nil, &resp); err != nil {
		return nil, err
	}
	if !resp.OK {
		return nil, fmt.Errorf("%s", resp.Error)
	}
	return &resp, nil
}

func (s *BrowserService) Action(ctx context.Context, sessionID string, req BrowserActionRequest) (*BrowserActionResponse, error) {
	if err := s.ensureEnabled(); err != nil {
		return nil, err
	}
	var resp BrowserActionResponse
	if err := s.doJSON(ctx, http.MethodPost, fmt.Sprintf("/sessions/%s/action", url.PathEscape(sessionID)), req, &resp); err != nil {
		return nil, err
	}
	if !resp.OK {
		return nil, fmt.Errorf("%s", resp.Error)
	}
	return &resp, nil
}

func (s *BrowserService) Screenshot(ctx context.Context, sessionID string, fullPage bool) (*BrowserScreenshotResponse, error) {
	if err := s.ensureEnabled(); err != nil {
		return nil, err
	}
	path := fmt.Sprintf("/sessions/%s/screenshot", url.PathEscape(sessionID))
	if fullPage {
		path += "?full=true"
	}
	var resp BrowserScreenshotResponse
	if err := s.doJSON(ctx, http.MethodPost, path, map[string]any{}, &resp); err != nil {
		return nil, err
	}
	if !resp.OK {
		return nil, fmt.Errorf("%s", resp.Error)
	}
	return &resp, nil
}

func (s *BrowserService) CloseSession(ctx context.Context, sessionID string) error {
	if err := s.ensureEnabled(); err != nil {
		return err
	}
	var resp BrowserSessionResponse
	if err := s.doJSON(ctx, http.MethodDelete, fmt.Sprintf("/sessions/%s", url.PathEscape(sessionID)), nil, &resp); err != nil {
		return err
	}
	if !resp.OK {
		return fmt.Errorf("%s", resp.Error)
	}
	return nil
}

func (s *BrowserService) SaveState(ctx context.Context, sessionID, stateName string) (*BrowserStateResponse, error) {
	if err := s.ensureEnabled(); err != nil {
		return nil, err
	}
	var resp BrowserStateResponse
	if err := s.doJSON(ctx, http.MethodPost, fmt.Sprintf("/sessions/%s/state/save", url.PathEscape(sessionID)), BrowserStateRequest{
		StateName: stateName,
	}, &resp); err != nil {
		return nil, err
	}
	if !resp.OK {
		return nil, fmt.Errorf("%s", resp.Error)
	}
	return &resp, nil
}

func (s *BrowserService) LoadState(ctx context.Context, req BrowserLoadStateRequest) (*BrowserStateResponse, error) {
	if err := s.ensureEnabled(); err != nil {
		return nil, err
	}
	var resp BrowserStateResponse
	if err := s.doJSON(ctx, http.MethodPost, "/state/load", req, &resp); err != nil {
		return nil, err
	}
	if !resp.OK {
		return nil, fmt.Errorf("%s", resp.Error)
	}
	return &resp, nil
}

func (s *BrowserService) ensureEnabled() error {
	if s == nil || !s.enabled {
		return fmt.Errorf("browser automation is disabled")
	}
	if s.baseURL == "" {
		return fmt.Errorf("browser service base URL is not configured")
	}
	return nil
}

func (s *BrowserService) validateURL(raw string) error {
	parsed, err := url.Parse(raw)
	if err != nil {
		return fmt.Errorf("invalid URL: %w", err)
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return fmt.Errorf("unsupported URL scheme %q", parsed.Scheme)
	}
	if len(s.allowedDomains) == 0 {
		return nil
	}
	host := strings.ToLower(parsed.Hostname())
	for _, domain := range s.allowedDomains {
		domain = strings.ToLower(strings.TrimSpace(domain))
		if domain == "" {
			continue
		}
		if host == domain || strings.HasSuffix(host, "."+domain) {
			return nil
		}
	}
	return fmt.Errorf("domain %q is not allowed by browser policy", host)
}

func (s *BrowserService) doJSON(ctx context.Context, method, path string, in any, out any) error {
	var body io.Reader
	if in != nil {
		data, err := json.Marshal(in)
		if err != nil {
			return err
		}
		body = bytes.NewReader(data)
	}

	req, err := http.NewRequestWithContext(ctx, method, s.baseURL+path, body)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	if s.apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+s.apiKey)
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		data, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		return fmt.Errorf("browser service %s %s failed: %s", method, path, strings.TrimSpace(string(data)))
	}
	return json.NewDecoder(resp.Body).Decode(out)
}
