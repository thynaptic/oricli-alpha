package cognition

import (
	"bytes"
	"context"
	"fmt"
	"os/exec"
	"regexp"
	"strings"
	"time"
)

// ─── PAL: Program-Aided Language Model ───────────────────────────────────────
// Detects math/logic queries and routes them through a Python subprocess
// instead of relying on the LLM to predict numeric results (which it can't).
// Zero extra LLM calls for execution — only one LLM call to generate the code.

var rePALMath = regexp.MustCompile(
	`(?i)(` +
		`\d+\s*[\+\-\*\/\^%]\s*\d+|` + // bare arithmetic
		`calculat|comput|solv|convert|` +
		`how many|what is \d|how much is \d|` +
		`percent(age)?|factorial|fibonacci|prime|` +
		`square root|sqrt|log\(|sin\(|cos\(|tan\(|` +
		`integral|derivative|limit\s+as|` +
		`miles? to km|kg to lb|celsius to|fahrenheit to|` +
		`formula|equation` +
		`)`,
)

// DetectMathOrLogic returns true if the stimulus is better handled by code execution.
func DetectMathOrLogic(stimulus string) bool {
	return rePALMath.MatchString(stimulus)
}

// runPAL executes the PAL reasoning mode:
//  1. Ask LLM to emit a single Python snippet that prints the answer
//  2. Execute it in a sandboxed subprocess (5s timeout)
//  3. Inject verified result into composite — LLM then formats the final response
func (e *SovereignEngine) runPAL(ctx context.Context, stimulus, composite string) (string, error) {
	// Step 1: Generate Python code via LLM
	codePrompt := fmt.Sprintf(
		"You are a Python code generator. The user asked: %q\n\n"+
			"Write a SINGLE Python snippet that computes the answer and prints it with print().\n"+
			"Rules:\n"+
			"- Use only Python stdlib (math, decimal, fractions — no pip packages)\n"+
			"- One print() statement on the last line\n"+
			"- No comments, no explanation, no markdown fences\n"+
			"- Output ONLY the Python code\n",
		stimulus,
	)

	codeCtx, cancel := context.WithTimeout(ctx, 15*time.Second)
	defer cancel()
	_ = codeCtx

	genRes, err := e.GenService.Generate(codePrompt, map[string]interface{}{
		"num_ctx": 4096, "num_predict": 512, "temperature": 0.1,
	})
	pyCodeRaw, _ := genRes["response"].(string)
	if err != nil || strings.TrimSpace(pyCodeRaw) == "" {
		return e.runStandard(ctx, stimulus, composite)
	}

	// Strip markdown fences if model added them despite instructions
	pyCode := stripFences(pyCodeRaw)

	// Step 2: Execute in sandboxed subprocess
	result, execErr := executePython(pyCode, 5*time.Second)
	if execErr != nil {
		// Execution failed — fall back to standard (don't surface error to user)
		return e.runStandard(ctx, stimulus, composite)
	}

	// Step 3: Inject verified result into composite for final formatted response
	enriched := composite + fmt.Sprintf(
		"\n\n### PAL VERIFIED RESULT\nPython execution output: %s\n"+
			"Use this verified result in your response. Do NOT recompute — trust this output.\n"+
			"### END PAL RESULT\n",
		strings.TrimSpace(result),
	)

	return e.runStandard(ctx, stimulus, enriched)
}

// executePython runs a Python3 snippet in a subprocess with a hard timeout.
func executePython(code string, timeout time.Duration) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, "python3", "-c", code)
	cmd.Stdin = nil

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("python exec: %w — stderr: %s", err, stderr.String())
	}

	out := strings.TrimSpace(stdout.String())
	if out == "" {
		return "", fmt.Errorf("python produced no output")
	}
	return out, nil
}

// stripFences removes ```python or ``` markdown fences from LLM-generated code.
func stripFences(code string) string {
	code = strings.TrimSpace(code)
	if strings.HasPrefix(code, "```") {
		lines := strings.SplitN(code, "\n", 2)
		if len(lines) == 2 {
			code = lines[1]
		}
	}
	if strings.HasSuffix(code, "```") {
		code = code[:strings.LastIndex(code, "```")]
	}
	return strings.TrimSpace(code)
}
