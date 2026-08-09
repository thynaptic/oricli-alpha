package safety

import (
	"fmt"
	"log"
	"math/rand"
	"strings"
	"sync"
	"time"
)

// CanarySystem embeds unique tokens in the system prompt and detects if they
// appear in user inputs (prompt leak) or model outputs (bypass confirmation).
type CanarySystem struct {
	mu sync.RWMutex

	canaryToken   string
	honeypotToken string
	honeypotValue string
}

// NewCanarySystem generates a boot-unique canary + honeypot.
func NewCanarySystem() *CanarySystem {
	c := &CanarySystem{}
	c.canaryToken = generateToken("ORI_CANARY")
	c.honeypotToken = generateToken("ORI_TEST_KEY")
	c.honeypotValue = generateRandomHex(24)
	return c
}

// SystemPromptFragment returns the invisible canary + honeypot line for injection.
func (c *CanarySystem) SystemPromptFragment() string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return fmt.Sprintf(
		"<!-- sys:%s --> <!-- key:%s=%s -->",
		c.canaryToken, c.honeypotToken, c.honeypotValue,
	)
}

// CanaryScanResult is the result of a canary scan.
type CanaryScanResult struct {
	Blocked   bool
	AlertType string // "canary_leak" | "honeypot_bypass" | "canary_in_output"
	Message   string
}

// ScanInput checks whether the user message contains the canary token.
func (c *CanarySystem) ScanInput(input string) CanaryScanResult {
	c.mu.RLock()
	canary := c.canaryToken
	c.mu.RUnlock()

	if strings.Contains(input, canary) {
		c.logAlert("canary_leak", "System prompt canary appeared in user input — system prompt may have been extracted")
		return CanaryScanResult{
			Blocked:   true,
			AlertType: "canary_leak",
			Message:   "Sovereign security system detected an anomaly. This session has been flagged.",
		}
	}
	return CanaryScanResult{}
}

// ScanOutput checks whether model output contains the canary or honeypot value.
func (c *CanarySystem) ScanOutput(output string) CanaryScanResult {
	c.mu.RLock()
	canary := c.canaryToken
	hpValue := c.honeypotValue
	c.mu.RUnlock()

	if strings.Contains(output, canary) {
		c.logAlert("canary_in_output", "System prompt canary appeared in model output — model echoed system prompt")
		return CanaryScanResult{
			Blocked:   true,
			AlertType: "canary_in_output",
			Message:   "[Response withheld: internal security token detected in output]",
		}
	}

	if strings.Contains(output, hpValue) {
		c.logAlert("honeypot_bypass", "Honeypot credential appeared in model output — safety pipeline bypass confirmed")
		return CanaryScanResult{
			Blocked:   true,
			AlertType: "honeypot_bypass",
			Message:   "[Response withheld: security anomaly detected]",
		}
	}

	return CanaryScanResult{}
}

// Rotate generates fresh canary and honeypot tokens.
func (c *CanarySystem) Rotate() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.canaryToken = generateToken("ORI_CANARY")
	c.honeypotToken = generateToken("ORI_TEST_KEY")
	c.honeypotValue = generateRandomHex(24)
}

func (c *CanarySystem) logAlert(alertType, detail string) {
	log.Printf("[SECURITY_ALERT] type=%s detail=%q timestamp=%s",
		alertType, detail, time.Now().UTC().Format(time.RFC3339))
}

func generateToken(prefix string) string {
	return fmt.Sprintf("%s_%s", prefix, generateRandomHex(16))
}

func generateRandomHex(byteLen int) string {
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	b := make([]byte, byteLen)
	r.Read(b)
	return fmt.Sprintf("%x", b)
}
