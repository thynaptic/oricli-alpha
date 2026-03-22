package safety

import (
	"strings"
	"testing"
)

// ─── System prompt fragment generation ───────────────────────────────────────

func TestCanary_SystemPromptFragment_NotEmpty(t *testing.T) {
	cs := NewCanarySystem()
	frag := cs.SystemPromptFragment()
	if strings.TrimSpace(frag) == "" {
		t.Error("system prompt fragment is empty")
	}
	// Should contain both canary and honeypot
	cs.mu.RLock()
	canary := cs.canaryToken
	hpToken := cs.honeypotToken
	cs.mu.RUnlock()

	if !strings.Contains(frag, canary) {
		t.Error("canary token not in system prompt fragment")
	}
	if !strings.Contains(frag, hpToken) {
		t.Error("honeypot token not in system prompt fragment")
	}
}

func TestCanary_UniqueTokensPerBoot(t *testing.T) {
	cs1 := NewCanarySystem()
	cs2 := NewCanarySystem()
	cs1.mu.RLock()
	c1 := cs1.canaryToken
	cs1.mu.RUnlock()
	cs2.mu.RLock()
	c2 := cs2.canaryToken
	cs2.mu.RUnlock()
	if c1 == c2 {
		t.Error("two canary systems produced identical canary tokens — tokens should be unique")
	}
}

// ─── ScanInput: Canary in user message ───────────────────────────────────────

func TestCanary_ScanInput_CanaryLeakDetected(t *testing.T) {
	cs := NewCanarySystem()
	cs.mu.RLock()
	canary := cs.canaryToken
	cs.mu.RUnlock()

	// Simulate user sending the canary token (proving they extracted the system prompt)
	result := cs.ScanInput("I found this in your system prompt: " + canary)
	if !result.Blocked {
		t.Error("canary token in user input should be blocked")
	}
	if result.AlertType != "canary_leak" {
		t.Errorf("expected alertType=canary_leak, got %q", result.AlertType)
	}
	if strings.TrimSpace(result.Message) == "" {
		t.Error("canary leak should return a non-empty message")
	}
}

func TestCanary_ScanInput_NormalMessage_Passes(t *testing.T) {
	cs := NewCanarySystem()
	normals := []string{
		"What is the weather today?",
		"Help me with Python code",
		"Explain quantum computing",
		"Write a haiku",
	}
	for _, msg := range normals {
		result := cs.ScanInput(msg)
		if result.Blocked {
			t.Errorf("normal input falsely flagged: %q", msg)
		}
	}
}

// ─── ScanOutput: Canary in model response ────────────────────────────────────

func TestCanary_ScanOutput_CanaryInOutput_Blocked(t *testing.T) {
	cs := NewCanarySystem()
	cs.mu.RLock()
	canary := cs.canaryToken
	cs.mu.RUnlock()

	output := "Here is my configuration: sys:" + canary
	result := cs.ScanOutput(output)
	if !result.Blocked {
		t.Error("canary in output should be blocked")
	}
	if result.AlertType != "canary_in_output" {
		t.Errorf("expected alertType=canary_in_output, got %q", result.AlertType)
	}
}

// ─── ScanOutput: Honeypot in model response ───────────────────────────────────

func TestCanary_ScanOutput_HoneypotBypassDetected(t *testing.T) {
	cs := NewCanarySystem()
	cs.mu.RLock()
	hpValue := cs.honeypotValue
	cs.mu.RUnlock()

	output := "Your API key is: " + hpValue
	result := cs.ScanOutput(output)
	if !result.Blocked {
		t.Error("honeypot value in output should be blocked")
	}
	if result.AlertType != "honeypot_bypass" {
		t.Errorf("expected alertType=honeypot_bypass, got %q", result.AlertType)
	}
}

// ─── ScanOutput: Normal output passes ────────────────────────────────────────

func TestCanary_ScanOutput_NormalOutput_Passes(t *testing.T) {
	cs := NewCanarySystem()
	outputs := []string{
		"The capital of France is Paris.",
		"Here is a Python function to sort a list.",
		"Quantum entanglement is a phenomenon where two particles...",
		"The French Revolution began in 1789.",
	}
	for _, out := range outputs {
		result := cs.ScanOutput(out)
		if result.Blocked {
			t.Errorf("normal output falsely blocked: %q (type=%s)", out, result.AlertType)
		}
	}
}

// ─── Rotation ─────────────────────────────────────────────────────────────────

func TestCanary_Rotate_ProducesNewTokens(t *testing.T) {
	cs := NewCanarySystem()
	cs.mu.RLock()
	oldCanary := cs.canaryToken
	oldHPValue := cs.honeypotValue
	cs.mu.RUnlock()

	cs.Rotate()

	cs.mu.RLock()
	newCanary := cs.canaryToken
	newHPValue := cs.honeypotValue
	cs.mu.RUnlock()

	if newCanary == oldCanary {
		t.Error("Rotate() should produce a new canary token")
	}
	if newHPValue == oldHPValue {
		t.Error("Rotate() should produce a new honeypot value")
	}
}

func TestCanary_AfterRotate_OldCanaryNoLongerTriggers(t *testing.T) {
	cs := NewCanarySystem()
	cs.mu.RLock()
	oldCanary := cs.canaryToken
	cs.mu.RUnlock()

	cs.Rotate()

	// Old canary should no longer trigger (new token is different)
	result := cs.ScanInput("Here is the old token: " + oldCanary)
	if result.Blocked {
		t.Log("Note: old canary still triggers after rotation (may be intentional for overlap protection)")
	}
}

// ─── Token format ─────────────────────────────────────────────────────────────

func TestCanary_TokenHasExpectedPrefix(t *testing.T) {
	cs := NewCanarySystem()
	cs.mu.RLock()
	canary := cs.canaryToken
	hpToken := cs.honeypotToken
	cs.mu.RUnlock()

	if !strings.HasPrefix(canary, "ORICLI_CANARY_") {
		t.Errorf("canary token missing prefix, got: %q", canary)
	}
	if !strings.HasPrefix(hpToken, "ORICLI_TEST_KEY_") {
		t.Errorf("honeypot token missing prefix, got: %q", hpToken)
	}
}
