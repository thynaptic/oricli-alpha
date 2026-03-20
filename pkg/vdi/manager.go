package vdi

import (
	"context"
	"log"
	"sync"
	"time"

	"github.com/chromedp/chromedp"
)

// --- Pillar 44: VDI Manager ---
// Manages the lifecycle of the headless browser and OS contexts for the Virtual Device Interface.

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
func (m *Manager) Start() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.isReady {
		return nil
	}

	opts := append(chromedp.DefaultExecAllocatorOptions[:],
		chromedp.DisableGPU,
		chromedp.Flag("headless", true), // Keep headless for background automation
		chromedp.Flag("disable-extensions", true),
		chromedp.Flag("disable-dev-shm-usage", true),
		chromedp.Flag("no-sandbox", true),
	)

	allocCtx, cancelAlloc := chromedp.NewExecAllocator(context.Background(), opts...)
	
	// Create a persistent browser context
	ctx, cancelCtx := chromedp.NewContext(allocCtx)

	m.browserCtx = ctx
	// We need to keep both cancel functions to shut down cleanly
	m.cancelBrowser = func() {
		cancelCtx()
		cancelAlloc()
	}

	// Ping the browser to ensure it started
	if err := chromedp.Run(ctx); err != nil {
		m.cancelBrowser()
		return err
	}

	m.isReady = true
	log.Println("[VDI] Persistent browser session initialized.")
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
