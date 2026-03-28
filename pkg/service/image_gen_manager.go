package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/connectors/runpod"
)

// ImageGenState mirrors RunPodState for the image gen pod lifecycle.
type ImageGenState int

const (
	ImgStateOff     ImageGenState = iota
	ImgStateWarming               // A1111 booting
	ImgStateWarm                  // ready for requests
)

// ImageGenRequest mirrors the OpenAI images/generations request body.
type ImageGenRequest struct {
	Prompt         string `json:"prompt"`
	NegativePrompt string `json:"negative_prompt,omitempty"`
	N              int    `json:"n,omitempty"`
	Size           string `json:"size,omitempty"` // "widthxheight" e.g. "1024x1024"
	Steps          int    `json:"steps,omitempty"`
}

// ImageGenResponse is the OpenAI-compatible images/generations response.
type ImageGenResponse struct {
	Created int64 `json:"created"`
	Data    []struct {
		B64JSON string `json:"b64_json"`
	} `json:"data"`
}

// ImageGenManager manages Stable Diffusion image generation via either:
//   - RunPod serverless endpoint (preferred): set RUNPOD_IMAGEGEN_ENDPOINT_ID
//   - RunPod on-demand pod (fallback): lazy spin-up / idle auto-terminate
type ImageGenManager struct {
	client      *runpod.Client
	enabled     bool
	apiKey      string
	endpointID  string // serverless endpoint ID — if set, skips pod lifecycle entirely
	maxHourly   float64
	monthlyCap  float64
	idleTimeout time.Duration
	minVRAM     int

	mu          sync.Mutex
	state       ImageGenState
	pod         *runpod.ImageGenPod
	idleTimer   *time.Timer
	lastTraffic time.Time

	monthSpend float64
	spendMu    sync.Mutex

	httpClient *http.Client
}

// NewImageGenManager reads config from env and returns an ImageGenManager.
// Activated by RUNPOD_IMAGEGEN_ENABLED=true (or falls back to RUNPOD_ENABLED).
func NewImageGenManager() *ImageGenManager {
	enabledStr := os.Getenv("RUNPOD_IMAGEGEN_ENABLED")
	if enabledStr == "" {
		enabledStr = os.Getenv("RUNPOD_ENABLED") // inherit from main flag
	}
	enabled := enabledStr == "true"

	apiKey := os.Getenv("RUNPOD_API_KEY")
	if apiKey == "" {
		apiKey = os.Getenv("OricliAlpha_Key")
	}

	maxHourly := parseFloatEnv("RUNPOD_IMAGEGEN_MAX_HOURLY", parseFloatEnv("RUNPOD_MAX_HOURLY", 1.50))
	monthlyCap := parseFloatEnv("RUNPOD_MONTHLY_CAP", 50.00)
	idleMin := parseFloatEnv("RUNPOD_IMAGEGEN_IDLE_TIMEOUT_MIN", 10)
	minVRAM := int(parseFloatEnv("RUNPOD_IMAGEGEN_MIN_VRAM", 8))

	mgr := &ImageGenManager{
		client:      runpod.NewClient(apiKey),
		enabled:     enabled && apiKey != "",
		apiKey:      apiKey,
		endpointID:  os.Getenv("RUNPOD_IMAGEGEN_ENDPOINT_ID"),
		maxHourly:   maxHourly,
		monthlyCap:  monthlyCap,
		idleTimeout: time.Duration(idleMin) * time.Minute,
		minVRAM:     minVRAM,
		state:       ImgStateOff,
		httpClient:  &http.Client{Timeout: 120 * time.Second},
	}

	if mgr.enabled {
		if mgr.endpointID != "" {
			log.Printf("[ImageGenMgr] serverless mode — endpoint: %s", mgr.endpointID)
		} else {
			log.Printf("[ImageGenMgr] pod mode — max $%.2f/hr, cap $%.2f/mo, idle %v, minVRAM %dGB",
				maxHourly, monthlyCap, mgr.idleTimeout, minVRAM)
			mgr.tryRestoreImgPod()
		}
	} else {
		log.Printf("[ImageGenMgr] disabled (set RUNPOD_IMAGEGEN_ENABLED=true to activate)")
	}
	return mgr
}

// IsEnabled reports whether image gen is active.
func (m *ImageGenManager) IsEnabled() bool { return m.enabled }

// WarmingUp reports whether the pod is currently starting up.
func (m *ImageGenManager) WarmingUp() bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.state == ImgStateWarming
}

// Status returns a human-readable pod state string.
func (m *ImageGenManager) Status() string {
	m.mu.Lock()
	defer m.mu.Unlock()
	switch m.state {
	case ImgStateOff:
		return "off"
	case ImgStateWarming:
		return "warming"
	case ImgStateWarm:
		return "warm"
	}
	return "unknown"
}

// GenerateImage runs SD inference via serverless endpoint (preferred) or on-demand pod.
// Returns the base64-encoded PNG.
func (m *ImageGenManager) GenerateImage(ctx context.Context, req ImageGenRequest) (string, error) {
	if m.endpointID != "" {
		return m.generateServerless(ctx, req)
	}
	return m.generateViaPod(ctx, req)
}

// generateServerless submits to a RunPod serverless SD worker via /runsync.
func (m *ImageGenManager) generateServerless(ctx context.Context, req ImageGenRequest) (string, error) {
	width, height := parseSizeString(req.Size)
	steps := req.Steps
	if steps == 0 {
		steps = 20
	}

	payload := map[string]interface{}{
		"input": map[string]interface{}{
			"prompt":               req.Prompt,
			"negative_prompt":      req.NegativePrompt,
			"width":                width,
			"height":               height,
			"num_inference_steps":  steps,
			"guidance_scale":       7,
			"num_images":           1,
			"scheduler":            "EulerAncestralDiscreteScheduler",
		},
	}
	body, _ := json.Marshal(payload)

	url := fmt.Sprintf("https://api.runpod.ai/v2/%s/runsync?wait=90000", m.endpointID)
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", "Bearer "+m.apiKey)

	client := &http.Client{Timeout: 95 * time.Second}
	resp, err := client.Do(httpReq)
	if err != nil {
		return "", fmt.Errorf("serverless request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 400 {
		return "", fmt.Errorf("serverless returned HTTP %d: %s", resp.StatusCode, string(respBody))
	}

	var result struct {
		Status string `json:"status"`
		Error  string `json:"error"`
		Output struct {
			Images []string `json:"images"`
			Image  string   `json:"image"` // some workers use singular "image"
		} `json:"output"`
	}
	if err := json.Unmarshal(respBody, &result); err != nil {
		return "", fmt.Errorf("serverless response parse: %w", err)
	}
	if result.Error != "" {
		return "", fmt.Errorf("serverless worker error: %s", result.Error)
	}
	if len(result.Output.Images) > 0 {
		return result.Output.Images[0], nil
	}
	if result.Output.Image != "" {
		return result.Output.Image, nil
	}
	return "", fmt.Errorf("serverless worker returned no images (status: %s)", result.Status)
}

func (m *ImageGenManager) generateViaPod(ctx context.Context, req ImageGenRequest) (string, error) {
	endpoint, err := m.ensure(ctx)
	if err != nil {
		return "", err
	}

	width, height := parseSizeString(req.Size)
	steps := req.Steps
	if steps == 0 {
		steps = 20
	}

	a1111Req := map[string]interface{}{
		"prompt":          req.Prompt,
		"negative_prompt": req.NegativePrompt,
		"steps":           steps,
		"width":           width,
		"height":          height,
		"cfg_scale":       7,
		"sampler_name":    "Euler a",
	}
	body, _ := json.Marshal(a1111Req)

	httpReq, err := http.NewRequestWithContext(ctx, "POST", endpoint+"/sdapi/v1/txt2img", bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := m.httpClient.Do(httpReq)
	if err != nil {
		return "", fmt.Errorf("A1111 request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("A1111 returned HTTP %d: %s", resp.StatusCode, string(b))
	}

	var result struct {
		Images []string `json:"images"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("A1111 response parse: %w", err)
	}
	if len(result.Images) == 0 {
		return "", fmt.Errorf("A1111 returned no images")
	}

	m.mu.Lock()
	m.resetImgIdle()
	m.mu.Unlock()

	return result.Images[0], nil
}

func (m *ImageGenManager) ensure(ctx context.Context) (string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if !m.IsEnabled() {
		return "", fmt.Errorf("image gen not enabled")
	}

	m.spendMu.Lock()
	over := m.monthSpend >= m.monthlyCap
	m.spendMu.Unlock()
	if over {
		return "", fmt.Errorf("RunPod monthly cap $%.2f reached", m.monthlyCap)
	}

	if m.state == ImgStateWarm && m.pod != nil {
		m.resetImgIdle()
		return m.pod.EndpointURL, nil
	}

	if m.state == ImgStateWarming {
		m.mu.Unlock()
		ep, err := m.waitImgWarm(ctx)
		m.mu.Lock()
		return ep, err
	}

	m.state = ImgStateWarming
	m.mu.Unlock()
	ep, err := m.spinUpImg(ctx)
	m.mu.Lock()
	if err != nil {
		m.state = ImgStateOff
		return "", err
	}
	m.state = ImgStateWarm
	m.resetImgIdle()
	return ep, nil
}

func (m *ImageGenManager) spinUpImg(ctx context.Context) (string, error) {
	log.Printf("[ImageGenMgr] selecting GPU (≥%dGB VRAM, max $%.2f/hr)...", m.minVRAM, m.maxHourly)
	gpu, err := m.client.SelectBestGPU(m.minVRAM, m.maxHourly)
	if err != nil {
		return "", fmt.Errorf("GPU selection failed: %w", err)
	}
	log.Printf("[ImageGenMgr] selected GPU: %s (%dGB, $%.3f/hr)", gpu.DisplayName, gpu.MemoryInGb, gpu.SecurePrice)

	pod, err := m.client.CreateImageGenPod(gpu.ID)
	if err != nil {
		return "", fmt.Errorf("image gen pod creation failed: %w", err)
	}
	pod.HourlyRate = gpu.SecurePrice
	log.Printf("[ImageGenMgr] pod %s created — waiting for A1111 to load (~2 min)...", pod.PodID)

	// A1111 takes 3-12 min on cold boot (image pull + model load)
	waitCtx, cancel := context.WithTimeout(ctx, 12*time.Minute)
	defer cancel()
	if err := m.client.WaitForImageReady(waitCtx, pod); err != nil {
		_ = m.client.TerminatePod(pod.PodID)
		return "", fmt.Errorf("image pod %s never became ready: %w", pod.PodID, err)
	}

	m.mu.Lock()
	m.pod = pod
	m.mu.Unlock()

	m.saveImgPodState(pod)
	log.Printf("[ImageGenMgr] pod %s warm — endpoint: %s", pod.PodID, pod.EndpointURL)
	go m.trackImgSpend(pod)

	return pod.EndpointURL, nil
}

const imageGenStateFile = ".oricli/imagegen_pod_state.json"

type imageGenPodState struct {
	PodID       string    `json:"pod_id"`
	EndpointURL string    `json:"endpoint_url"`
	GPUTypeID   string    `json:"gpu_type_id"`
	StartedAt   time.Time `json:"started_at"`
}

func (m *ImageGenManager) saveImgPodState(pod *runpod.ImageGenPod) {
	s := imageGenPodState{
		PodID:       pod.PodID,
		EndpointURL: pod.EndpointURL,
		GPUTypeID:   pod.GPUTypeID,
		StartedAt:   pod.StartedAt,
	}
	b, _ := json.Marshal(s)
	_ = os.WriteFile(imageGenStateFile, b, 0600)
}

func (m *ImageGenManager) clearImgPodState() {
	_ = os.Remove(imageGenStateFile)
}

// tryRestoreImgPod checks for a saved pod state and reconnects if A1111 is still responding.
func (m *ImageGenManager) tryRestoreImgPod() {
	b, err := os.ReadFile(imageGenStateFile)
	if err != nil {
		return
	}
	var s imageGenPodState
	if err := json.Unmarshal(b, &s); err != nil || s.PodID == "" {
		return
	}
	healthURL := s.EndpointURL + "/sdapi/v1/options"
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Get(healthURL)
	if err != nil || resp.StatusCode >= 400 {
		if resp != nil {
			resp.Body.Close()
		}
		log.Printf("[ImageGenMgr] saved pod %s not responding — will spin fresh", s.PodID)
		m.clearImgPodState()
		return
	}
	resp.Body.Close()
	m.pod = &runpod.ImageGenPod{
		PodID:       s.PodID,
		EndpointURL: s.EndpointURL,
		GPUTypeID:   s.GPUTypeID,
		StartedAt:   s.StartedAt,
	}
	m.state = ImgStateWarm
	m.resetImgIdle()
	log.Printf("[ImageGenMgr] reconnected to saved pod %s — endpoint: %s", s.PodID, s.EndpointURL)
}

func (m *ImageGenManager) waitImgWarm(ctx context.Context) (string, error) {
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return "", ctx.Err()
		case <-ticker.C:
			m.mu.Lock()
			s, pod := m.state, m.pod
			m.mu.Unlock()
			if s == ImgStateWarm && pod != nil {
				return pod.EndpointURL, nil
			}
			if s == ImgStateOff {
				return "", fmt.Errorf("image pod warmup failed")
			}
		}
	}
}

func (m *ImageGenManager) resetImgIdle() {
	if m.idleTimer != nil {
		m.idleTimer.Reset(m.idleTimeout)
	} else {
		m.idleTimer = time.AfterFunc(m.idleTimeout, func() {
			log.Printf("[ImageGenMgr] idle timeout — terminating pod")
			m.Shutdown()
		})
	}
	m.lastTraffic = time.Now()
}

// Shutdown terminates the active image gen pod.
func (m *ImageGenManager) Shutdown() {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.idleTimer != nil {
		m.idleTimer.Stop()
		m.idleTimer = nil
	}
	if m.pod != nil {
		podID := m.pod.PodID
		m.clearImgPodState()
		go func() {
			if err := m.client.TerminatePod(podID); err != nil {
				log.Printf("[ImageGenMgr] terminate pod %s error: %v", podID, err)
			} else {
				log.Printf("[ImageGenMgr] pod %s terminated", podID)
			}
		}()
		m.pod = nil
	}
	m.state = ImgStateOff
}

func (m *ImageGenManager) trackImgSpend(pod *runpod.ImageGenPod) {
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()
	perMin := pod.HourlyRate / 60.0
	for range ticker.C {
		m.mu.Lock()
		active := m.pod != nil && m.pod.PodID == pod.PodID
		m.mu.Unlock()
		if !active {
			return
		}
		m.spendMu.Lock()
		m.monthSpend += perMin
		spend := m.monthSpend
		m.spendMu.Unlock()
		if spend >= m.monthlyCap {
			log.Printf("[ImageGenMgr] monthly cap $%.2f reached — shutting down", m.monthlyCap)
			m.Shutdown()
			return
		}
	}
}

// parseSizeString parses "WxH" into (width, height) integers.
// Defaults to 768x768 for unknown/empty input.
func parseSizeString(size string) (int, int) {
	switch size {
	case "512x512":
		return 512, 512
	case "768x768":
		return 768, 768
	case "1024x1024":
		return 1024, 1024
	case "1024x768":
		return 1024, 768
	case "768x1024":
		return 768, 1024
	default:
		return 768, 768
	}
}
