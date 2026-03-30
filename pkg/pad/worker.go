package pad

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"
)

// WorkerResult is what a single worker returns after completing its task.
type WorkerResult struct {
	TaskID   string        `json:"task_id"`
	Goal     string        `json:"goal"`
	Output   string        `json:"output"`
	Error    string        `json:"error,omitempty"`
	Duration time.Duration `json:"duration_ms"`
}

// Worker executes a single WorkerTask using an LLM and optional Blackboard context.
// Workers are structured goroutines — they share a Blackboard for cross-worker findings
// but do not spawn child workers.
type Worker struct {
	Distiller  PADDistiller
	Blackboard Blackboard
	Model      string // Ollama model name
}

// NewWorker creates a Worker with the given distiller and shared blackboard.
func NewWorker(distiller PADDistiller, blackboard Blackboard) *Worker {
	return &Worker{
		Distiller:  distiller,
		Blackboard: blackboard,
		Model:      "ministral-3:3b",
	}
}

// Run executes the assigned WorkerTask and returns a WorkerResult.
// It reads shared context from the Blackboard and writes its finding back.
func (w *Worker) Run(ctx context.Context, task WorkerTask) WorkerResult {
	start := time.Now()
	result := WorkerResult{
		TaskID: task.ID,
		Goal:   task.Goal,
	}

	if w.Distiller == nil {
		result.Error = "no distiller configured"
		result.Duration = time.Since(start)
		return result
	}

	// Read any relevant context peers have already written to the Blackboard.
	sharedContext := w.readSharedContext(task.ID)

	prompt := w.buildPrompt(task, sharedContext)

	raw, err := w.Distiller.Generate(prompt, map[string]interface{}{
		"temperature": 0.3,
		"num_predict": 768,
	})
	if err != nil {
		result.Error = fmt.Sprintf("LLM error: %v", err)
		result.Duration = time.Since(start)
		log.Printf("[PAD:Worker:%s] error: %v", task.ID[:8], err)
		return result
	}

	output := extractPADText(raw)
	output = strings.TrimSpace(output)
	if output == "" {
		result.Error = "empty LLM response"
		result.Duration = time.Since(start)
		return result
	}

	result.Output = output
	result.Duration = time.Since(start)

	// Write finding to Blackboard so sibling workers / synthesizer can see it.
	if w.Blackboard != nil {
		w.Blackboard.SetState("pad:worker:"+task.ID, map[string]interface{}{
			"goal":   task.Goal,
			"output": output,
			"done":   true,
		})
	}

	log.Printf("[PAD:Worker:%s] done in %dms — %d chars", task.ID[:8], result.Duration.Milliseconds(), len(output))
	return result
}

// ─────────────────────────────────────────────────────────────────────────────
// Internals
// ─────────────────────────────────────────────────────────────────────────────

func (w *Worker) buildPrompt(task WorkerTask, sharedCtx string) string {
	base := fmt.Sprintf(`You are a focused research worker for Oricli, a sovereign AI.

YOUR ASSIGNED GOAL: %s`, task.Goal)

	if sharedCtx != "" {
		base += fmt.Sprintf(`

SHARED CONTEXT FROM PEER WORKERS (use if relevant, do not repeat):
%s`, sharedCtx)
	}

	if len(task.Tools) > 0 {
		base += fmt.Sprintf(`

SUGGESTED TOOLS: %s (use if you have access)`, strings.Join(task.Tools, ", "))
	}

	base += `

Provide a thorough, factual answer to your assigned goal. Be concise but complete.
Do not repeat instructions. Output only your findings.`

	return base
}

// readSharedContext pulls findings other workers have written to the Blackboard.
// Only reads keys from peers (not self).
func (w *Worker) readSharedContext(selfID string) string {
	if w.Blackboard == nil {
		return ""
	}
	// We don't enumerate Blackboard keys directly — workers write to known key patterns.
	// The synthesizer does the full read; workers here get a lightweight summary key
	// that the PADService writes before dispatch if prior context exists.
	val := w.Blackboard.GetState("pad:shared_context")
	if val == nil {
		return ""
	}
	if s, ok := val.(string); ok {
		return s
	}
	return ""
}
