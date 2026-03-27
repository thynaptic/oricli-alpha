package service

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/connectors/runpod"
	"github.com/thynaptic/oricli-go/pkg/reform"
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

	// Approximate spend tracking (resets on process restart — persists via MemoryBank)
	monthSpend float64
	spendMu    sync.Mutex

	MemoryBank  *MemoryBank // PocketBase spend persistence (optional)

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
	spend := m.monthSpend
	m.spendMu.Unlock()
	if over {
		return "", fmt.Errorf("RunPod monthly cap $%.2f reached — routing to local Ollama", m.monthlyCap)
	}

	// RunPod Constitution pre-flight check.
	// Validates Single Pod Principle, Task-Justified Activation, and Tier Justification
	// before any pod creation attempt. Existing warm/warming states return early above.
	if m.state == StateOff {
		rpConstitution := reform.NewRunPodConstitution()
		if err := rpConstitution.ValidateCreate(reform.RunPodCreateRequest{
			Tier:           tier,
			MonthlySpend:   spend,
			MonthlyCap:     m.monthlyCap,
			HasActivePod:   m.state == StateWarm || m.state == StateWarming,
			HasActiveTasks: true, // Ensure() is only called from user-request paths
		}); err != nil {
			log.Printf("[RunPodConstitution] BLOCKED: %v", err)
			return "", err
		}
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

	// Constitution: validate hourly rate against cap before pod creation.
	if err := reform.NewRunPodConstitution().ValidateBudget(gpu.SecurePrice, m.maxHourly); err != nil {
		log.Printf("[RunPodConstitution] BLOCKED: %v", err)
		return "", err
	}

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
	month := time.Now().Format("2006-01")
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

		// Persist to PocketBase so spend survives daemon restarts
		if m.MemoryBank != nil {
			m.MemoryBank.PersistSpend("inference", month, spend)
		}

		if spend >= m.monthlyCap {
			log.Printf("[RunPodMgr] monthly cap $%.2f reached — shutting down pod", m.monthlyCap)
			m.Shutdown()
			return
		}
	}
}

// LoadSpendFromBank restores this month's accumulated spend from PocketBase.
// Call once during startup so monthSpend survives process restarts.
func (m *RunPodManager) LoadSpendFromBank(ctx context.Context) {
	if m.MemoryBank == nil || !m.MemoryBank.IsEnabled() {
		return
	}
	month := time.Now().Format("2006-01")
	stored := m.MemoryBank.LoadSpend(ctx, "inference", month)
	if stored > 0 {
		m.spendMu.Lock()
		m.monthSpend = stored
		m.spendMu.Unlock()
		log.Printf("[RunPodMgr] restored month spend $%.4f from PocketBase", stored)
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

// ─────────────────────────────────────────────────────────────────
// PrimaryInferenceManager
// ─────────────────────────────────────────────────────────────────
// Manages a single long-lived vLLM pod on RunPod that serves ALL
// chat/code/research requests. Enabled when RUNPOD_PRIMARY=true.
//
// Lifecycle mirrors RunPodManager:
//   off → warming → warm
//
// When RUNPOD_PRIMARY_WARM_ON_START=true the pod is spun up
// proactively at API startup rather than on first request.
// ─────────────────────────────────────────────────────────────────

type PrimaryInferenceManager struct {
	client      *runpod.Client
	minVRAM     int
	maxHourly   float64
	modelOverride string
	idleTimeout time.Duration
	maxMonthly  float64

	mu         sync.Mutex
	state      RunPodState
	pod        *runpod.PrimaryPod
	lastActive time.Time

	spendMu    sync.Mutex
	monthSpend float64
}

// NewPrimaryInferenceManager creates a PrimaryInferenceManager from env vars.
//
//	RUNPOD_API_KEY          — required
//	RUNPOD_MIN_VRAM         — minimum VRAM in GB (default: 14)
//	RUNPOD_MAX_HOURLY       — max $/hr per pod (default: 0.50)
//	RUNPOD_PRIMARY_MODEL    — HF model ID override (default: auto-select by VRAM)
//	RUNPOD_IDLE_TIMEOUT_MIN — minutes before idle pod teardown (default: 30)
//	RUNPOD_MAX_MONTHLY      — monthly spend cap (default: 40.0)
func NewPrimaryInferenceManager() *PrimaryInferenceManager {
	key := os.Getenv("RUNPOD_API_KEY")
	if key == "" {
		return nil
	}
	minVRAM := 14
	if v := os.Getenv("RUNPOD_MIN_VRAM"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			minVRAM = n
		}
	}
	idleMin := parseFloatEnv("RUNPOD_IDLE_TIMEOUT_MIN", 30)
	m := &PrimaryInferenceManager{
		client:        runpod.NewClient(key),
		minVRAM:       minVRAM,
		maxHourly:     parseFloatEnv("RUNPOD_MAX_HOURLY", 0.50),
		modelOverride: os.Getenv("RUNPOD_PRIMARY_MODEL"),
		idleTimeout:   time.Duration(idleMin) * time.Minute,
		maxMonthly:    parseFloatEnv("RUNPOD_MAX_MONTHLY", 40.0),
		state:         StateOff,
	}
	// Attempt to reconnect to a pod that survived a service restart.
	m.tryRestorePod()
	return m
}

// ── Pod state persistence ─────────────────────────────────────────────────
// Survives service restarts: if a pod was warm when the service last exited,
// we reconnect to it rather than spinning up a brand-new one.

const podStateFile = "/home/mike/Mavaia/.oricli/primary_pod_state.json"

type savedPodState struct {
	PodID       string  `json:"pod_id"`
	EndpointURL string  `json:"endpoint_url"`
	ModelID     string  `json:"model_id"`
	ModelName   string  `json:"model_name"`
	HourlyRate  float64 `json:"hourly_rate"`
	GPUTypeID   string  `json:"gpu_type_id"`
}

func (m *PrimaryInferenceManager) savePodState(pod *runpod.PrimaryPod) {
	s := savedPodState{
		PodID:       pod.PodID,
		EndpointURL: pod.EndpointURL,
		ModelID:     pod.ModelID,
		ModelName:   pod.ModelName,
		HourlyRate:  pod.HourlyRate,
		GPUTypeID:   pod.GPUTypeID,
	}
	data, _ := json.Marshal(s)
	_ = os.WriteFile(podStateFile, data, 0600)
}

func (m *PrimaryInferenceManager) clearPodState() {
	_ = os.Remove(podStateFile)
}

// tryRestorePod checks if a previously-saved pod is still live on RunPod.
// If the /v1/models endpoint responds, we restore to StateWarm immediately.
func (m *PrimaryInferenceManager) tryRestorePod() {
	data, err := os.ReadFile(podStateFile)
	if err != nil {
		return // no saved state
	}
	var s savedPodState
	if err := json.Unmarshal(data, &s); err != nil || s.PodID == "" {
		return
	}

	// Quick liveness check — 10s timeout is plenty for a warm pod.
	hc := &http.Client{Timeout: 10 * time.Second}
	resp, err := hc.Get(s.EndpointURL + "/models")
	if err != nil || resp.StatusCode != 200 {
		if resp != nil {
			resp.Body.Close()
		}
		log.Printf("[PrimaryMgr] Saved pod %s is not responding — will spin up fresh", s.PodID)
		m.clearPodState()
		return
	}
	resp.Body.Close()

	pod := &runpod.PrimaryPod{
		PodID:       s.PodID,
		EndpointURL: s.EndpointURL,
		ModelID:     s.ModelID,
		ModelName:   s.ModelName,
		HourlyRate:  s.HourlyRate,
		GPUTypeID:   s.GPUTypeID,
		StartedAt:   time.Now(), // approximate; spend tracking restarts from 0
	}
	m.pod = pod
	m.state = StateWarm
	m.lastActive = time.Now()
	log.Printf("[PrimaryMgr] Reconnected to existing pod %s (%s) — skipping spin-up", pod.PodID, pod.ModelName)
	go m.trackSpend(pod)
	go m.idleWatcher()
}

// Ensure guarantees a warm vLLM pod is available; call before every request.
func (m *PrimaryInferenceManager) Ensure(ctx context.Context) (string, error) {
	m.mu.Lock()
	state := m.state
	m.mu.Unlock()

	switch state {
	case StateWarm:
		m.mu.Lock()
		m.lastActive = time.Now()
		url := m.pod.EndpointURL
		m.mu.Unlock()
		return url, nil
	case StateWarming:
		return m.waitWarm(ctx)
	case StateOff:
		m.mu.Lock()
		m.state = StateWarming
		m.mu.Unlock()
		go func() {
			spinCtx, cancel := context.WithTimeout(context.Background(), 15*time.Minute)
			defer cancel()
			if _, err := m.spinUp(spinCtx); err != nil {
				log.Printf("[PrimaryMgr] spinUp failed: %v", err)
				m.mu.Lock()
				m.state = StateOff
				m.mu.Unlock()
			}
		}()
		return m.waitWarm(ctx)
	}
	return "", fmt.Errorf("PrimaryInferenceManager: unknown state")
}

func (m *PrimaryInferenceManager) spinUp(ctx context.Context) (string, error) {
	m.spendMu.Lock()
	spend := m.monthSpend
	m.spendMu.Unlock()
	if spend >= m.maxMonthly {
		return "", fmt.Errorf("[PrimaryMgr] monthly cap $%.2f reached", m.maxMonthly)
	}

	log.Printf("[PrimaryMgr] selecting GPU (≥%dGB VRAM, max $%.2f/hr)...", m.minVRAM, m.maxHourly)
	pod, err := m.client.TryCreatePrimaryPod(m.minVRAM, m.maxHourly, m.modelOverride)
	if err != nil {
		return "", fmt.Errorf("pod creation failed: %w", err)
	}
	pod.HourlyRate = pod.HourlyRate
	log.Printf("[PrimaryMgr] pod %s created (model: %s $%.3f/hr) — waiting for vLLM...", pod.PodID, pod.ModelName, pod.HourlyRate)

	waitCtx, cancel := context.WithTimeout(ctx, 12*time.Minute)
	defer cancel()
	if err := m.client.WaitForPrimaryReady(waitCtx, pod); err != nil {
		_ = m.client.TerminatePod(pod.PodID)
		return "", fmt.Errorf("pod %s never became ready: %w", pod.PodID, err)
	}

	m.mu.Lock()
	m.pod = pod
	m.state = StateWarm
	m.lastActive = time.Now()
	m.mu.Unlock()

	m.savePodState(pod)
	log.Printf("[PrimaryMgr] pod %s WARM — endpoint: %s", pod.PodID, pod.EndpointURL)
	go m.trackSpend(pod)
	go m.idleWatcher()

	return pod.EndpointURL, nil
}

func (m *PrimaryInferenceManager) waitWarm(ctx context.Context) (string, error) {
	t := time.NewTicker(2 * time.Second)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return "", ctx.Err()
		case <-t.C:
			m.mu.Lock()
			s, pod := m.state, m.pod
			m.mu.Unlock()
			if s == StateWarm && pod != nil {
				return pod.EndpointURL, nil
			}
			if s == StateOff {
				return "", fmt.Errorf("pod spin-up failed")
			}
		}
	}
}

func (m *PrimaryInferenceManager) trackSpend(pod *runpod.PrimaryPod) {
	t := time.NewTicker(1 * time.Minute)
	defer t.Stop()
	for {
		m.mu.Lock()
		if m.state != StateWarm || m.pod == nil || m.pod.PodID != pod.PodID {
			m.mu.Unlock()
			return
		}
		m.mu.Unlock()
		m.spendMu.Lock()
		m.monthSpend += pod.HourlyRate / 60
		m.spendMu.Unlock()
		<-t.C
	}
}

func (m *PrimaryInferenceManager) idleWatcher() {
	t := time.NewTicker(1 * time.Minute)
	defer t.Stop()
	for range t.C {
		m.mu.Lock()
		if m.state != StateWarm {
			m.mu.Unlock()
			return
		}
		idle := time.Since(m.lastActive)
		if idle < m.idleTimeout {
			m.mu.Unlock()
			continue
		}
		pod := m.pod
		m.state = StateOff
		m.pod = nil
		m.mu.Unlock()
		m.clearPodState()
		log.Printf("[PrimaryMgr] idle timeout (%s) — terminating pod %s", idle.Round(time.Second), pod.PodID)
		_ = m.client.TerminatePod(pod.PodID)
		return
	}
}

// WarmOnStart spins up the pod proactively at server startup.
func (m *PrimaryInferenceManager) WarmOnStart() {
	if os.Getenv("RUNPOD_PRIMARY_WARM_ON_START") != "true" {
		return
	}
	m.mu.Lock()
	if m.state != StateOff {
		m.mu.Unlock()
		return
	}
	m.state = StateWarming
	m.mu.Unlock()
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 15*time.Minute)
		defer cancel()
		if _, err := m.spinUp(ctx); err != nil {
			log.Printf("[PrimaryMgr] WarmOnStart failed: %v", err)
			m.mu.Lock()
			m.state = StateOff
			m.mu.Unlock()
		}
	}()
}

// ChatStream streams a chat response from the vLLM pod.
// ChatStream streams a chat response from the vLLM pod.
// Blocks until the pod is ready (Ensure), then streams tokens.
// Callouts and Ollama fallback are handled by the caller (GenerationService).
func (m *PrimaryInferenceManager) ChatStream(ctx context.Context, messages []map[string]string, options map[string]interface{}) (<-chan string, error) {
	endpoint, err := m.Ensure(ctx)
	if err != nil {
		return nil, err
	}

	ollamaMessages := make([]map[string]interface{}, len(messages))
	for i, msg := range messages {
		ollamaMessages[i] = map[string]interface{}{"role": msg["role"], "content": msg["content"]}
	}

	m.mu.Lock()
	modelID := ""
	if m.pod != nil {
		modelID = m.pod.ModelID
	}
	m.mu.Unlock()

	payload := map[string]interface{}{
		"model":    modelID,
		"messages": ollamaMessages,
		"stream":   true,
	}
	if t, ok := options["temperature"].(float64); ok {
		payload["temperature"] = t
	}
	// max_tokens arrives as float64 from JSON unmarshal — accept both
	switch v := options["max_tokens"].(type) {
	case int:
		payload["max_tokens"] = v
	case float64:
		payload["max_tokens"] = int(v)
	}

	body, _ := json.Marshal(payload)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("PrimaryMgr chat request: %w", err)
	}
	if resp.StatusCode != 200 {
		errBody, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, fmt.Errorf("PrimaryMgr: vLLM returned HTTP %d: %s", resp.StatusCode, string(errBody))
	}

	out := make(chan string, 32)
	go func() {
		defer close(out)
		defer resp.Body.Close()
		scanner := bufio.NewScanner(resp.Body)
		for scanner.Scan() {
			line := scanner.Text()
			if len(line) < 6 || line[:6] != "data: " {
				continue
			}
			raw := line[6:]
			if raw == "[DONE]" {
				break
			}
			var chunk struct {
				Choices []struct {
					Delta struct {
						Content string `json:"content"`
					} `json:"delta"`
				} `json:"choices"`
			}
			if err := json.Unmarshal([]byte(raw), &chunk); err != nil {
				continue
			}
			if len(chunk.Choices) > 0 && chunk.Choices[0].Delta.Content != "" {
				out <- chunk.Choices[0].Delta.Content
			}
		}
	}()
	return out, nil
}

// IsEnabled returns true when a RunPod API key is configured.
func (m *PrimaryInferenceManager) IsEnabled() bool {
	return m != nil && m.client != nil
}

// PodState returns the current lifecycle state.
func (m *PrimaryInferenceManager) PodState() RunPodState {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.state
}

// PodModelName returns the name of the model loaded in the current pod (empty if off).
func (m *PrimaryInferenceManager) PodModelName() string {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.pod != nil {
		return m.pod.ModelName
	}
	return ""
}

// Status returns a human-readable pod state string.
func (m *PrimaryInferenceManager) Status() string {
	m.mu.Lock()
	defer m.mu.Unlock()
	switch m.state {
	case StateOff:
		return "off"
	case StateWarming:
		return "warming"
	case StateWarm:
		if m.pod != nil {
			return fmt.Sprintf("warm (%s)", m.pod.ModelName)
		}
		return "warm"
	}
	return "unknown"
}
