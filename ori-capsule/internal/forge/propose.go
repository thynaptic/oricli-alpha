package forge

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/thynaptic/ori-capsule/internal/byok"
)

// ProposeRequest asks BYOK to generate a Yaegi/script tool (one LLM call).
type ProposeRequest struct {
	Task         string `json:"task"`
	Model        string `json:"model,omitempty"`
	Name         string `json:"name,omitempty"`
	Kind         string `json:"kind,omitempty"` // yaegi (default) | script
	Register     bool   `json:"register"`
	ExpectedHint string `json:"expected_hint,omitempty"`
}

// ProposeResult is the verified (and optionally registered) tool.
type ProposeResult struct {
	Tool   JITTool      `json:"tool"`
	Verify VerifyResult `json:"verify"`
	Raw    string       `json:"raw_excerpt,omitempty"`
	Stored bool         `json:"stored"`
}

// Propose uses a single BYOK chat completion to generate a tool, then VerifyStatic.
func Propose(ctx context.Context, cred byok.Credentials, model string, req ProposeRequest, lib *MemoryLibrary) (ProposeResult, error) {
	task := strings.TrimSpace(req.Task)
	if task == "" {
		return ProposeResult{}, fmt.Errorf("task required")
	}
	kind := strings.ToLower(strings.TrimSpace(req.Kind))
	if kind == "" {
		kind = "yaegi"
	}
	if kind != "yaegi" && kind != "script" {
		return ProposeResult{}, fmt.Errorf("kind must be yaegi or script")
	}
	if model == "" {
		return ProposeResult{}, fmt.Errorf("model required")
	}

	prompt := buildProposePrompt(task, req.Name, kind, req.ExpectedHint)
	chatReq := byok.ChatRequest{
		Model: model,
		Messages: []byok.Message{
			{Role: "system", Content: "You generate sandboxed capsule tools. Respond with JSON only."},
			{Role: "user", Content: prompt},
		},
	}
	out, err := byok.ChatNonStream(ctx, cred, chatReq)
	if err != nil {
		return ProposeResult{}, err
	}
	raw := ""
	if len(out.Choices) > 0 {
		raw = out.Choices[0].Message.Content
	}
	parsed, err := parseProposedJSON(raw)
	if err != nil {
		return ProposeResult{Raw: truncate(raw, 400)}, fmt.Errorf("parse proposal: %w", err)
	}
	if req.Name != "" {
		parsed.Name = req.Name
	}
	parsed.Kind = kind
	parsed.ModelUsed = model

	vr := VerifyStatic(VerifyRequest{
		Script: pick(kind == "script", parsed.Source, ""),
		Source: pick(kind == "yaegi", parsed.Source, ""),
	})
	res := ProposeResult{Tool: parsed, Verify: vr, Raw: truncate(raw, 200)}
	if !vr.OK {
		return res, fmt.Errorf("constitution: %s", vr.Summary)
	}
	if req.Register {
		if lib == nil {
			return res, fmt.Errorf("library unavailable")
		}
		stored, err := lib.Put(parsed)
		if err != nil {
			return res, err
		}
		res.Tool = stored
		res.Stored = true
	}
	return res, nil
}

func buildProposePrompt(task, name, kind, hint string) string {
	var b strings.Builder
	b.WriteString("Generate a docker-friendly capsule tool.\n")
	b.WriteString("TASK: " + task + "\n")
	if name != "" {
		b.WriteString("NAME: " + name + "\n")
	}
	if hint != "" {
		b.WriteString("HINT: " + hint + "\n")
	}
	b.WriteString("KIND: " + kind + "\n\n")
	if kind == "yaegi" {
		b.WriteString(`Yaegi Go tool contract:
- package main
- Export a function: func ToolName(args []string) (stdout string, stderr string, error)
- No os/exec, net/http, syscall, unsafe
- No TODO/FIXME/stubs
- Pure computation / string processing only
`)
	} else {
		b.WriteString(`Script contract (GOSH allowlisted builtins only: cat ls mkdir rm pwd echo):
- Read params somehow ($1 or files)
- Prefer JSON-ish stdout
- No curl/wget/bash/python/sudo/rm -rf
`)
	}
	b.WriteString(`
Respond with JSON only:
{
  "name": "snake_case_name",
  "description": "one sentence",
  "parameters": {"type":"object","properties":{"input":{"type":"string"}},"required":["input"]},
  "source": "full source with \\n newlines"
}
`)
	return b.String()
}

func parseProposedJSON(raw string) (JITTool, error) {
	start := strings.Index(raw, "{")
	end := strings.LastIndex(raw, "}")
	if start < 0 || end <= start {
		return JITTool{}, fmt.Errorf("no JSON object in model response")
	}
	var blob struct {
		Name        string         `json:"name"`
		Description string         `json:"description"`
		Source      string         `json:"source"`
		Parameters  map[string]any `json:"parameters"`
	}
	if err := json.Unmarshal([]byte(raw[start:end+1]), &blob); err != nil {
		return JITTool{}, err
	}
	if strings.TrimSpace(blob.Source) == "" {
		return JITTool{}, fmt.Errorf("empty source")
	}
	return JITTool{
		Name:        blob.Name,
		Description: blob.Description,
		Source:      blob.Source,
		Parameters:  blob.Parameters,
		CreatedAt:   time.Now().UTC(),
	}, nil
}

func truncate(s string, n int) string {
	s = strings.TrimSpace(s)
	if len(s) <= n {
		return s
	}
	return s[:n-1] + "…"
}
