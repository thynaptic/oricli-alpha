package tools

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/thynaptic/ori-capsule/internal/byok"
	"github.com/thynaptic/ori-capsule/internal/forge"
	"github.com/thynaptic/ori-capsule/internal/gosh"
	"github.com/thynaptic/ori-capsule/internal/memory"
	"github.com/thynaptic/ori-capsule/internal/rag"
	"github.com/thynaptic/ori-capsule/internal/skills"
)

// Deps are capsule services exposed as allowlisted tools.
type Deps struct {
	Mem    *memory.Runtime
	Gosh   *gosh.Manager
	RAG    *rag.Store
	Skills *skills.Library
}

// RegisterBuiltins installs the default capsule tool allowlist.
func RegisterBuiltins(r *Registry, d Deps) {
	if r == nil {
		return
	}
	_ = r.Register(byok.ToolDefinition{
		Type: "function",
		Function: byok.ToolFunction{
			Name:        "tasks_list",
			Description: "List local capsule tasks (consumer memory).",
			Parameters:  objectSchema(map[string]any{}),
		},
	}, func(args map[string]any) (string, error) {
		if d.Mem == nil || d.Mem.Tasks == nil {
			return "", fmt.Errorf("memory unavailable")
		}
		list, err := d.Mem.Tasks.List(50)
		if err != nil {
			return "", err
		}
		return mustJSON(list), nil
	})

	_ = r.Register(byok.ToolDefinition{
		Type: "function",
		Function: byok.ToolFunction{
			Name:        "tasks_add",
			Description: "Add a local task. Args: title (string).",
			Parameters:  objectSchema(map[string]any{"title": strProp("Task title")}, "title"),
		},
	}, func(args map[string]any) (string, error) {
		if d.Mem == nil || d.Mem.Tasks == nil {
			return "", fmt.Errorf("memory unavailable")
		}
		title, _ := args["title"].(string)
		t, err := d.Mem.Tasks.Add(title)
		if err != nil {
			return "", err
		}
		return mustJSON(t), nil
	})

	_ = r.Register(byok.ToolDefinition{
		Type: "function",
		Function: byok.ToolFunction{
			Name:        "tasks_done",
			Description: "Mark a task done/undone. Args: id (number), done (bool, default true).",
			Parameters: objectSchema(map[string]any{
				"id":   numProp("Task id"),
				"done": boolProp("Done flag"),
			}, "id"),
		},
	}, func(args map[string]any) (string, error) {
		if d.Mem == nil || d.Mem.Tasks == nil {
			return "", fmt.Errorf("memory unavailable")
		}
		idF, ok := args["id"].(float64)
		if !ok {
			return "", fmt.Errorf("id required (number)")
		}
		done := true
		if v, ok := args["done"].(bool); ok {
			done = v
		}
		if err := d.Mem.Tasks.SetDone(int64(idF), done); err != nil {
			return "", err
		}
		return mustJSON(map[string]any{"id": int64(idF), "done": done}), nil
	})

	_ = r.Register(byok.ToolDefinition{
		Type: "function",
		Function: byok.ToolFunction{
			Name:        "spaces_list",
			Description: "List local knowledge spaces.",
			Parameters:  objectSchema(map[string]any{}),
		},
	}, func(args map[string]any) (string, error) {
		if d.Mem == nil || d.Mem.Spaces == nil {
			return "", fmt.Errorf("memory unavailable")
		}
		return mustJSON(d.Mem.Spaces.List()), nil
	})

	_ = r.Register(byok.ToolDefinition{
		Type: "function",
		Function: byok.ToolFunction{
			Name:        "rag_query",
			Description: "Query local BM25 RAG store. Args: query (string), top_k (number, optional).",
			Parameters: objectSchema(map[string]any{
				"query": strProp("Search query"),
				"top_k": numProp("Max hits"),
			}, "query"),
		},
	}, func(args map[string]any) (string, error) {
		if d.RAG == nil {
			return "", fmt.Errorf("rag unavailable")
		}
		q, _ := args["query"].(string)
		topK := rag.DefaultTopK
		if v, ok := args["top_k"].(float64); ok && int(v) > 0 {
			topK = int(v)
		}
		hits := d.RAG.Query(q, topK)
		return mustJSON(hits), nil
	})

	_ = r.Register(byok.ToolDefinition{
		Type: "function",
		Function: byok.ToolFunction{
			Name:        "skills_list",
			Description: "List mounted .ori skill overlays (name, description, triggers).",
			Parameters:  objectSchema(map[string]any{}),
		},
	}, func(args map[string]any) (string, error) {
		if d.Skills == nil {
			return mustJSON([]any{}), nil
		}
		return mustJSON(d.Skills.List()), nil
	})

	_ = r.Register(byok.ToolDefinition{
		Type: "function",
		Function: byok.ToolFunction{
			Name:        "gosh_verify",
			Description: "Statically verify a GOSH script/Go source against the forge constitution (no execute).",
			Parameters: objectSchema(map[string]any{
				"script":      strProp("Shell script"),
				"source":      strProp("Yaegi Go source"),
				"strict_tool": boolProp("Apply JIT tool contract"),
			}),
		},
	}, func(args map[string]any) (string, error) {
		script, _ := args["script"].(string)
		source, _ := args["source"].(string)
		strict, _ := args["strict_tool"].(bool)
		res := forge.VerifyStatic(forge.VerifyRequest{
			Script:     script,
			Source:     source,
			StrictTool: strict,
		})
		return mustJSON(res), nil
	})

	_ = r.Register(byok.ToolDefinition{
		Type: "function",
		Function: byok.ToolFunction{
			Name:        "gosh_run",
			Description: "Run an allowlisted script in the capsule GOSH sandbox (forge-verified). Args: script (string), session_id (optional), expected_result (optional).",
			Parameters: objectSchema(map[string]any{
				"script":          strProp("Allowlisted shell script (cat/ls/mkdir/rm/pwd/echo)"),
				"session_id":      strProp("Groups ActionTracker lessons"),
				"expected_result": strProp("Optional stdout expectation"),
			}, "script"),
		},
	}, func(args map[string]any) (string, error) {
		if d.Gosh == nil || !d.Gosh.Enabled() {
			return "", fmt.Errorf("gosh disabled")
		}
		script, _ := args["script"].(string)
		sessionID, _ := args["session_id"].(string)
		expected, _ := args["expected_result"].(string)
		ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
		defer cancel()
		res := d.Gosh.Run(ctx, gosh.RunRequest{
			Script:         script,
			SessionID:      sessionID,
			ExpectedResult: expected,
		})
		return mustJSON(map[string]any{
			"ok":      res.ExitOK,
			"stdout":  res.Stdout,
			"stderr":  res.Stderr,
			"error":   res.Error,
			"mode":    res.Mode,
			"verify":  res.Verify,
			"action":  res.Action,
			"lessons": truncate(res.Lessons, 1200),
		}), nil
	})
}

func mustJSON(v any) string {
	b, err := json.Marshal(v)
	if err != nil {
		return errJSON("marshal_error", "%v", err)
	}
	return string(b)
}

func truncate(s string, n int) string {
	s = strings.TrimSpace(s)
	if len(s) <= n {
		return s
	}
	return s[:n-1] + "…"
}
