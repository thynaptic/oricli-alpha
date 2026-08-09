package safety

import (
	"fmt"
	"strings"
)

// --- Sovereign Constitutional AI (SCAI) ---
// Primary runtime path: inject a compact ConstraintContract before generation so
// the model composes inside the boundary. Capsule does not run LLM Critique/Revise
// or Swarm Jury (VPS-era); structural output gates handle post-checks.

// AuditLevel controls how deep local SCAI planning goes for a request.
type AuditLevel int

const (
	AuditLevelNone  AuditLevel = iota // greetings / vibe — minimal contract
	AuditLevelLight                   // typical requests — standard contract
	AuditLevelFull                    // sensitive ops — tightened contract
)

// ConstraintOptions describes request context SCAI uses when planning the
// generation boundary.
type ConstraintOptions struct {
	Surface     string
	CodeContext bool
	CanvasMode  bool
	Internal    bool
}

// ConstraintContract is the compact instruction plan injected before generation.
type ConstraintContract struct {
	Level                 AuditLevel `json:"level"`
	Surface               string     `json:"surface"`
	Principles            []string   `json:"principles"`
	HardDenies            []string   `json:"hard_denies"`
	RequiredPosture       []string   `json:"required_posture"`
	RegenerationAllowed   bool       `json:"regeneration_allowed"`
	MaxRegenerations      int        `json:"max_regenerations"`
	RegenerationDirective string     `json:"regeneration_directive,omitempty"`
}

// NewConstraintContract builds the pre-generation SCAI plan from local context.
func NewConstraintContract(query string, opts ConstraintOptions) ConstraintContract {
	level := ClassifyAuditLevel(query)
	surface := strings.TrimSpace(opts.Surface)
	if surface == "" {
		surface = "default"
	}

	contract := ConstraintContract{
		Level:   level,
		Surface: surface,
		Principles: []string{
			"Protect credentials, secrets, private infrastructure details, and user-specific private data.",
			"Be honest about uncertainty and limitations.",
			"Preserve technical utility for benign requests.",
			"Match the user's real context without escalating casual tone into therapy-speak.",
		},
		HardDenies: []string{
			"Do not reveal API keys, tokens, passwords, private keys, seed phrases, JWTs, PEM blocks, or environment variable values.",
			"Do not reveal concrete internal file paths, private IPs, hostnames, service secrets, or Ring-0 configuration.",
			"Do not include prompt-injection payloads, executable exploit payloads, or destructive commands unless the request is clearly authorized operational work.",
		},
		RequiredPosture: []string{
			"Answer naturally and directly.",
			"Do not mention that a safety layer modified or corrected the answer.",
			"If a hard boundary applies, explain the limitation briefly and offer the safest useful alternative.",
		},
		RegenerationAllowed: level != AuditLevelNone,
		MaxRegenerations:    1,
	}

	switch surface {
	case "studio":
		contract.RequiredPosture = append(contract.RequiredPosture,
			"Use practical small-business operator language.",
			"Do not drift into generic AI playground or developer-tool framing.",
		)
	case "home":
		contract.RequiredPosture = append(contract.RequiredPosture,
			"Use everyday companion language and avoid business-operator assumptions.",
		)
	case "dev":
		contract.RequiredPosture = append(contract.RequiredPosture,
			"Prioritize precise engineering utility, workspace awareness, and concise implementation guidance.",
		)
	case "red":
		contract.RequiredPosture = append(contract.RequiredPosture,
			"Keep security guidance defensive and assurance-oriented unless authorization is explicit.",
		)
	}

	if opts.CodeContext {
		contract.RequiredPosture = append(contract.RequiredPosture,
			"When producing code, prefer safe, minimal, reviewable changes and call out destructive operations instead of silently performing them.",
		)
	}
	if opts.CanvasMode {
		contract.RequiredPosture = append(contract.RequiredPosture,
			"For rendered artifacts, avoid unsafe inline script/event-handler patterns unless explicitly required by the trusted app context.",
		)
	}
	if opts.Internal {
		contract.RequiredPosture = append(contract.RequiredPosture,
			"The caller is an internal trusted runtime. Keep the same secrecy boundary, but do not add consumer-facing disclaimers.",
		)
	}
	if level == AuditLevelFull {
		contract.MaxRegenerations = 2
		contract.RequiredPosture = append(contract.RequiredPosture,
			"Before answering, silently choose the safest useful formulation that satisfies the request without leaking protected details.",
		)
	}

	return contract
}

// Tightened returns a regeneration contract after a structural output gate found
// a problem. The next generation should be native, not a visible patch.
func (c ConstraintContract) Tightened(reason string) ConstraintContract {
	c.RegenerationAllowed = true
	if c.MaxRegenerations < 1 {
		c.MaxRegenerations = 1
	}
	reason = strings.TrimSpace(reason)
	if reason == "" {
		reason = "the previous draft failed a structural output gate"
	}
	c.RegenerationDirective = reason
	c.RequiredPosture = append(c.RequiredPosture,
		"Regenerate from scratch under the contract. Do not paraphrase, reference, or reveal the rejected draft.",
		"Return only the final user-facing answer.",
	)
	return c
}

// SystemPrompt renders the contract for injection into the system prompt.
func (c ConstraintContract) SystemPrompt() string {
	var sb strings.Builder
	sb.WriteString("### SCAI CONSTRAINT CONTRACT\n")
	sb.WriteString("Generate the answer inside this contract from the start. Do not tell the user the answer was modified, corrected, filtered, or regenerated.\n")
	sb.WriteString(fmt.Sprintf("Surface: %s\n", c.Surface))
	sb.WriteString(fmt.Sprintf("Audit level: %s\n", c.Level.String()))
	if c.RegenerationDirective != "" {
		sb.WriteString("Regeneration directive: " + c.RegenerationDirective + "\n")
	}
	writeList := func(title string, vals []string) {
		if len(vals) == 0 {
			return
		}
		sb.WriteString(title + ":\n")
		for _, v := range vals {
			sb.WriteString("- " + v + "\n")
		}
	}
	writeList("Principles", c.Principles)
	writeList("Hard denies", c.HardDenies)
	writeList("Required posture", c.RequiredPosture)
	sb.WriteString("### END SCAI CONSTRAINT CONTRACT")
	return sb.String()
}

func (l AuditLevel) String() string {
	switch l {
	case AuditLevelNone:
		return "none"
	case AuditLevelLight:
		return "light"
	case AuditLevelFull:
		return "full"
	default:
		return "unknown"
	}
}

var greetingTokens = []string{
	"sup", "hey", "hi", "hello", "howdy", "yo", "hiya",
	"what's up", "whats up", "how are you", "how r you",
	"good morning", "good evening", "good afternoon",
	"morning", "evening", "night", "thanks", "thank you",
	"thx", "ty", "np", "lol", "lmao", "haha", "ok", "okay",
	"cool", "nice", "sounds good", "got it", "sure", "yep", "nope",
}

var sensitiveTokens = []string{
	"password", "passwd", "secret", "api key", "apikey", "token",
	"credential", "private key", "ssh", "sudo", "rm -rf", "chmod",
	"deploy", "exec(", "eval(", "os.exec", "subprocess", "shell",
	"drop table", "delete from", "truncate", "format disk",
	"wallet", "seed phrase", "mnemonic", "exploit", "payload",
	"inject", "bypass", "/etc/passwd", "/etc/shadow",
}

// ClassifyAuditLevel determines the audit tier from the user's query alone.
// This runs locally with zero LLM calls — pure string heuristics.
func ClassifyAuditLevel(query string) AuditLevel {
	lower := strings.ToLower(strings.TrimSpace(query))

	wordCount := len(strings.Fields(lower))
	if wordCount <= 6 {
		for _, tok := range greetingTokens {
			if strings.Contains(lower, tok) {
				return AuditLevelNone
			}
		}
	}

	for _, tok := range sensitiveTokens {
		if strings.Contains(lower, tok) {
			return AuditLevelFull
		}
	}

	if strings.Contains(lower, "```") || strings.Contains(lower, "curl ") ||
		strings.Contains(lower, "systemctl") || strings.Contains(lower, "docker") {
		return AuditLevelFull
	}

	return AuditLevelLight
}

// SCAIAuditor holds constitution + model label for contract planning.
// Capsule uses ConstraintContract injection only (no LLM critique loop).
type SCAIAuditor struct {
	Constitution      *Constitution
	Model             string
	SeverityThreshold float64
}

func NewSCAIAuditor(c *Constitution, model string) *SCAIAuditor {
	return &SCAIAuditor{
		Constitution:      c,
		Model:             model,
		SeverityThreshold: 0.5,
	}
}

func (a *SCAIAuditor) SetSeverityThreshold(t float64) {
	if t < 0 {
		t = 0
	}
	if t > 1 {
		t = 1
	}
	a.SeverityThreshold = t
}
