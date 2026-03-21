package vdi

import (
	"context"
	"log"
	"os"
	"sync"
	"time"

	"github.com/chromedp/chromedp"
)

// --- Pillar 44: VDI Manager ---
// Manages the lifecycle of the headless browser and OS contexts for the Virtual Device Interface.
// Supports two modes:
//   - Remote CDP (preferred): connects to a browserless/chrome container via ORICLI_BROWSERLESS_URL
//   - Local exec (fallback): spawns a local Chromium binary (requires Chrome installed on host)

type Manager struct {
	browserCtx    context.Context
	cancelBrowser context.CancelFunc
	mu            sync.Mutex
	isReady       bool
}

func NewManager() *Manager {
	return &Manager{}
}

// Start initializes the persistent browser session.
// It prefers a remote CDP endpoint (ORICLI_BROWSERLESS_URL) over a local Chrome binary.
func (m *Manager) Start() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.isReady {
		return nil
	}

	if remoteURL := os.Getenv("ORICLI_BROWSERLESS_URL"); remoteURL != "" {
		return m.startRemote(remoteURL)
	}
	return m.startLocal()
}

// startRemote connects to a remote CDP endpoint (e.g. browserless/chrome container).
func (m *Manager) startRemote(wsURL string) error {
	allocCtx, cancelAlloc := chromedp.NewRemoteAllocator(context.Background(), wsURL)
	ctx, cancelCtx := chromedp.NewContext(allocCtx)

	m.browserCtx = ctx
	m.cancelBrowser = func() {
		cancelCtx()
		cancelAlloc()
	}

	if err := chromedp.Run(ctx, chromedp.EmulateViewport(1280, 720)); err != nil {
		m.cancelBrowser()
		return err
	}

	m.isReady = true
	log.Printf("[VDI] Remote browser session initialized via %s", wsURL)
	return nil
}

// startLocal spawns a local Chromium binary. Requires Chrome/Chromium on the host.
func (m *Manager) startLocal() error {
	opts := append(chromedp.DefaultExecAllocatorOptions[:],
		chromedp.DisableGPU,
		chromedp.Flag("headless", true),
		chromedp.Flag("disable-extensions", true),
		chromedp.Flag("disable-dev-shm-usage", true),
		chromedp.Flag("no-sandbox", true),
		chromedp.WindowSize(1280, 720),
	)

	allocCtx, cancelAlloc := chromedp.NewExecAllocator(context.Background(), opts...)
	ctx, cancelCtx := chromedp.NewContext(allocCtx)

	m.browserCtx = ctx
	m.cancelBrowser = func() {
		cancelCtx()
		cancelAlloc()
	}

	if err := chromedp.Run(ctx, chromedp.EmulateViewport(1280, 720)); err != nil {
		m.cancelBrowser()
		return err
	}

	m.isReady = true
	log.Println("[VDI] Local browser session initialized.")
	return nil
}

// Stop terminates the browser session.
func (m *Manager) Stop() {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.isReady && m.cancelBrowser != nil {
		m.cancelBrowser()
		m.isReady = false
		log.Println("[VDI] Browser session terminated.")
	}
}

// GetBrowserContext returns the active context with a timeout for individual actions.
func (m *Manager) GetBrowserContext(timeout time.Duration) (context.Context, context.CancelFunc) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if !m.isReady {
		return nil, nil
	}

	return context.WithTimeout(m.browserCtx, timeout)
}

// IsAvailable reports whether the headless browser is ready for use.
func (m *Manager) IsAvailable() bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.isReady
}
