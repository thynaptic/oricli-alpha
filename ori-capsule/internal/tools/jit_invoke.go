package tools

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/thynaptic/ori-capsule/internal/forge"
	"github.com/thynaptic/ori-capsule/internal/gosh"
)

// InvokeJIT runs a stored JIT tool inside GOSH.
func InvokeJIT(ctx context.Context, mgr *gosh.Manager, tool forge.JITTool, args map[string]any) (string, error) {
	if mgr == nil || !mgr.Enabled() {
		return "", fmt.Errorf("gosh disabled")
	}
	if ctx == nil {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(context.Background(), 8*time.Second)
		defer cancel()
	}
	switch tool.Kind {
	case "script":
		res := mgr.Run(ctx, gosh.RunRequest{Script: tool.Source})
		return mustJSON(map[string]any{
			"ok": res.ExitOK, "stdout": res.Stdout, "stderr": res.Stderr, "error": res.Error,
		}), nil
	default:
		argList := jitArgsToStrings(args)
		script := tool.Name
		for _, a := range argList {
			script += " " + jitShellQuote(a)
		}
		res := mgr.Run(ctx, gosh.RunRequest{
			Tools:  []gosh.ToolDef{{Name: tool.Name, Source: tool.Source}},
			Script: script,
		})
		return mustJSON(map[string]any{
			"ok": res.ExitOK, "stdout": res.Stdout, "stderr": res.Stderr, "error": res.Error,
		}), nil
	}
}

func jitArgsToStrings(args map[string]any) []string {
	if args == nil {
		return nil
	}
	if v, ok := args["args"].([]any); ok {
		out := make([]string, 0, len(v))
		for _, x := range v {
			out = append(out, fmt.Sprint(x))
		}
		return out
	}
	if v, ok := args["input"].(string); ok {
		return []string{v}
	}
	b, _ := json.Marshal(args)
	return []string{string(b)}
}

func jitShellQuote(s string) string {
	if s == "" {
		return `""`
	}
	if !strings.ContainsAny(s, " \t\"'\\$`") {
		return s
	}
	return `"` + strings.ReplaceAll(s, `"`, `\"`) + `"`
}
