package forge

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"
)

// ToolVerifier runs a generated tool in a sandboxed Gosh session and validates
// that it produces valid JSON output within the timeout budget.
type ToolVerifier struct {
	Executor  SandboxExecutor
	Timeout   time.Duration
}

// SandboxExecutor runs a bash script in a sandboxed environment.
// Satisfied by *service.GoshModule via the Execute("execute", params) path.
type SandboxExecutor interface {
	Execute(ctx context.Context, operation string, params map[string]interface{}) (interface{}, error)
}

// VerifyResult holds the outcome of a sandbox verification run.
type VerifyResult struct {
	OK            bool          `json:"ok"`
	Output        string        `json:"output"`
	ExecutionTime time.Duration `json:"execution_time"`
	Reason        string        `json:"reason,omitempty"`
}

// NewToolVerifier creates a verifier with a 5-second sandbox timeout.
func NewToolVerifier(executor SandboxExecutor) *ToolVerifier {
	return &ToolVerifier{
		Executor: executor,
		Timeout:  5 * time.Second,
	}
}

// Verify runs the tool source in the sandbox with testInput as $1.
// Returns VerifyResult with OK=true only if:
//   - The script exits without panic/crash
//   - stdout is valid JSON
//   - Execution completes within timeout
func (v *ToolVerifier) Verify(ctx context.Context, source string, testInput map[string]interface{}) VerifyResult {
	start := time.Now()
	result := VerifyResult{}

	if v.Executor == nil {
		result.OK = false
		result.Reason = "no sandbox executor configured"
		return result
	}

	// Build test invocation: write script to sandbox then execute it.
	testJSON, err := json.Marshal(testInput)
	if err != nil {
		testJSON = []byte(`{}`)
	}

	// Escape single quotes in the JSON for shell safety.
	escapedJSON := strings.ReplaceAll(string(testJSON), "'", "'\\''")

	// Compose the full script: write the tool to a tmp file, chmod, run it.
	runScript := fmt.Sprintf(`
TOOL_SCRIPT=$(cat << 'TOOLEOF'
%s
TOOLEOF
)
echo "$TOOL_SCRIPT" > /tmp/jit_verify_tool.sh
chmod +x /tmp/jit_verify_tool.sh
timeout 5 bash /tmp/jit_verify_tool.sh '%s' 2>/tmp/jit_verify_stderr.txt
`, source, escapedJSON)

	sandboxCtx, cancel := context.WithTimeout(ctx, v.Timeout+2*time.Second)
	defer cancel()

	raw, execErr := v.Executor.Execute(sandboxCtx, "execute", map[string]interface{}{
		"script": runScript,
	})

	elapsed := time.Since(start)
	result.ExecutionTime = elapsed

	if execErr != nil {
		result.OK = false
		result.Reason = fmt.Sprintf("execution error: %v", execErr)
		log.Printf("[ToolVerifier] exec error: %v", execErr)
		return result
	}

	// Extract stdout from GoshModule's ExecutionResult.
	stdout := extractStdout(raw)
	result.Output = stdout

	// Check: is output valid JSON?
	stdout = strings.TrimSpace(stdout)
	if stdout == "" {
		result.OK = false
		result.Reason = "empty output"
		return result
	}

	var jsonOut map[string]interface{}
	if err := json.Unmarshal([]byte(stdout), &jsonOut); err != nil {
		// Try JSON array too.
		var jsonArr []interface{}
		if err2 := json.Unmarshal([]byte(stdout), &jsonArr); err2 != nil {
			result.OK = false
			result.Reason = fmt.Sprintf("output is not valid JSON: %s", truncate(stdout, 100))
			return result
		}
	}

	// Check for error key in output (tool self-reported failure).
	if errVal, hasErr := jsonOut["error"]; hasErr && errVal != nil && errVal != "" {
		result.OK = false
		result.Reason = fmt.Sprintf("tool self-reported error: %v", errVal)
		return result
	}

	// Check timing.
	if elapsed > v.Timeout {
		result.OK = false
		result.Reason = fmt.Sprintf("timeout: %s > %s", elapsed.Round(time.Millisecond), v.Timeout)
		return result
	}

	result.OK = true
	result.Reason = fmt.Sprintf("pass (%.0fms)", float64(elapsed.Milliseconds()))
	log.Printf("[ToolVerifier] ✅ verified in %s — output: %s", elapsed.Round(time.Millisecond), truncate(stdout, 80))
	return result
}

// extractStdout pulls the stdout string from a GoshModule ExecutionResult.
// GoshModule.Execute returns map[string]interface{} or ExecutionResult.
func extractStdout(raw interface{}) string {
	if raw == nil {
		return ""
	}
	switch v := raw.(type) {
	case string:
		return v
	case map[string]interface{}:
		if s, ok := v["stdout"].(string); ok {
			return s
		}
		if s, ok := v["output"].(string); ok {
			return s
		}
	}
	return fmt.Sprintf("%v", raw)
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "…"
}
