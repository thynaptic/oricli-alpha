// Package engine provides the RemoteConfigSync service for headless Oricli Engine deployments.
// It periodically polls a Thynaptic-hosted configuration endpoint and applies
// hot-reload updates to the Sovereign Engine's Constitutional Stack, SCAI thresholds,
// and model routing rules — without requiring a process restart.
//
// All communication is one-way pull (no telemetry pushed to Thynaptic by this service).
// Set THYNAPTIC_CONFIG_URL="" to run fully offline — no requests are made.
//
// Env vars:
//
//	THYNAPTIC_CONFIG_URL      — remote config endpoint (empty = disabled)
//	THYNAPTIC_CONFIG_INTERVAL — polling interval (default: 1h, min: 5m)
//	THYNAPTIC_ENGINE_ID       — stable ID for this deployment (auto-generated if absent)
package engine

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// EngineConfig is the JSON payload served by the Thynaptic config endpoint.
// Every field is optional — absent fields leave the current value unchanged.
type EngineConfig struct {
	// Version hash — if identical to last applied, the update is skipped.
	Version string `json:"version,omitempty"`

	// ConstitutionOverrides patches the Ops/Code constitution allowlists.
	// Keys map to the override target: e.g. "allowed_commands", "risk_threshold".
	ConstitutionOverrides map[string]any `json:"constitution_overrides,omitempty"`

	// SCAIThreshold overrides the SCAI severity gate (0.0–1.0).
	// Lower = stricter. Nil = unchanged.
	SCAIThreshold *float64 `json:"scai_threshold,omitempty"`

	// AllowedModels overrides the set of Ollama model slugs the engine will use.
	// Empty slice = no change.
	AllowedModels []string `json:"allowed_models,omitempty"`

	// DisabledModules lists brain module slugs to hot-disable.
	DisabledModules []string `json:"disabled_modules,omitempty"`

	// Message is a human-readable changelog entry logged on apply.
	Message string `json:"message,omitempty"`
}

// Applier is the interface RemoteConfigSync calls to apply incoming updates.
// Implement this on your ServerV2 or SovereignEngine to receive config changes.
type Applier interface {
	ApplyEngineConfig(cfg EngineConfig) error
}

// RemoteConfigSync periodically fetches config from THYNAPTIC_CONFIG_URL and
// calls Applier.ApplyEngineConfig. It is a fire-and-forget background service.
type RemoteConfigSync struct {
	url        string
	interval   time.Duration
	engineID   string
	applier    Applier
	httpClient *http.Client
	mu         sync.Mutex
	lastHash   string
	lastApply  time.Time
	stateFile  string // persists last-applied hash across restarts
}

// NewRemoteConfigSync creates a RemoteConfigSync from environment variables.
// Returns nil if THYNAPTIC_CONFIG_URL is empty (offline mode).
func NewRemoteConfigSync(applier Applier) *RemoteConfigSync {
	url := os.Getenv("THYNAPTIC_CONFIG_URL")
	if url == "" {
		log.Println("[RemoteConfig] THYNAPTIC_CONFIG_URL not set — running offline (no remote updates)")
		return nil
	}

	interval := time.Hour
	if v := os.Getenv("THYNAPTIC_CONFIG_INTERVAL"); v != "" {
		if d, err := time.ParseDuration(v); err == nil && d >= 5*time.Minute {
			interval = d
		}
	}

	engineID := os.Getenv("THYNAPTIC_ENGINE_ID")
	if engineID == "" {
		engineID = generateEngineID()
		log.Printf("[RemoteConfig] Generated engine ID: %s (set THYNAPTIC_ENGINE_ID to persist)", engineID)
	}

	stateDir := os.Getenv("ORICLI_STATE_DIR")
	if stateDir == "" {
		stateDir = ".oricli"
	}

	r := &RemoteConfigSync{
		url:       url,
		interval:  interval,
		engineID:  engineID,
		applier:   applier,
		stateFile: filepath.Join(stateDir, "remote_config_state.json"),
		httpClient: &http.Client{Timeout: 15 * time.Second},
	}

	r.loadState()
	log.Printf("[RemoteConfig] Config sync enabled: url=%s interval=%s engine=%s", url, interval, engineID)
	return r
}

// Run starts the polling loop. Blocks until ctx is cancelled.
// Call in a goroutine: go sync.Run(ctx)
func (r *RemoteConfigSync) Run(ctx context.Context) {
	// Apply once immediately on startup, then on interval.
	r.poll(ctx)

	ticker := time.NewTicker(r.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			log.Println("[RemoteConfig] Polling stopped.")
			return
		case <-ticker.C:
			r.poll(ctx)
		}
	}
}

// ForceSync fetches and applies config immediately (useful for testing/CLI).
func (r *RemoteConfigSync) ForceSync(ctx context.Context) error {
	return r.poll(ctx)
}

// LastApply returns the time of the last successful config application.
func (r *RemoteConfigSync) LastApply() time.Time {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.lastApply
}

func (r *RemoteConfigSync) poll(ctx context.Context) error {
	reqURL := fmt.Sprintf("%s?engine=%s", r.url, r.engineID)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, reqURL, nil)
	if err != nil {
		log.Printf("[RemoteConfig] Build request error: %v", err)
		return err
	}
	req.Header.Set("User-Agent", "oricli-engine/1.0 (+https://oricli.thynaptic.com)")

	resp, err := r.httpClient.Do(req)
	if err != nil {
		log.Printf("[RemoteConfig] Fetch error: %v", err)
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotModified {
		log.Println("[RemoteConfig] No new config (304).")
		return nil
	}
	if resp.StatusCode != http.StatusOK {
		log.Printf("[RemoteConfig] Unexpected status: %d", resp.StatusCode)
		return fmt.Errorf("remote config: unexpected status %d", resp.StatusCode)
	}

	body, err := io.ReadAll(io.LimitReader(resp.Body, 64*1024))
	if err != nil {
		log.Printf("[RemoteConfig] Read body error: %v", err)
		return err
	}

	hash := sha256Hash(body)

	r.mu.Lock()
	skip := hash == r.lastHash
	r.mu.Unlock()

	if skip {
		log.Println("[RemoteConfig] Config unchanged — no update needed.")
		return nil
	}

	var cfg EngineConfig
	if err := json.Unmarshal(body, &cfg); err != nil {
		log.Printf("[RemoteConfig] Parse error: %v", err)
		return err
	}

	if cfg.Message != "" {
		log.Printf("[RemoteConfig] Applying update: %s", cfg.Message)
	}

	if err := r.applier.ApplyEngineConfig(cfg); err != nil {
		log.Printf("[RemoteConfig] Apply error: %v", err)
		return err
	}

	r.mu.Lock()
	r.lastHash = hash
	r.lastApply = time.Now()
	r.mu.Unlock()

	r.saveState(hash)
	log.Printf("[RemoteConfig] Config applied successfully (hash=%s)", hash[:8])
	return nil
}

type syncState struct {
	LastHash  string    `json:"last_hash"`
	LastApply time.Time `json:"last_apply"`
	EngineID  string    `json:"engine_id"`
}

func (r *RemoteConfigSync) loadState() {
	data, err := os.ReadFile(r.stateFile)
	if err != nil {
		return
	}
	var s syncState
	if err := json.Unmarshal(data, &s); err == nil {
		r.mu.Lock()
		r.lastHash = s.LastHash
		r.lastApply = s.LastApply
		r.mu.Unlock()
		log.Printf("[RemoteConfig] Loaded prior state: hash=%s applied=%s", s.LastHash[:min(8, len(s.LastHash))], s.LastApply.Format(time.RFC3339))
	}
}

func (r *RemoteConfigSync) saveState(hash string) {
	s := syncState{LastHash: hash, LastApply: r.lastApply, EngineID: r.engineID}
	data, err := json.Marshal(s)
	if err != nil {
		return
	}
	os.MkdirAll(filepath.Dir(r.stateFile), 0700)
	_ = os.WriteFile(r.stateFile, data, 0600)
}

func sha256Hash(b []byte) string {
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}

func generateEngineID() string {
	// Deterministic from hostname — stable across restarts without env config.
	host, _ := os.Hostname()
	h := sha256.Sum256([]byte(host + fmt.Sprintf("%d", os.Getpid())))
	return "engine-" + hex.EncodeToString(h[:4])
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
