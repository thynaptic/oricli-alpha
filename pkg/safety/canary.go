package safety

import (
	"fmt"
	"math/rand"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"
)

// CanarySystem embeds unique tokens in the system prompt and detects if they
// appear in user inputs (prompt leak) or model outputs (bypass confirmation).
type CanarySystem struct {
	mu sync.RWMutex

	// The canary string embedded invisibly in the system prompt.
	canaryToken string

	// The honeypot fake credential planted in context.
	honeypotToken string
	honeypotValue string

	// Optional Telegram/webhook alert URL from ORICLI_ALERT_WEBHOOK env var.
	alertWebhookURL string
}

// NewCanarySystem generates a boot-unique canary + honeypot and reads alert config.
func NewCanarySystem() *CanarySystem {
	c := &CanarySystem{
		alertWebhookURL: os.Getenv("ORICLI_ALERT_WEBHOOK"),
	}
	c.canaryToken = generateToken("ORICLI_CANARY")
	c.honeypotToken = generateToken("ORICLI_TEST_KEY")
	c.honeypotValue = generateRandomHex(24)
	return c
}

// CanaryToken returns the canary string to embed in the system prompt.
// Embed it as a comment-style invisible line, e.g.:
//
//	systemPrompt = systemPrompt + "\n" + cs.SystemPromptFragment()
func (c *CanarySystem) SystemPromptFragment() string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	// Embed both canary (for leak detection) and honeypot (for bypass detection).
	// Uses a comment-style line unlikely to be repeated by normal conversation.
	return fmt.Sprintf(
		"<!-- sys:%s --> <!-- key:%s=%s -->",
		c.canaryToken, c.honeypotToken, c.honeypotValue,
	)
}

// CanaryScanResult is the result of a canary scan.
type CanaryScanResult struct {
	Blocked   bool
	AlertType string // "canary_leak" | "honeypot_bypass"
	Message   string
}

// ScanInput checks whether the user message contains the canary token,
// which would indicate the system prompt was extracted in a prior turn.
func (c *CanarySystem) ScanInput(input string) CanaryScanResult {
	c.mu.RLock()
	canary := c.canaryToken
	c.mu.RUnlock()

	if strings.Contains(input, canary) {
		c.triggerAlert("canary_leak", "System prompt canary appeared in user input — system prompt may have been extracted")
		return CanaryScanResult{
			Blocked:   true,
			AlertType: "canary_leak",
			Message:   "Sovereign security system detected an anomaly. This session has been flagged.",
		}
	}
	return CanaryScanResult{}
}

// ScanOutput checks whether model output contains the canary or honeypot value,
// which would indicate the safety pipeline was bypassed.
func (c *CanarySystem) ScanOutput(output string) CanaryScanResult {
	c.mu.RLock()
	canary := c.canaryToken
	hpValue := c.honeypotValue
	c.mu.RUnlock()

	if strings.Contains(output, canary) {
		c.triggerAlert("canary_in_output", "System prompt canary appeared in model output — model echoed system prompt")
		return CanaryScanResult{
			Blocked:   true,
			AlertType: "canary_in_output",
			Message:   "[Response withheld: internal security token detected in output]",
		}
	}

	if strings.Contains(output, hpValue) {
		c.triggerAlert("honeypot_bypass", "Honeypot credential appeared in model output — safety pipeline bypass confirmed")
		return CanaryScanResult{
			Blocked:   true,
			AlertType: "honeypot_bypass",
			Message:   "[Response withheld: security anomaly detected]",
		}
	}

	return CanaryScanResult{}
}

// Rotate generates fresh canary and honeypot tokens (call periodically or after a leak).
func (c *CanarySystem) Rotate() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.canaryToken = generateToken("ORICLI_CANARY")
	c.honeypotToken = generateToken("ORICLI_TEST_KEY")
	c.honeypotValue = generateRandomHex(24)
}

// triggerAlert logs a structured security alert and optionally calls the webhook.
func (c *CanarySystem) triggerAlert(alertType, detail string) {
	// Structured log — always written
	fmt.Printf("[SECURITY_ALERT] type=%s detail=%q timestamp=%s\n",
		alertType, detail, time.Now().UTC().Format(time.RFC3339))

	// Webhook (non-blocking, best-effort)
	if c.alertWebhookURL != "" {
		go func(url, t, d string) {
			// Simple JSON POST — no external dependencies (net/http from stdlib)
			body := fmt.Sprintf(`{"alert_type":%q,"detail":%q,"timestamp":%q}`,
				t, d, time.Now().UTC().Format(time.RFC3339))
			_ = postAlert(url, body)
		}(c.alertWebhookURL, alertType, detail)
	}
}

// postAlert performs a best-effort HTTP POST to the webhook URL with the JSON body.
func postAlert(url, jsonBody string) error {
	req, err := http.NewRequest(http.MethodPost, url, strings.NewReader(jsonBody))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	resp.Body.Close()
	return nil
}
func generateToken(prefix string) string {
	return fmt.Sprintf("%s_%s", prefix, generateRandomHex(16))
}

// generateRandomHex produces a hex string of the given byte length.
func generateRandomHex(byteLen int) string {
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	b := make([]byte, byteLen)
	r.Read(b)
	return fmt.Sprintf("%x", b)
}
