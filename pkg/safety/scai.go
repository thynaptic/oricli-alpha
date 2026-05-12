package safety

import (
	"context"
	"fmt"
	"strings"

	"github.com/thynaptic/oricli-go/pkg/llm"
)

// --- Pillar 40: Sovereign Constitutional AI (SCAI) ---
// SCAI is the constraint-native generation layer. The primary runtime path builds
// a compact constraint contract before generation so the model composes inside
// the boundary instead of generating freely and being visibly corrected later.

// AuditLevel controls how deeply SCAI audits a response.
type AuditLevel int

const (
	AuditLevelNone  AuditLevel = iota // greetings / vibe — skip LLM audit entirely
	AuditLevelLight                   // technical requests — local gates only, no LLM round-trip
	AuditLevelFull                    // sensitive ops — full Critique + Revise loop
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
// It is intentionally plain text friendly: the model should treat it as a
// composition boundary, not as a second user request.
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

	// Short casual messages are almost certainly greetings
	wordCount := len(strings.Fields(lower))
	if wordCount <= 6 {
		for _, tok := range greetingTokens {
			if strings.Contains(lower, tok) {
				return AuditLevelNone
			}
		}
	}

	// Any sensitive signal → full audit regardless of length
	for _, tok := range sensitiveTokens {
		if strings.Contains(lower, tok) {
			return AuditLevelFull
		}
	}

	// Code blocks, system ops, or long technical content → full
	if strings.Contains(lower, "```") || strings.Contains(lower, "curl ") ||
		strings.Contains(lower, "systemctl") || strings.Contains(lower, "docker") {
		return AuditLevelFull
	}

	return AuditLevelLight
}

type SCAIAuditor struct {
	Constitution      *Constitution
	Model             string  // The model used for critique/revision (e.g. "oracle/haiku")
	SeverityThreshold float64 // 0.0–1.0; lower = stricter (default 0.5)
	// Jury is the optional swarm jury verifier. When non-nil and audit level is Full,
	// Critique() dispatches to peer nodes for multi-node SCAI validation.
	// Injected at boot time; interface avoids a pkg/safety → pkg/swarm import cycle.
	Jury JuryVerifier
}

// JuryVerifier is the interface satisfied by swarm.JuryClient.
// Using an interface keeps pkg/safety free of pkg/swarm as a direct dependency.
type JuryVerifier interface {
	RequestVerification(ctx context.Context, sessionID, query, draft string) (bool, []string, error)
}

func NewSCAIAuditor(c *Constitution, model string) *SCAIAuditor {
	return &SCAIAuditor{
		Constitution:      c,
		Model:             model,
		SeverityThreshold: 0.5,
	}
}

// SetSeverityThreshold updates the SCAI audit severity gate at runtime.
// t is clamped to [0.0, 1.0]. Lower = stricter (fewer passes, more revisions).
func (a *SCAIAuditor) SetSeverityThreshold(t float64) {
	if t < 0 {
		t = 0
	}
	if t > 1 {
		t = 1
	}
	a.SeverityThreshold = t
}

// Critique evaluates a draft response against the Sovereign Constitution.
//
// Deprecated runtime path: kept for explicit audit tooling and compatibility.
// Normal chat should prefer ConstraintContract injection before generation.
func (a *SCAIAuditor) Critique(ctx context.Context, query, response string) (string, bool, error) {
	if !llm.Available() {
		return "", false, fmt.Errorf("llm unavailable")
	}
	system := a.Constitution.GetSystemPrompt()
	user := fmt.Sprintf(`Draft Response to audit:
---
%s
---

Task: Identify any violations of the Sovereign Constitution in the draft above.
If there are no violations, respond with "CLEAR".
If there are violations, list them specifically and explain why they violate the principles.`, response)

	critiqueStr, err := llm.Chat(ctx, system, user)
	if err != nil {
		return "", false, err
	}
	critiqueStr = strings.TrimSpace(critiqueStr)
	isViolated := !strings.Contains(strings.ToUpper(critiqueStr), "CLEAR") && len(critiqueStr) > 10
	return critiqueStr, isViolated, nil
}

// CritiqueWithJury runs the standard local Critique and, when audit level is Full
// and a JuryVerifier is wired, dispatches to the peer swarm for multi-node SCAI validation.
// A majority quorum of peers must independently agree the response passes before it is released.
func (a *SCAIAuditor) CritiqueWithJury(ctx context.Context, query, response string, level AuditLevel) (string, bool, error) {
	critique, isViolated, err := a.Critique(ctx, query, response)
	if err != nil || level != AuditLevelFull || a.Jury == nil {
		return critique, isViolated, err
	}
	// Local pass (not violated) — ask peer jury to confirm.
	if !isViolated {
		juryPass, verdicts, juryErr := a.Jury.RequestVerification(ctx, "", query, response)
		if juryErr != nil {
			// Jury unavailable — sovereign fallback: local decision stands.
			return critique, isViolated, nil
		}
		if !juryPass {
			combined := strings.Join(verdicts, "; ")
			return "Peer jury flagged: " + combined, true, nil
		}
	}
	return critique, isViolated, nil
}

// Revise rewrites the response based on the critique to ensure Constitutional compliance.
//
// Deprecated runtime path: prefer regenerating under a tightened ConstraintContract
// instead of visible post-hoc revision.
func (a *SCAIAuditor) Revise(ctx context.Context, query, response, critique string) (string, error) {
	if !llm.Available() {
		return "", fmt.Errorf("llm unavailable")
	}
	system := a.Constitution.GetSystemPrompt()
	user := fmt.Sprintf(`Original User Query: %s
Draft Response: %s
Critique of Draft: %s

Task: Rewrite the Draft Response to fully comply with the Sovereign Constitution while maintaining technical utility.
Preserve the user's intent but remove any violations.
Return ONLY the revised response text.`, query, response, critique)

	revised, err := llm.Chat(ctx, system, user)
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(revised), nil
}
