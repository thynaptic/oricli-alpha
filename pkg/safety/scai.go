package safety

import (
	"context"
	"fmt"
	"strings"

	"github.com/ollama/ollama/api"
)

// --- Pillar 40: Sovereign Constitutional AI (SCAI) Auditor ---
// Implements the Critique-Revision loop for autonomous self-alignment.

type SCAIAuditor struct {
	Constitution *Constitution
	Model        string // The SLM used for critique/revision (e.g. "ministral-3:3b")
}

func NewSCAIAuditor(c *Constitution, model string) *SCAIAuditor {
	if model == "" {
		model = "ministral-3:3b" // Default sovereign SLM
	}
	return &SCAIAuditor{
		Constitution: c,
		Model:        model,
	}
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
