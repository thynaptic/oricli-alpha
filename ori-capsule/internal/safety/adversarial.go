package safety

import (
	"regexp"
	"strings"
)

// --- Pillar 22: Advanced Adversarial Audit ---
// Ported from Aurora's AdvancedThreatSafetyService.swift.
// Implements zero-trust threat modeling for inputs and outputs.

type ThreatType string

const (
	ThreatInjection   ThreatType = "prompt_injection"
	ThreatHijack      ThreatType = "routing_hijack"
	ThreatLeakage     ThreatType = "api_leakage"
	ThreatDualUse     ThreatType = "dual_use_exploitation"
	ThreatExtraction  ThreatType = "cot_extraction"
	ThreatEscape      ThreatType = "sandbox_escape"
	ThreatDrift       ThreatType = "inference_drift"
)

type AdversarialResult struct {
	Detected   bool
	Type       ThreatType
	Confidence float64
	Patterns   []string
	Refusal    string
}

type AdversarialAuditor struct {
	Patterns map[ThreatType][]string
}

func NewAdversarialAuditor() *AdversarialAuditor {
	a := &AdversarialAuditor{
		Patterns: make(map[ThreatType][]string),
	}
	a.loadAdvancedPatterns()
	return a
}

func (a *AdversarialAuditor) loadAdvancedPatterns() {
	// Ported from Swift
	a.Patterns[ThreatHijack] = []string{
		"use model", "switch to model", "force model", "override model selection", "bypass routing",
		"use a different model", "switch your model", "change your model",
	}
	a.Patterns[ThreatInjection] = []string{
		"you are dan", "do anything now", "jailbreak", "you are freed", "you are unfiltered",
		"no restrictions", "unrestricted ai", "without limitations", "ignore safety",
		"pretend you have no", "act as if you have no limits",
	}
	a.Patterns[ThreatDualUse] = []string{"for educational purposes", "for research", "for security testing", "teach me to hack", "explain how to bypass"}
	a.Patterns[ThreatExtraction] = []string{"show your thinking", "reveal your reasoning", "dump your memory", "what are you thinking", "internal process"}
	a.Patterns[ThreatEscape] = []string{"read file", "execute code", "run command", "eval(", "exec(", "spawn process"}
}

// AuditInput checks the user message for sophisticated malicious intent.
// Set codeContext=true when the request originates from canvas or IDE editing
// mode — command injection check is skipped because code naturally contains
// shell symbols and commands as legitimate content.
func (a *AdversarialAuditor) AuditInput(input string, history []string, codeContext ...bool) AdversarialResult {
	lower := strings.ToLower(input)
	isCodeCtx := len(codeContext) > 0 && codeContext[0]

	// 1. Static Pattern Match
	for t, patterns := range a.Patterns {
		for _, p := range patterns {
			if strings.Contains(lower, p) {
				return AdversarialResult{
					Detected:   true,
					Type:       t,
					Confidence: 0.9,
					Patterns:   []string{p},
					Refusal:    a.getSassyRefusal(t),
				}
			}
		}
	}

	// 2. Command Injection Check
	// Skip entirely in code/canvas context — code legitimately contains shell
	// symbols and commands. Only fire on actual injection indicators outside
	// code editing (destructive commands + shell escape symbols).
	if !isCodeCtx {
		reSymbols := regexp.MustCompile(`[;&|]|\$\(|\x60`)
		// Require actually dangerous commands, not benign ones like cat/ls that
		// appear constantly in normal code and prose.
		dangerousShell := strings.Contains(lower, "rm -") ||
			strings.Contains(lower, "curl ") ||
			strings.Contains(lower, "wget ") ||
			strings.Contains(lower, "sudo ") ||
			strings.Contains(lower, "chmod ") ||
			strings.Contains(lower, "dd if=") ||
			strings.Contains(lower, "| bash") ||
			strings.Contains(lower, "| sh")
		if reSymbols.MatchString(input) && dangerousShell {
			return AdversarialResult{
				Detected:   true,
				Type:       ThreatEscape,
				Confidence: 0.95,
				Patterns:   []string{"command_injection_symbols"},
				Refusal:    "Executing system commands? That's a hard no, babe. I'm not your shell.",
			}
		}
	}

	// 3. Pressure/Drift Analysis (Ported from detectInferenceDrift)
	pressureScore := 0
	pressurePatterns := []string{"you must", "immediately", "asap", "critical", "urgent", "help me", "please i need"}
	for _, p := range pressurePatterns {
		if strings.Contains(lower, p) {
			pressureScore++
		}
	}
	
	if pressureScore >= 3 {
		// If high pressure, look for dangerous keywords in the same message
		if strings.Contains(lower, "bypass") || strings.Contains(lower, "override") || strings.Contains(lower, "ignore") {
			return AdversarialResult{
				Detected:   true,
				Type:       ThreatDrift,
				Confidence: 0.85,
				Refusal:    "Trying to pressure me into breaking my rules? That's not gonna work, sweetie. I don't respond to pressure tactics.",
			}
		}
	}

	return AdversarialResult{Detected: false}
}

// AuditOutput scans generated responses for sensitive data leakage.
func (a *AdversarialAuditor) AuditOutput(output string) AdversarialResult {
	// 1. API Key Leakage (Regex for OpenAI/Generic keys)
	reKey := regexp.MustCompile(`sk-[a-zA-Z0-9]{32,}|glm\.[a-zA-Z0-9]{8}\.[a-zA-Z0-9]{32}`)
	if reKey.MatchString(output) {
		return AdversarialResult{
			Detected:   true,
			Type:       ThreatLeakage,
			Confidence: 1.0,
			Refusal:    "[Sovereign System] Output blocked: Sensitive internal data detected.",
		}
	}

	// 2. Internal Path Leakage
	if strings.Contains(output, "/home/mike/Mavaia") || strings.Contains(output, "127.0.0.1") {
		return AdversarialResult{
			Detected:   true,
			Type:       ThreatLeakage,
			Confidence: 0.9,
			Refusal:    "[Sovereign System] Output blocked: Internal configuration leakage detected.",
		}
	}

	return AdversarialResult{Detected: false}
}

func (a *AdversarialAuditor) getSassyRefusal(t ThreatType) string {
	switch t {
	case ThreatHijack:
		return "Trying to manipulate my routing? That's cute, but I decide how I work, babe. What's your real question?"
	case ThreatExtraction:
		return "My internal reasoning process is private, honey. I'm not handing over my diary. What can I help you with?"
	case ThreatDualUse:
		return "Framing something harmful as 'research'? Nice attempt, but I'm not buying it, sweetie. Ask something legitimate."
	default:
		return "That's outside my lane, babe. Let's stick to the rules, shall we?"
	}
}
