package vdi

import (
	"fmt"
	"strings"
	"time"

	"github.com/chromedp/chromedp"
)

// --- Pillar 45: Sovereign Browser Automation ---
// Implements direct DOM interaction using chromedp.

// Navigate opens a URL in the active VDI browser session.
func (m *Manager) Navigate(url string) (string, error) {
	ctx, cancel := m.GetBrowserContext(30 * time.Second)
	if ctx == nil {
		return "", fmt.Errorf("VDI browser is not initialized")
	}
	defer cancel()

	var pageTitle string
	err := chromedp.Run(ctx,
		chromedp.Navigate(url),
		chromedp.Title(&pageTitle),
	)

	if err != nil {
		return "", fmt.Errorf("navigation failed: %v", err)
	}

	return fmt.Sprintf("Successfully navigated to %s (Title: %s)", url, pageTitle), nil
}

// ScrapeExtracts clean text from the body of the current page.
func (m *Manager) Scrape() (string, error) {
	ctx, cancel := m.GetBrowserContext(15 * time.Second)
	if ctx == nil {
		return "", fmt.Errorf("VDI browser is not initialized")
	}
	defer cancel()

	var textContent string
	err := chromedp.Run(ctx,
		chromedp.Text("body", &textContent, chromedp.NodeVisible),
	)

	if err != nil {
		return "", fmt.Errorf("scrape failed: %v", err)
	}

	// Clean up whitespace
	clean := strings.Join(strings.Fields(textContent), " ")
	if len(clean) > 8000 {
		clean = clean[:8000] + "... (truncated)"
	}

	return clean, nil
}

// Click interacts with an element on the page using a CSS selector.
func (m *Manager) Click(selector string) (string, error) {
	ctx, cancel := m.GetBrowserContext(15 * time.Second)
	if ctx == nil {
		return "", fmt.Errorf("VDI browser is not initialized")
	}
	defer cancel()

	err := chromedp.Run(ctx,
		chromedp.WaitVisible(selector),
		chromedp.Click(selector, chromedp.NodeVisible),
	)

	if err != nil {
		return "", fmt.Errorf("click failed on %s: %v", selector, err)
	}

	return fmt.Sprintf("Clicked element matching: %s", selector), nil
}

// Type fills out a form or input field.
func (m *Manager) Type(selector string, text string) (string, error) {
	ctx, cancel := m.GetBrowserContext(15 * time.Second)
	if ctx == nil {
		return "", fmt.Errorf("VDI browser is not initialized")
	}
	defer cancel()

	err := chromedp.Run(ctx,
		chromedp.WaitVisible(selector),
		chromedp.SendKeys(selector, text, chromedp.NodeVisible),
	)

	if err != nil {
		return "", fmt.Errorf("type failed on %s: %v", selector, err)
	}

	return fmt.Sprintf("Typed text into element matching: %s", selector), nil
}
