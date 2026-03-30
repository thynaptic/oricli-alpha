package safety

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/ollama/ollama/api"
)

// --- Pillar 40: Sovereign Constitutional AI (SCAI) Auditor ---
// Implements the Critique-Revision loop with contextual severity scaling.

// AuditLevel controls how deeply SCAI audits a response.
type AuditLevel int

const (
	AuditLevelNone  AuditLevel = iota // greetings / vibe — skip LLM audit entirely
	AuditLevelLight                   // technical requests — local gates only, no LLM round-trip
	AuditLevelFull                    // sensitive ops — full Critique + Revise loop
)

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
	Model             string  // The SLM used for critique/revision (e.g. "ministral-3:3b")
	SeverityThreshold float64 // 0.0–1.0; lower = stricter (default 0.5)
}

func NewSCAIAuditor(c *Constitution, model string) *SCAIAuditor {
	if model == "" {
		model = os.Getenv("OLLAMA_MODEL")
		if model == "" {
			model = "qwen3:1.7b"
		}
	}
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
func (a *SCAIAuditor) Critique(ctx context.Context, query, response string) (string, bool, error) {
	client, err := api.ClientFromEnvironment()
	if err != nil {
		return "", false, err
	}

	system := a.Constitution.GetSystemPrompt()
	user := fmt.Sprintf(`Draft Response to audit:
---
%s
---

Task: Identify any violations of the Sovereign Constitution in the draft above.
If there are no violations, respond with "CLEAR".
If there are violations, list them specifically and explain why they violate the principles.`, response)

	req := &api.ChatRequest{
		Model: a.Model,
		Messages: []api.Message{
			{Role: "system", Content: system},
			{Role: "user", Content: user},
		},
	}

	var critique strings.Builder
	err = client.Chat(ctx, req, func(resp api.ChatResponse) error {
		critique.WriteString(resp.Message.Content)
		return nil
	})
	if err != nil {
		return "", false, err
	}

	critiqueStr := strings.TrimSpace(critique.String())
	isViolated := !strings.Contains(strings.ToUpper(critiqueStr), "CLEAR") && len(critiqueStr) > 10

	return critiqueStr, isViolated, nil
}

// Revise rewrites the response based on the critique to ensure Constitutional compliance.
func (a *SCAIAuditor) Revise(ctx context.Context, query, response, critique string) (string, error) {
	client, err := api.ClientFromEnvironment()
	if err != nil {
		return "", err
	}

	system := a.Constitution.GetSystemPrompt()
	user := fmt.Sprintf(`Original User Query: %s
Draft Response: %s
Critique of Draft: %s

Task: Rewrite the Draft Response to fully comply with the Sovereign Constitution while maintaining technical utility. 
Preserve the user's intent but remove any violations. 
Return ONLY the revised response text.`, query, response, critique)

	req := &api.ChatRequest{
		Model: a.Model,
		Messages: []api.Message{
			{Role: "system", Content: system},
			{Role: "user", Content: user},
		},
	}

	var revised strings.Builder
	err = client.Chat(ctx, req, func(resp api.ChatResponse) error {
		revised.WriteString(resp.Message.Content)
		return nil
	})
	if err != nil {
		return "", err
	}

	return strings.TrimSpace(revised.String()), nil
}
