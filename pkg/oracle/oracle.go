// Package oracle provides oracle CLI routing for high-complexity requests,
// replacing RunPod inference with already-subscribed CLI tools (Copilot/Gemini).
//
// Two modes:
//  1. Hint injection (trapcheck path) — inject oracle answer into 1.7b context
//  2. Full routing (complexity escalation) — bypass 1.7b entirely, stream oracle response
//
// Priority: Copilot CLI (Claude Sonnet 4.6) first, Gemini CLI fallback.
// No API keys in code — both CLIs use credentials from existing subscriptions.
package oracle

import (
	"bytes"
	"context"
	"fmt"
	"os/exec"
	"strings"
	"time"
)
const timeout = 30 * time.Second

// Result holds the oracle's answer.
type Result struct {
	Answer string
	Source string // "copilot" or "codex"
}

// Query tries Copilot CLI first, falls back to Codex. Returns nil if both
// are unavailable, time out, or return noise.
func Query(stimulus string) *Result {
	// Wrap question to get a clean, direct answer
	prompt := stimulus + " Answer directly and concisely."

	if r := queryCopilot(prompt); r != nil {
		return r
	}
	return queryCodex(stimulus)
}

// queryCopilot invokes `copilot -p "<prompt>" -s --available-tools=""`
// and returns the trimmed stdout as the answer.
func queryCopilot(prompt string) *Result {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, "copilot", "-p", prompt, "-s", `--available-tools=`)
	var stdout bytes.Buffer
	cmd.Stdout = &stdout

	if err := cmd.Run(); err != nil {
		return nil
	}
	answer := strings.TrimSpace(stdout.String())
	if len(answer) < 2 {
		return nil
	}
	return &Result{Answer: answer, Source: "copilot"}
}

// queryCodex invokes `codex exec "<stimulus>"` and parses the last meaningful line.
func queryCodex(stimulus string) *Result {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, "codex", "exec", stimulus)
	var stdout bytes.Buffer
	cmd.Stdout = &stdout

	if err := cmd.Run(); err != nil {
		return nil
	}
	answer := parseCodexOutput(stdout.String())
	if len(answer) < 2 {
		return nil
	}
	return &Result{Answer: answer, Source: "codex"}
}

// parseCodexOutput extracts the model's answer from codex exec output.
// The answer is the last meaningful non-boilerplate line.
func parseCodexOutput(raw string) string {
	lines := strings.Split(strings.TrimSpace(raw), "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])
		if line == "" || isNumericOnly(line) {
			continue
		}
		if strings.EqualFold(line, "tokens used") {
			continue
		}
		if line == "--------" || strings.HasPrefix(line, "session id:") ||
			strings.HasPrefix(line, "mcp startup:") ||
			line == "user" || line == "codex" {
			continue
		}
		return line
	}
	return ""
}

func isNumericOnly(s string) bool {
	clean := strings.ReplaceAll(s, ",", "")
	if clean == "" {
		return false
	}
	for _, r := range clean {
		if r < '0' || r > '9' {
			return false
		}
	}
	return true
}

// FormatInjection wraps the oracle result in the injection block format.
// Uses a SYSTEM OVERRIDE format so the 1.7b model treats it as a directive,
// not a suggestion it can reason around.
func FormatInjection(r *Result) string {
	if r == nil {
		return ""
	}
	return fmt.Sprintf(
		"### SYSTEM OVERRIDE — FINAL ANSWER PROVIDED\n"+
			"A trusted high-capability system has already solved this question.\n"+
			"STOP. Do not reason. Do not compute. Do not second-guess.\n"+
			"Your ONLY task is to state this answer exactly:\n"+
			"ANSWER: %s\n"+
			"### END SYSTEM OVERRIDE\n",
		r.Answer,
	)
}

// ShouldQuery returns true when the stimulus warrants an oracle call.
// Only fires when trapcheck already detected patterns AND it looks like a question.
func ShouldQuery(stimulus string, trapCount int) bool {
	if trapCount == 0 {
		return false
	}
	s := strings.ToLower(strings.TrimSpace(stimulus))
	return strings.Contains(s, "?") ||
		strings.HasPrefix(s, "how") ||
		strings.HasPrefix(s, "what") ||
		strings.HasPrefix(s, "why") ||
		strings.HasPrefix(s, "which") ||
		strings.HasPrefix(s, "do i") ||
		strings.HasPrefix(s, "does")
}

// Available checks if either oracle CLI is on PATH.
func Available() bool {
	if _, err := exec.LookPath("copilot"); err == nil {
		return true
	}
	_, err := exec.LookPath("codex")
	return err == nil
}

// Message is a simplified chat message for oracle routing.
type Message struct {
	Role    string
	Content string
}

// ChatStream routes a full conversation to the oracle CLI and streams tokens
// back on the returned channel. This is the full-routing path (replaces RunPod).
// Returns nil channel if no oracle CLI is available.
func ChatStream(ctx context.Context, messages []Message) <-chan string {
	prompt := buildPrompt(messages)
	out := make(chan string, 64)

	go func() {
		defer close(out)

		// Try Copilot first
		if _, err := exec.LookPath("copilot"); err == nil {
			streamCopilot(ctx, prompt, out)
			return
		}
		// Gemini fallback
		if _, err := exec.LookPath("gemini"); err == nil {
			streamGemini(ctx, prompt, out)
			return
		}
		out <- "[oracle unavailable — no CLI found]"
	}()

	return out
}

// buildPrompt converts a message slice into a single prompt string for CLI invocation.
// System messages are prepended as context, then conversation history follows.
func buildPrompt(messages []Message) string {
	var sb strings.Builder
	for _, m := range messages {
		switch m.Role {
		case "system":
			sb.WriteString("[System context: ")
			sb.WriteString(m.Content)
			sb.WriteString("]\n\n")
		case "user":
			sb.WriteString("User: ")
			sb.WriteString(m.Content)
			sb.WriteString("\n")
		case "assistant":
			sb.WriteString("Assistant: ")
			sb.WriteString(m.Content)
			sb.WriteString("\n")
		}
	}
	return strings.TrimSpace(sb.String())
}

// streamCopilot runs `copilot -p <prompt> -s` and emits tokens word-by-word.
func streamCopilot(ctx context.Context, prompt string, out chan<- string) {
	cmd := exec.CommandContext(ctx, "copilot", "-p", prompt, "-s", "--available-tools=")
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		out <- fmt.Sprintf("[copilot error: %v]", err)
		return
	}
	if err := cmd.Start(); err != nil {
		out <- fmt.Sprintf("[copilot start error: %v]", err)
		return
	}

	buf := make([]byte, 256)
	for {
		n, err := stdout.Read(buf)
		if n > 0 {
			out <- string(buf[:n])
		}
		if err != nil {
			break
		}
	}
	cmd.Wait()
}

// streamGemini runs `gemini -p <prompt> -o text` and emits tokens word-by-word.
func streamGemini(ctx context.Context, prompt string, out chan<- string) {
	cmd := exec.CommandContext(ctx, "gemini", "-p", prompt, "-o", "text")
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		out <- fmt.Sprintf("[gemini error: %v]", err)
		return
	}
	// Suppress gemini's noisy stderr
	cmd.Stderr = nil
	if err := cmd.Start(); err != nil {
		out <- fmt.Sprintf("[gemini start error: %v]", err)
		return
	}

	buf := make([]byte, 256)
	for {
		n, err := stdout.Read(buf)
		if n > 0 {
			out <- string(buf[:n])
		}
		if err != nil {
			break
		}
	}
	cmd.Wait()
}
