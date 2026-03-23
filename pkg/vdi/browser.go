package vdi

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
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

// NavigateAndExtract navigates to url, waits for the DOM to settle, scrapes
// the main content, strips common chrome (nav/header/footer/ads), and returns
// clean text capped at maxChars. Designed for CuriosityDaemon deep-forage.
func (m *Manager) NavigateAndExtract(url string, maxChars int) (string, error) {
	ctx, cancel := m.GetBrowserContext(10 * time.Second)
	if ctx == nil {
		return "", fmt.Errorf("VDI browser is not initialized")
	}
	defer cancel()

	// Try content selectors in priority order; fall back to body.
	contentSelectors := []string{"article", "main", "[role=main]", ".content", "#content", "body"}

	var rawText string
	if err := chromedp.Run(ctx, chromedp.Navigate(url), chromedp.WaitVisible("body", chromedp.ByQuery)); err != nil {
		return "", fmt.Errorf("NavigateAndExtract navigation failed for %s: %v", url, err)
	}

	for _, sel := range contentSelectors {
		var t string
		if err := chromedp.Run(ctx, chromedp.Text(sel, &t, chromedp.NodeVisible, chromedp.ByQuery)); err == nil {
			if len(strings.TrimSpace(t)) > 100 {
				rawText = t
				break
			}
		}
	}

	return cleanPageText(rawText, maxChars), nil
}

// cleanPageText normalises whitespace and strips common boilerplate lines.
func cleanPageText(raw string, maxChars int) string {
	lines := strings.Split(raw, "\n")
	var kept []string
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if len(line) < 20 {
			continue // skip nav crumbs, single words, button labels
		}
		// Skip lines that look like navigation/cookie banners
		lower := strings.ToLower(line)
		if strings.HasPrefix(lower, "cookie") ||
			strings.HasPrefix(lower, "accept") ||
			strings.HasPrefix(lower, "subscribe") ||
			strings.HasPrefix(lower, "advertisement") ||
			strings.HasPrefix(lower, "skip to") {
			continue
		}
		kept = append(kept, line)
	}
	result := strings.Join(kept, " ")
	result = strings.Join(strings.Fields(result), " ")
	if maxChars > 0 && len(result) > maxChars {
		result = result[:maxChars] + "… [truncated]"
	}
	return result
}


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

// Screenshot captures the current browser viewport as a PNG (base64).
func (m *Manager) Screenshot() (string, error) {
	ctx, cancel := m.GetBrowserContext(15 * time.Second)
	if ctx == nil {
		return "", fmt.Errorf("VDI browser is not initialized")
	}
	defer cancel()

	var buf []byte
	if err := chromedp.Run(ctx, chromedp.CaptureScreenshot(&buf)); err != nil {
		return "", fmt.Errorf("screenshot failed: %v", err)
	}

	// We return the raw base64 data for the vision model
	return fmt.Sprintf("%s", strings.TrimSpace(string(buf))), nil
}

// ClickAt executes a mouse click at specific pixel coordinates.
func (m *Manager) ClickAt(x, y float64) (string, error) {
	ctx, cancel := m.GetBrowserContext(15 * time.Second)
	if ctx == nil {
		return "", fmt.Errorf("VDI browser is not initialized")
	}
	defer cancel()

	err := chromedp.Run(ctx,
		chromedp.MouseClickXY(x, y),
	)

	if err != nil {
		return "", fmt.Errorf("coordinate click failed at (%.2f, %.2f): %v", x, y, err)
	}

	return fmt.Sprintf("Clicked at coordinates: (%.2f, %.2f)", x, y), nil
}

// NavigateAndSee is Oricli's visual comprehension path.
// It navigates to a URL, captures a screenshot, and sends it to a vision model
// for a natural-language description of what the page looks like visually.
// Falls back to DOM text extraction if the vision model is unavailable.
//
// The vision model is controlled by OLLAMA_VISION_MODEL (default: moondream).
// The Ollama base URL defaults to http://127.0.0.1:11434.
func (m *Manager) NavigateAndSee(rawURL string) (string, error) {
	ctx, cancel := m.GetBrowserContext(20 * time.Second)
	if ctx == nil {
		return "", fmt.Errorf("VDI browser not initialised")
	}
	defer cancel()

	if err := chromedp.Run(ctx,
		chromedp.Navigate(rawURL),
		chromedp.WaitVisible("body", chromedp.ByQuery),
		chromedp.Sleep(800*time.Millisecond), // let lazy-loaded content settle
	); err != nil {
		return "", fmt.Errorf("NavigateAndSee navigation failed: %v", err)
	}

	var buf []byte
	if err := chromedp.Run(ctx, chromedp.CaptureScreenshot(&buf)); err != nil {
		return "", fmt.Errorf("screenshot capture failed: %v", err)
	}

	b64img := base64.StdEncoding.EncodeToString(buf)
	return askVisionModel(rawURL, b64img)
}

// askVisionModel sends a base64 PNG to the configured Ollama vision model
// and returns its natural-language description of the page.
func askVisionModel(pageURL, b64img string) (string, error) {
	ollamaURL := os.Getenv("OLLAMA_GEN_URL")
	if ollamaURL == "" {
		ollamaURL = "http://127.0.0.1:11434"
	}
	model := os.Getenv("OLLAMA_VISION_MODEL")
	if model == "" {
		model = "moondream"
	}

	prompt := fmt.Sprintf(
		"You are analyzing a web page screenshot. URL: %s\n"+
			"Describe: 1) The page topic/purpose. 2) Key information visible. "+
			"3) Any data tables, charts, or images. Be concise and factual.",
		pageURL,
	)

	payload := map[string]interface{}{
		"model":  model,
		"stream": false,
		"messages": []map[string]interface{}{
			{
				"role":    "user",
				"content": prompt,
				"images":  []string{b64img},
			},
		},
		"options": map[string]interface{}{
			"num_predict": 400,
			"num_thread":  6,
		},
	}

	body, _ := json.Marshal(payload)
	resp, err := (&http.Client{Timeout: 120 * time.Second}).Post(
		ollamaURL+"/api/chat",
		"application/json",
		bytes.NewReader(body),
	)
	if err != nil {
		return "", fmt.Errorf("vision model request failed: %v", err)
	}
	defer resp.Body.Close()

	raw, _ := io.ReadAll(resp.Body)
	var result struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	}
	if err := json.Unmarshal(raw, &result); err != nil || result.Message.Content == "" {
		return "", fmt.Errorf("vision model returned empty response")
	}
	return result.Message.Content, nil
}
