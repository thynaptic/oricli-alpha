package api

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/oracle"
)

// ─── Request / SSE types ─────────────────────────────────────────────────────

type workspaceRunRequest struct {
	Task  string   `json:"task"`
	Tools []string `json:"tools"` // e.g. ["browser","filesystem","github"]
}

type wsEvent struct {
	Type    string `json:"type"`              // plan|step|result|error|done
	Content string `json:"content"`           // human-readable
	Step    int    `json:"step,omitempty"`    // current step index (1-based)
	Total   int    `json:"total,omitempty"`   // total steps
	Tool    string `json:"tool,omitempty"`    // tool used for this step
}

// wsEmit writes a single SSE data frame.
func wsEmit(c *gin.Context, flusher http.Flusher, ev wsEvent) {
	b, _ := json.Marshal(ev)
	fmt.Fprintf(c.Writer, "data: %s\n\n", b)
	if flusher != nil {
		flusher.Flush()
	}
}

// ─── Planning prompt ─────────────────────────────────────────────────────────

func workspacePlanPrompt(task string, tools []string) string {
	toolList := strings.Join(tools, ", ")
	if toolList == "" {
		toolList = "none"
	}
	return fmt.Sprintf(`TASK: %s
ENABLED TOOLS: %s

Output a JSON plan. Do NOT execute the task. Do NOT show results. Output ONLY this JSON structure, nothing else:

{
  "plan": "one sentence describing your approach",
  "steps": [
    {"desc": "human-readable step description", "cmd": "single bash command", "tool": "browser|filesystem|github"}
  ]
}

Tool → command mapping:
- filesystem: standard bash (ls, cat, find, grep, etc.)
- browser: curl -s --max-time 10 <url>
- github: gh repo list, gh issue list --repo owner/name, etc.

Rules:
- Maximum 5 steps
- Only include steps using enabled tools
- Each cmd is ONE safe bash command
- desc is plain English, SMB-friendly
- Output raw JSON only. No markdown fences. No explanation. No preamble.

EXAMPLE OUTPUT for "find large files":
{"plan":"Search filesystem for files over 100MB","steps":[{"desc":"Find files larger than 100MB","cmd":"find / -type f -size +100M 2>/dev/null","tool":"filesystem"}]}`, task, toolList)
}

// ─── Plan types ───────────────────────────────────────────────────────────────

type planStep struct {
	Desc string `json:"desc"`
	Cmd  string `json:"cmd"`
	Tool string `json:"tool"`
}

type planPayload struct {
	Plan  string     `json:"plan"`
	Steps []planStep `json:"steps"`
}

// ─── Oracle helpers ───────────────────────────────────────────────────────────

// oracleCollect drains an oracle.ChatStream channel into a string.
func oracleCollect(ch <-chan string) string {
	var sb strings.Builder
	for tok := range ch {
		sb.WriteString(tok)
	}
	return strings.TrimSpace(sb.String())
}

// ─── Planning: race Oracle vs local ──────────────────────────────────────────

type planRaceResult struct {
	payload planPayload
	err     error
}

// planWithRace starts Oracle and the local model in parallel for the planning step.
// Whichever returns valid parseable JSON first wins; the other is cancelled.
func planWithRace(ctx context.Context, genSvc interface{ ChatStream(context.Context, []map[string]string, map[string]interface{}) (<-chan string, error) }, prompt string) (planPayload, error) {
	raceCtx, cancel := context.WithTimeout(ctx, 35*time.Second)
	defer cancel()

	ch := make(chan planRaceResult, 2)

	msgs := []map[string]string{
		{"role": "system", "content": "You output ONLY raw JSON. No prose. No markdown. No preamble. If you output anything other than a JSON object starting with '{', it is wrong."},
		{"role": "user", "content": prompt},
	}

	// ── Oracle goroutine ─────────────────────────────────────────────────────
	if oracle.Available() {
		go func() {
			oracleMsgs := []oracle.Message{
				{Role: "system", Content: "You output ONLY raw JSON. No prose. No markdown. No preamble. The response MUST start with '{'. If you write anything before '{', it is wrong."},
				{Role: "user", Content: prompt},
			}
			raw := oracleCollect(oracle.ChatStream(raceCtx, oracleMsgs))
			raw = stripJSONFences(raw)
			var p planPayload
			if err := json.Unmarshal([]byte(raw), &p); err != nil {
				log.Printf("[Workspace/Oracle] parse error: %v\nraw: %.200s", err, raw)
				ch <- planRaceResult{err: err}
				return
			}
			ch <- planRaceResult{payload: p}
		}()
	}

	// ── Local model goroutine ─────────────────────────────────────────────────
	go func() {
		tokenCh, err := genSvc.ChatStream(raceCtx, msgs, map[string]interface{}{
			"temperature": 0.1,
			"format":      "json",
		})
		if err != nil {
			ch <- planRaceResult{err: err}
			return
		}
		var sb strings.Builder
		for tok := range tokenCh {
			sb.WriteString(tok)
		}
		raw := stripJSONFences(strings.TrimSpace(sb.String()))
		var p planPayload
		if err := json.Unmarshal([]byte(raw), &p); err != nil {
			log.Printf("[Workspace/Local] parse error: %v\nraw: %.200s", err, raw)
			ch <- planRaceResult{err: err}
			return
		}
		ch <- planRaceResult{payload: p}
	}()

	// ── Collect: first valid result wins ──────────────────────────────────────
	expected := 1
	if oracle.Available() {
		expected = 2
	}
	var lastErr error
	for i := 0; i < expected; i++ {
		r := <-ch
		if r.err == nil {
			cancel() // kill the loser
			return r.payload, nil
		}
		lastErr = r.err
	}
	if lastErr != nil {
		return planPayload{}, lastErr
	}
	return planPayload{}, fmt.Errorf("all planners returned empty")
}

// ─── Handler ─────────────────────────────────────────────────────────────────

// POST /v1/workspaces/run
// Streams a workspace execution: plan → step execution → summary.
func (s *ServerV2) handleWorkspaceRun(c *gin.Context) {
	var req workspaceRunRequest
	if err := c.ShouldBindJSON(&req); err != nil || strings.TrimSpace(req.Task) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "task is required"})
		return
	}

	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("X-Accel-Buffering", "no")
	c.Header("Connection", "keep-alive")

	flusher, _ := c.Writer.(http.Flusher)

	vdi := s.Agent.SovEngine.VDI
	genSvc := s.Agent.GenService
	if genSvc == nil {
		wsEmit(c, flusher, wsEvent{Type: "error", Content: "Generation service unavailable"})
		return
	}

	// ── Phase 1: Plan (Oracle race) ───────────────────────────────────────────
	wsEmit(c, flusher, wsEvent{Type: "plan", Content: "Analysing task…"})

	planPrompt := workspacePlanPrompt(req.Task, req.Tools)
	plan, err := planWithRace(c.Request.Context(), genSvc, planPrompt)
	if err != nil {
		wsEmit(c, flusher, wsEvent{Type: "error", Content: "Could not plan task — try rephrasing"})
		return
	}
	if len(plan.Steps) == 0 {
		wsEmit(c, flusher, wsEvent{Type: "done", Content: "No steps needed for that task."})
		return
	}

	wsEmit(c, flusher, wsEvent{Type: "plan", Content: plan.Plan})

	// ── Phase 2: Execute steps ────────────────────────────────────────────────
	toolEnabled := map[string]bool{}
	for _, t := range req.Tools {
		toolEnabled[t] = true
	}

	results := make([]string, 0, len(plan.Steps))

	for i, step := range plan.Steps {
		if step.Tool != "" && !toolEnabled[step.Tool] {
			wsEmit(c, flusher, wsEvent{
				Type:    "step",
				Step:    i + 1,
				Total:   len(plan.Steps),
				Content: fmt.Sprintf("⏭ Skipped (%s not enabled): %s", step.Tool, step.Desc),
				Tool:    step.Tool,
			})
			continue
		}

		wsEmit(c, flusher, wsEvent{
			Type:    "step",
			Step:    i + 1,
			Total:   len(plan.Steps),
			Content: step.Desc,
			Tool:    step.Tool,
		})

		if vdi == nil || step.Cmd == "" {
			wsEmit(c, flusher, wsEvent{Type: "result", Step: i + 1, Content: "(no VDI — skipped)"})
			continue
		}

		out, execErr := vdi.ExecCommand(step.Cmd)
		if execErr != nil {
			wsEmit(c, flusher, wsEvent{Type: "result", Step: i + 1, Content: fmt.Sprintf("❌ %s", execErr.Error())})
			results = append(results, fmt.Sprintf("Step %d failed: %v", i+1, execErr))
			continue
		}

		trimmed := truncate(out, 800)
		wsEmit(c, flusher, wsEvent{Type: "result", Step: i + 1, Content: trimmed})
		results = append(results, fmt.Sprintf("Step %d (%s): %s", i+1, step.Desc, trimmed))
	}

	// ── Phase 3: Summary — Oracle preferred, local fallback ──────────────────
	if len(results) > 0 {
		wsEmit(c, flusher, wsEvent{Type: "plan", Content: "Summarising results…"})

		sumCtx, sumCancel := context.WithTimeout(c.Request.Context(), 25*time.Second)
		defer sumCancel()

		sumPrompt := fmt.Sprintf("Task: %s\n\nResults:\n%s\n\nSummarise in 2–4 plain sentences. Be direct and factual.", req.Task, strings.Join(results, "\n"))
		sumMsgs := []map[string]string{
			{"role": "system", "content": "You are ORI. Summarise task results concisely. No fluff."},
			{"role": "user", "content": sumPrompt},
		}

		var sumCh <-chan string
		if oracle.Available() {
			oracleMsgs := []oracle.Message{
				{Role: "system", Content: "You are ORI. Summarise task results concisely. No fluff."},
				{Role: "user", Content: sumPrompt},
			}
			sumCh = oracle.ChatStream(sumCtx, oracleMsgs)
		} else {
			var sumErr error
			sumCh, sumErr = genSvc.ChatStream(sumCtx, sumMsgs, map[string]interface{}{"temperature": 0.3})
			if sumErr != nil {
				sumCh = nil
			}
		}

		if sumCh != nil {
			var sumBuf strings.Builder
			for tok := range sumCh {
				sumBuf.WriteString(tok)
			}
			wsEmit(c, flusher, wsEvent{Type: "done", Content: strings.TrimSpace(sumBuf.String())})
			fmt.Fprintf(c.Writer, "data: [DONE]\n\n")
			if flusher != nil {
				flusher.Flush()
			}
			return
		}
	}

	wsEmit(c, flusher, wsEvent{Type: "done", Content: "Task complete."})
	fmt.Fprintf(c.Writer, "data: [DONE]\n\n")
	if flusher != nil {
		flusher.Flush()
	}
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

func stripJSONFences(s string) string {
	s = strings.TrimSpace(s)
	for _, fence := range []string{"```json", "```JSON", "```"} {
		if strings.HasPrefix(s, fence) {
			s = strings.TrimPrefix(s, fence)
			if idx := strings.LastIndex(s, "```"); idx != -1 {
				s = s[:idx]
			}
			break
		}
	}
	// Find the first '{' in case there's leading prose
	if idx := strings.Index(s, "{"); idx > 0 {
		s = s[idx:]
	}
	if idx := strings.LastIndex(s, "}"); idx != -1 && idx < len(s)-1 {
		s = s[:idx+1]
	}
	return strings.TrimSpace(s)
}

func truncate(s string, max int) string {
	if len(s) <= max {
		return strings.TrimSpace(s)
	}
	return strings.TrimSpace(s[:max]) + "…"
}
