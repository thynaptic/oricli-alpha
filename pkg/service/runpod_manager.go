package service

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/connectors/runpod"
)

// RunPodState is the lifecycle state of the inference pod.
type RunPodState int

const (
	StateOff     RunPodState = iota // no pod, not spending
	StateWarming                    // pod created, KoboldCpp not yet ready
	StateWarm                       // pod ready, traffic can route here
)

// RunPodManager manages a single KoboldCpp inference pod on RunPod.
// It implements lazy spin-up, idle auto-terminate, and a hard budget guard.
// The model is auto-selected from the baked-in catalog based on available GPU VRAM.
// Set RUNPOD_MODEL_URL_CODE or RUNPOD_MODEL_URL_RESEARCH to override per-tier.
type RunPodManager struct {
	client      *runpod.Client
	enabled     bool
	maxHourly   float64       // max $/hr for GPU selection
	monthlyCap  float64       // hard monthly spend cap ($)
	idleTimeout time.Duration // auto-terminate after this idle period
	minVRAM     int           // minimum GPU VRAM (GB)
	// Per-tier URL overrides (optional — catalog is used when empty)
	modelURLCode     string
	modelURLResearch string

	mu          sync.Mutex
	state       RunPodState
	pod         *runpod.InferencePod
	lastTraffic time.Time
	idleTimer   *time.Timer

	// Approximate spend tracking (resets on process restart — persists in .env ideally)
	monthSpend float64
	spendMu    sync.Mutex

	httpClient *http.Client
}

// NewRunPodManager reads config from env and returns a RunPodManager.
// Only RUNPOD_ENABLED=true is required — model is auto-selected from the catalog.
func NewRunPodManager() *RunPodManager {
	enabled := os.Getenv("RUNPOD_ENABLED") == "true"
	apiKey := os.Getenv("RUNPOD_API_KEY")
	if apiKey == "" {
		apiKey = os.Getenv("OricliAlpha_Key")
	}

	maxHourly := parseFloatEnv("RUNPOD_MAX_HOURLY", 1.50)
	monthlyCap := parseFloatEnv("RUNPOD_MONTHLY_CAP", 50.00)
	idleMin := parseFloatEnv("RUNPOD_IDLE_TIMEOUT_MIN", 15)
	minVRAM := int(parseFloatEnv("RUNPOD_GPU_MIN_VRAM", 8))

	mgr := &RunPodManager{
		client:           runpod.NewClient(apiKey),
		enabled:          enabled && apiKey != "",
		maxHourly:        maxHourly,
		monthlyCap:       monthlyCap,
		idleTimeout:      time.Duration(idleMin) * time.Minute,
		minVRAM:          minVRAM,
		modelURLCode:     os.Getenv("RUNPOD_MODEL_URL_CODE"),
		modelURLResearch: os.Getenv("RUNPOD_MODEL_URL_RESEARCH"),
		state:            StateOff,
		httpClient:       &http.Client{Timeout: 0},
	}

	if mgr.enabled {
		log.Printf("[RunPodMgr] enabled — max $%.2f/hr, cap $%.2f/mo, idle %v, minVRAM %dGB (model auto-selected from catalog)",
			maxHourly, monthlyCap, mgr.idleTimeout, minVRAM)
	} else {
		log.Printf("[RunPodMgr] disabled (set RUNPOD_ENABLED=true to activate)")
	}
	return mgr
}

// IsEnabled reports whether RunPod routing is active.
func (m *RunPodManager) IsEnabled() bool {
	return m.enabled
}

// Ensure brings the pod to the warm state if needed and returns the endpoint URL.
// Concurrent callers wait for the same warmup — no duplicate pods.
func (m *RunPodManager) Ensure(ctx context.Context, tier string) (string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if !m.IsEnabled() {
		return "", fmt.Errorf("RunPod not enabled")
	}

	// Budget guard
	m.spendMu.Lock()
	over := m.monthSpend >= m.monthlyCap
	m.spendMu.Unlock()
	if over {
		return "", fmt.Errorf("RunPod monthly cap $%.2f reached — routing to local Ollama", m.monthlyCap)
	}

	if m.state == StateWarm && m.pod != nil {
		m.resetIdle()
		return m.pod.EndpointURL, nil
	}

	if m.state == StateWarming {
		m.mu.Unlock()
		endpoint, err := m.waitWarm(ctx)
		m.mu.Lock()
		return endpoint, err
	}

	// StateOff — spin up
	m.state = StateWarming
	m.mu.Unlock()
	endpoint, err := m.spinUp(ctx, tier)
	m.mu.Lock()
	if err != nil {
		m.state = StateOff
		return "", err
	}
	m.state = StateWarm
	m.resetIdle()
	return endpoint, nil
}

func (m *RunPodManager) spinUp(ctx context.Context, tier string) (string, error) {
	log.Printf("[RunPodMgr] selecting GPU (≥%dGB VRAM, max $%.2f/hr)...", m.minVRAM, m.maxHourly)
	gpu, err := m.client.SelectBestGPU(m.minVRAM, m.maxHourly)
	if err != nil {
		return "", fmt.Errorf("GPU selection failed: %w", err)
	}
	log.Printf("[RunPodMgr] selected GPU: %s (%dGB, $%.3f/hr)", gpu.DisplayName, gpu.MemoryInGb, gpu.SecurePrice)

	// Auto-select model from catalog based on GPU VRAM; env override takes precedence
	var override string
	if tier == "research" {
		override = m.modelURLResearch
	} else {
		override = m.modelURLCode
	}
	modelURL := runpod.ModelURLForTier(tier, gpu.MemoryInGb, override)
	log.Printf("[RunPodMgr] loading model for tier=%s vram=%dGB: %s", tier, gpu.MemoryInGb, modelURL)

	pod, err := m.client.CreateInferencePod(gpu.ID, modelURL)
	if err != nil {
		return "", fmt.Errorf("pod creation failed: %w", err)
	}
	pod.HourlyRate = gpu.SecurePrice
	log.Printf("[RunPodMgr] pod %s created — waiting for KoboldCpp to be ready...", pod.PodID)

	waitCtx, cancel := context.WithTimeout(ctx, 5*time.Minute)
	defer cancel()
	if err := m.client.WaitForReady(waitCtx, pod); err != nil {
		_ = m.client.TerminatePod(pod.PodID)
		return "", fmt.Errorf("pod %s never became ready: %w", pod.PodID, err)
	}

	m.mu.Lock()
	m.pod = pod
	m.mu.Unlock()

	log.Printf("[RunPodMgr] pod %s warm — endpoint: %s", pod.PodID, pod.EndpointURL)
	go m.trackSpend(pod)

	return pod.EndpointURL, nil
}

// waitWarm polls until the state transitions out of StateWarming.
func (m *RunPodManager) waitWarm(ctx context.Context) (string, error) {
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
			if s == StateWarm && pod != nil {
				return pod.EndpointURL, nil
			}
			if s == StateOff {
				return "", fmt.Errorf("pod warmup failed")
			}
		}
	}
}

// resetIdle resets (or starts) the idle auto-terminate timer. Must be called with m.mu held.
func (m *RunPodManager) resetIdle() {
	if m.idleTimer != nil {
		m.idleTimer.Reset(m.idleTimeout)
	} else {
		m.idleTimer = time.AfterFunc(m.idleTimeout, func() {
			log.Printf("[RunPodMgr] idle timeout — terminating pod")
			m.Shutdown()
		})
	}
	m.lastTraffic = time.Now()
}

// Shutdown terminates the active pod and resets state.
func (m *RunPodManager) Shutdown() {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.idleTimer != nil {
		m.idleTimer.Stop()
		m.idleTimer = nil
	}
	if m.pod != nil {
		podID := m.pod.PodID
		go func() {
			if err := m.client.TerminatePod(podID); err != nil {
				log.Printf("[RunPodMgr] terminate pod %s error: %v", podID, err)
			} else {
				log.Printf("[RunPodMgr] pod %s terminated", podID)
			}
		}()
		m.pod = nil
	}
	m.state = StateOff
}

// trackSpend accumulates estimated spend every minute until the pod is gone.
func (m *RunPodManager) trackSpend(pod *runpod.InferencePod) {
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
			log.Printf("[RunPodMgr] monthly cap $%.2f reached — shutting down pod", m.monthlyCap)
			m.Shutdown()
			return
		}
	}
}

// ChatStream routes a streaming request to the warm KoboldCpp pod.
// tier is used to auto-select the right model from the catalog on first spin-up.
func (m *RunPodManager) ChatStream(ctx context.Context, messages []map[string]string, options map[string]interface{}, tier string) (<-chan string, error) {
	endpoint, err := m.Ensure(ctx, tier)
	if err != nil {
		return nil, err
	}

	// Build OpenAI-compatible payload for KoboldCpp
	oaiMessages := make([]map[string]interface{}, len(messages))
	for i, msg := range messages {
		oaiMessages[i] = map[string]interface{}{"role": msg["role"], "content": msg["content"]}
	}
	payload := map[string]interface{}{
		"model":    "koboldcpp", // KoboldCpp ignores this but requires the field
		"messages": oaiMessages,
		"stream":   true,
	}
	if temp, ok := options["temperature"].(float64); ok {
		payload["temperature"] = temp
	}
	if maxTok, ok := options["max_tokens"].(int); ok {
		payload["max_tokens"] = maxTok
	}

	body, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, "POST", endpoint+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := m.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("RunPod request failed: %w", err)
	}
	if resp.StatusCode >= 400 {
		resp.Body.Close()
		return nil, fmt.Errorf("KoboldCpp returned HTTP %d", resp.StatusCode)
	}

	// Reset idle timer on successful request
	m.mu.Lock()
	m.resetIdle()
	m.mu.Unlock()

	ch := make(chan string, 64)
	go func() {
		defer resp.Body.Close()
		defer close(ch)
		scanner := bufio.NewScanner(resp.Body)
		for scanner.Scan() {
			line := scanner.Text()
			if len(line) < 6 || line[:5] != "data:" {
				continue
			}
			data := line[5:]
			if data == " [DONE]" || data == "[DONE]" {
				return
			}
			var chunk struct {
				Choices []struct {
					Delta struct {
						Content string `json:"content"`
					} `json:"delta"`
				} `json:"choices"`
			}
			if err := json.Unmarshal([]byte(data), &chunk); err != nil || len(chunk.Choices) == 0 {
				continue
			}
			if tok := chunk.Choices[0].Delta.Content; tok != "" {
				select {
				case ch <- tok:
				case <-ctx.Done():
					return
				}
			}
		}
	}()

	return ch, nil
}

// WarmingUp reports whether the pod is currently spinning up (for UI hints).
func (m *RunPodManager) WarmingUp() bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.state == StateWarming
}

// Status returns a human-readable status string.
func (m *RunPodManager) Status() string {
	m.mu.Lock()
	defer m.mu.Unlock()
	switch m.state {
	case StateOff:
		return "off"
	case StateWarming:
		return "warming"
	case StateWarm:
		return "warm"
	}
	return "unknown"
}

// MonthSpend returns the approximate spend this calendar month.
func (m *RunPodManager) MonthSpend() float64 {
	m.spendMu.Lock()
	defer m.spendMu.Unlock()
	return m.monthSpend
}

func parseFloatEnv(key string, defaultVal float64) float64 {
	v := os.Getenv(key)
	if v == "" {
		return defaultVal
	}
	f, err := strconv.ParseFloat(v, 64)
	if err != nil {
		return defaultVal
	}
	return f
}
