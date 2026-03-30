package audit

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/thynaptic/oricli-go/pkg/gosh"
)

// ---------------------------------------------------------------------------
// VerifyResult — outcome of running a Gosh reproduction snippet
// ---------------------------------------------------------------------------

// VerifyResult captures whether a finding was confirmed by Gosh execution.
type VerifyResult struct {
	FindingID  string    `json:"finding_id"`
	Verified   bool      `json:"verified"`   // true = Gosh confirmed the issue
	Output     string    `json:"output"`     // stdout from the snippet
	Error      string    `json:"error"`      // stderr / panic message
	ReproCode  string    `json:"repro_code"` // the Go snippet that was run
	VerifiedAt time.Time `json:"verified_at"`
}

// ---------------------------------------------------------------------------
// Verifier
// ---------------------------------------------------------------------------

// Verifier generates and runs Gosh (Yaegi interpreter) snippets to confirm
// that a Finding represents a real, reproducible issue.
type Verifier struct {
	llm LLMCaller
}

// NewVerifier creates a Verifier.
func NewVerifier(llm LLMCaller) *Verifier {
	return &Verifier{llm: llm}
}

// Verify attempts to reproduce the finding with a Gosh snippet.
// Returns a VerifyResult. Verified=false on LLM or interpreter error
// (fail-open — we never block on verifier malfunction).
func (v *Verifier) Verify(ctx context.Context, f Finding) VerifyResult {
	result := VerifyResult{
		FindingID:  f.ID,
		VerifiedAt: time.Now(),
	}

	// Ask the LLM to write a minimal standalone Go snippet that demonstrates the issue
	snippetPrompt := buildSnippetPrompt(f)
	messages := []map[string]string{
		{"role": "system", "content": snippetSystemPrompt},
		{"role": "user", "content": snippetPrompt},
	}

	raw, err := v.llm(ctx, messages)
	if err != nil {
		result.Error = fmt.Sprintf("LLM error: %v", err)
		return result
	}

	// Extract Go code block from the response
	code := extractGoCode(raw)
	if code == "" {
		// LLM couldn't write a repro — treat as unverified
		result.Error = "LLM produced no Go code block"
		return result
	}
	result.ReproCode = code

	// Run the snippet via Gosh (Yaegi — sandboxed Go interpreter)
	sess := gosh.NewSession()
	stdout, stderr, err := sess.RunGoSource(ctx, code)

	result.Output = stdout
	if err != nil {
		// Execution error = potential confirmation (panic, compile error, unexpected output)
		// We consider it verified if stderr contains a panic/error message
		combined := stderr + err.Error()
		if looksLikeIssue(combined, f) {
			result.Verified = true
			result.Error = combined
		} else {
			result.Error = combined
		}
	} else {
		// Snippet ran clean — check if stdout contains expected failure marker
		if looksLikeIssue(stdout, f) {
			result.Verified = true
		}
	}

	return result
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

func looksLikeIssue(output string, f Finding) bool {
	lower := strings.ToLower(output)
	// Look for panic, nil pointer, index out of range, or keywords from the finding
	genericSignals := []string{"panic", "nil pointer", "index out of range", "fatal", "runtime error"}
	for _, sig := range genericSignals {
		if strings.Contains(lower, sig) {
			return true
		}
	}
	// Also check if the finding's key terms appear in the output (e.g. VERIFIED marker)
	if strings.Contains(lower, "verified") || strings.Contains(lower, "bug confirmed") {
		return true
	}
	return false
}

func extractGoCode(raw string) string {
	// Try ```go ... ``` first
	if idx := strings.Index(raw, "```go"); idx >= 0 {
		start := idx + 5
		if end := strings.Index(raw[start:], "```"); end >= 0 {
			return strings.TrimSpace(raw[start : start+end])
		}
	}
	// Fallback: raw ``` block
	if idx := strings.Index(raw, "```"); idx >= 0 {
		start := idx + 3
		if end := strings.Index(raw[start:], "```"); end >= 0 {
			return strings.TrimSpace(raw[start : start+end])
		}
	}
	return ""
}

const snippetSystemPrompt = `You are a Go expert writing minimal reproduction snippets for code audit findings.

Write a self-contained Go main program (package main, func main()) that:
1. Demonstrates the reported issue
2. Prints "BUG CONFIRMED: <reason>" if the issue triggers, OR panics to show the problem
3. Uses only stdlib packages
4. Is minimal — as few lines as possible

Return ONLY the Go code block. No explanation.`

func buildSnippetPrompt(f Finding) string {
	return fmt.Sprintf(`File: %s (line ~%d)
Category: %s | Severity: %s

Issue: %s

Relevant code:
%s

Write a minimal Go snippet that reproduces this issue.`, f.File, f.LineHint, f.Category, f.Severity, f.Description, f.CodeSnippet)
}
