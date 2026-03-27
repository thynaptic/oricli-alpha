package service

import (
	"context"
	"encoding/base64"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/cognition"
	"github.com/thynaptic/oricli-go/pkg/connectors/runpod"
	"github.com/thynaptic/oricli-go/pkg/reform"
)

// RunPodVisionManager lazily spins up an Ollama GPU pod on RunPod for image analysis.
// It satisfies the cognition.VisionAnalyzer interface and mirrors RunPodManager's
// lifecycle pattern (off → warming → warm → idle timeout → terminate).
type RunPodVisionManager struct {
	client      *runpod.Client
	enabled     bool
	maxHourly   float64
	monthlyCap  float64
	idleTimeout time.Duration
	minVRAM     int

	mu         sync.Mutex
	state      RunPodState
	pod        *runpod.VisionPod
	lastUsed   time.Time
	idleTimer  *time.Timer
	monthSpend float64
}

// NewRunPodVisionManager creates a manager from environment variables.
// Env vars:
//
//	RUNPOD_VISION_ENABLED        true|false (default: false)
//	RUNPOD_VISION_MAX_HOURLY     max $/hr (default: 1.00)
//	RUNPOD_VISION_MONTHLY_CAP    hard cap $ (default: 20.00)
//	RUNPOD_VISION_MIN_VRAM       minimum GPU VRAM GB (default: 8)
//	RUNPOD_VISION_IDLE_TIMEOUT   idle minutes before pod terminates (default: 10)
func NewRunPodVisionManager(client *runpod.Client) *RunPodVisionManager {
	enabled := os.Getenv("RUNPOD_VISION_ENABLED") == "true"
	maxHourly := parseFloatEnv("RUNPOD_VISION_MAX_HOURLY", 1.00)
	monthlyCap := parseFloatEnv("RUNPOD_VISION_MONTHLY_CAP", 20.00)
	minVRAM := parseIntEnv("RUNPOD_VISION_MIN_VRAM", 8)
	idleMins := parseIntEnv("RUNPOD_VISION_IDLE_TIMEOUT", 10)
	return &RunPodVisionManager{
		client:      client,
		enabled:     enabled,
		maxHourly:   maxHourly,
		monthlyCap:  monthlyCap,
		idleTimeout: time.Duration(idleMins) * time.Minute,
		minVRAM:     minVRAM,
		state:       StateOff,
	}
}

// Analyze implements cognition.VisionAnalyzer. It ensures the GPU pod is warm,
// resolves the image to base64, then calls moondream on the pod.
func (m *RunPodVisionManager) Analyze(input cognition.VisionInput) (cognition.VisionResult, error) {
	if !m.enabled {
		return cognition.VisionResult{}, fmt.Errorf("vision: RunPod vision is not enabled (set RUNPOD_VISION_ENABLED=true)")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	defer cancel()

	baseURL, err := m.Ensure(ctx)
	if err != nil {
		return cognition.VisionResult{}, fmt.Errorf("vision: pod not ready: %w", err)
	}

	m.mu.Lock()
	m.lastUsed = time.Now()
	m.resetIdleTimer()
	m.mu.Unlock()

	b64, err := resolveImageToBase64(input)
	if err != nil {
		return cognition.VisionResult{}, err
	}

	prompt := input.Prompt
	if prompt == "" {
		prompt = cognition.DefaultVisionPrompt
	}

	description, err := runpod.CallVisionInference(ctx, baseURL, b64, prompt)
	if err != nil {
		return cognition.VisionResult{}, fmt.Errorf("vision: inference: %w", err)
	}

	return cognition.VisionResult{
		Description: description,
		Tags:        extractTagsFromDescription(description),
		Model:       runpod.VisionModel + "@runpod",
		RawResponse: description,
	}, nil
}

// Ensure guarantees a warm Ollama pod is running and returns its base URL.
// Concurrent callers share the same pod; only one spin-up happens at a time.
func (m *RunPodVisionManager) Ensure(ctx context.Context) (string, error) {
	m.mu.Lock()

	if m.state == StateWarm && m.pod != nil {
		url := m.pod.BaseURL
		m.mu.Unlock()
		return url, nil
	}

	if m.state == StateWarming {
		m.mu.Unlock()
		// Poll until warm or context cancelled
		for {
			select {
			case <-ctx.Done():
				return "", ctx.Err()
			case <-time.After(5 * time.Second):
				m.mu.Lock()
				if m.state == StateWarm && m.pod != nil {
					url := m.pod.BaseURL
					m.mu.Unlock()
					return url, nil
				}
				if m.state == StateOff {
					m.mu.Unlock()
					return "", fmt.Errorf("vision pod failed to warm")
				}
				m.mu.Unlock()
			}
		}
	}

	// Budget check
	if m.monthSpend >= m.monthlyCap {
		m.mu.Unlock()
		return "", fmt.Errorf("vision: monthly RunPod cap ($%.2f) reached", m.monthlyCap)
	}

	// RunPod Constitution pre-flight
	if err := reform.NewRunPodConstitution().ValidateCreate(reform.RunPodCreateRequest{
		Tier:           "research", // vision uses GPU on par with research tier
		GPUVRAM:        m.minVRAM,
		HourlyRate:     m.maxHourly,
		MonthlySpend:   m.monthSpend,
		MonthlyCap:     m.monthlyCap,
		HasActivePod:   false,
		HasActiveTasks: true, // Ensure() is only called from user-request paths
	}); err != nil {
		m.mu.Unlock()
		return "", fmt.Errorf("vision: constitution blocked: %w", err)
	}

	m.state = StateWarming
	m.mu.Unlock()

	pod, err := m.client.TryCreateVisionPod(m.minVRAM, m.maxHourly)
	if err != nil {
		m.mu.Lock()
		m.state = StateOff
		m.mu.Unlock()
		return "", fmt.Errorf("vision: pod creation: %w", err)
	}

	if err := m.client.WaitForVisionReady(ctx, pod); err != nil {
		_ = m.client.TerminatePod(pod.PodID)
		m.mu.Lock()
		m.state = StateOff
		m.mu.Unlock()
		return "", fmt.Errorf("vision: pod never became ready: %w", err)
	}

	m.mu.Lock()
	m.pod = pod
	m.state = StateWarm
	m.resetIdleTimer()
	m.mu.Unlock()

	go m.trackSpend()

	return pod.BaseURL, nil
}

func (m *RunPodVisionManager) resetIdleTimer() {
	if m.idleTimer != nil {
		m.idleTimer.Stop()
	}
	m.idleTimer = time.AfterFunc(m.idleTimeout, m.terminate)
}

func (m *RunPodVisionManager) terminate() {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.pod == nil {
		return
	}
	_ = m.client.TerminatePod(m.pod.PodID)
	m.pod = nil
	m.state = StateOff
	if m.idleTimer != nil {
		m.idleTimer.Stop()
	}
}

func (m *RunPodVisionManager) trackSpend() {
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()
	for range ticker.C {
		m.mu.Lock()
		if m.state != StateWarm || m.pod == nil {
			m.mu.Unlock()
			return
		}
		m.monthSpend += m.pod.HourlyRate / 60
		m.mu.Unlock()
	}
}

// resolveImageToBase64 converts any VisionInput source to a raw base64 string.
func resolveImageToBase64(input cognition.VisionInput) (string, error) {
	switch {
	case input.Base64 != "":
		return input.Base64, nil
	case input.FilePath != "":
		data, err := os.ReadFile(input.FilePath)
		if err != nil {
			return "", fmt.Errorf("vision: read file: %w", err)
		}
		return base64.StdEncoding.EncodeToString(data), nil
	case input.URL != "":
		resp, err := http.Get(input.URL) //nolint:gosec — caller is authenticated
		if err != nil {
			return "", fmt.Errorf("vision: fetch url: %w", err)
		}
		defer resp.Body.Close()
		data, err := io.ReadAll(resp.Body)
		if err != nil {
			return "", fmt.Errorf("vision: read url body: %w", err)
		}
		return base64.StdEncoding.EncodeToString(data), nil
	default:
		return "", fmt.Errorf("vision: no image source provided")
	}
}

// extractTagsFromDescription is a lightweight heuristic tag extractor (no LLM call).
func extractTagsFromDescription(description string) []string {
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

func parseIntEnv(key string, def int) int {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.Atoi(v); err == nil {
			return i
		}
	}
	return def
}
