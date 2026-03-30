package service

import (
	"bytes"
	"context"
	"encoding/json"
	"log"
	"net/http"
	"sort"
	"time"
)

// GoalExecutor is the autonomous execution loop for sovereign DAG objectives.
// It runs as a persistent goroutine, polling GoalService for objectives that are
// ready to run (pending + all dependencies completed), dispatching them to the
// ActionRouter, and tracking status through the full lifecycle.
//
// On backbone restart any objective stuck in "active" (meaning the last run was
// interrupted) is rehydrated back to "pending" so it will be re-queued automatically.
type GoalExecutor struct {
	Goals    *GoalService
	Router   *ActionRouter
	PollRate time.Duration
}

// NewGoalExecutor wires together the executor. pollRate is how often the executor
// scans for ready objectives; 30s is a reasonable default.
func NewGoalExecutor(goals *GoalService, router *ActionRouter, pollRate time.Duration) *GoalExecutor {
	return &GoalExecutor{
		Goals:    goals,
		Router:   router,
		PollRate: pollRate,
	}
}

// Start rehydrates interrupted goals and begins the execution loop.
// It blocks until ctx is cancelled — call it in a goroutine from the backbone.
func (e *GoalExecutor) Start(ctx context.Context) {
	e.rehydrate()

	ticker := time.NewTicker(e.PollRate)
	defer ticker.Stop()

	log.Printf("[GoalExecutor] DAG execution loop started (poll=%s)", e.PollRate)

	for {
		select {
		case <-ctx.Done():
			log.Println("[GoalExecutor] Shutdown — DAG loop stopped")
			return
		case <-ticker.C:
			e.tick(ctx)
		}
	}
}

// rehydrate resets any "active" objectives back to "pending".
// "active" at boot means the previous run was interrupted mid-execution.
func (e *GoalExecutor) rehydrate() {
	all, err := e.Goals.ListObjectives("")
	if err != nil {
		log.Printf("[GoalExecutor] rehydrate: failed to list objectives: %v", err)
		return
	}
	count := 0
	for _, obj := range all {
		if obj.Status == GoalActive {
			if _, err := e.Goals.UpdateObjective(obj.ID, map[string]interface{}{
				"status":      string(GoalPending),
				"retry_count": obj.RetryCount + 1,
			}); err != nil {
				log.Printf("[GoalExecutor] rehydrate: failed to reset %s: %v", obj.ID, err)
			} else {
				count++
			}
		}
	}
	if count > 0 {
		log.Printf("[GoalExecutor] Rehydrated %d interrupted objective(s) to pending", count)
	}
}

// tick runs one scan-and-dispatch cycle.
func (e *GoalExecutor) tick(ctx context.Context) {
	all, err := e.Goals.ListObjectives("")
	if err != nil {
		log.Printf("[GoalExecutor] tick: list error: %v", err)
		return
	}

	// Sort by priority descending so high-priority goals run first.
	sort.Slice(all, func(i, j int) bool {
		return all[i].Priority > all[j].Priority
	})

	for i := range all {
		obj := &all[i]
		if obj.Status != GoalPending {
			continue
		}
		if !obj.IsReady(all) {
			continue
		}
		e.dispatch(ctx, obj, all)
		// Only dispatch one goal per tick to avoid flooding the ActionRouter.
		break
	}
}

// dispatch marks the objective active and fires it into the ActionRouter.
func (e *GoalExecutor) dispatch(ctx context.Context, obj *Objective, all []Objective) {
	if _, err := e.Goals.UpdateObjective(obj.ID, map[string]interface{}{
		"status": string(GoalActive),
	}); err != nil {
		log.Printf("[GoalExecutor] dispatch: failed to mark %s active: %v", obj.ID, err)
		return
	}

	log.Printf("[GoalExecutor] Dispatching objective %s (priority=%d): %q", obj.ID, obj.Priority, obj.Goal)

	if e.Router == nil {
		// No router wired — mark failed so it doesn't loop forever.
		e.markFailed(obj.ID, "no ActionRouter wired")
		return
	}

	// Build a synthetic DetectedAction from the objective goal text.
	// DetectAction may not match a trigger word for arbitrary goals,
	// so we synthesize a research action directly.
	act := DetectAction(obj.Goal)
	if act == nil {
		act = &DetectedAction{
			Type:       ActionResearch,
			Subject:    obj.Goal,
			Confidence: 1.0,
		}
	}

	jobID := "goal-" + obj.ID
	e.Router.Dispatch(ctx, jobID, act)

	// GoalExecutor is fire-and-forget at dispatch time.
	// A completion callback goroutine waits for the job and updates status.
	go e.awaitCompletion(ctx, obj.ID, jobID)
}

// awaitCompletion polls for job completion and updates objective status accordingly.
func (e *GoalExecutor) awaitCompletion(ctx context.Context, objID, jobID string) {
	const maxWait = 10 * time.Minute
	const pollInterval = 5 * time.Second
	deadline := time.Now().Add(maxWait)

	for time.Now().Before(deadline) {
		select {
		case <-ctx.Done():
			return
		case <-time.After(pollInterval):
		}

		if e.Router == nil {
			e.markFailed(objID, "router unavailable during await")
			return
		}

		status := e.Router.JobStatus(jobID)
		switch status {
		case JobStatusCompleted:
			if _, err := e.Goals.UpdateObjective(objID, map[string]interface{}{
				"status":   string(GoalCompleted),
				"progress": 1.0,
			}); err != nil {
				log.Printf("[GoalExecutor] failed to mark %s completed: %v", objID, err)
			} else {
				log.Printf("[GoalExecutor] Objective %s completed ✓", objID)
				if obj, err := e.Goals.GetObjective(objID); err == nil && obj.WebhookURL != "" {
					go fireGoalWebhook(obj.WebhookURL, objID, string(GoalCompleted), "", obj.Result)
				}
			}
			return
		case JobStatusFailed:
			e.markFailed(objID, "ActionRouter job reported failure")
			return
		}
		// JobStatusPending / JobStatusRunning — keep polling
	}

	// Timeout — treat as failure and rehydrate on next restart
	e.markFailed(objID, "execution timeout exceeded "+maxWait.String())
}

func (e *GoalExecutor) markFailed(objID, reason string) {
	if _, err := e.Goals.UpdateObjective(objID, map[string]interface{}{
		"status": string(GoalFailed),
		"metadata": map[string]interface{}{
			"failure_reason": reason,
			"failed_at":      time.Now().Format(time.RFC3339),
		},
	}); err != nil {
		log.Printf("[GoalExecutor] failed to mark %s as failed: %v", objID, err)
	} else {
		log.Printf("[GoalExecutor] Objective %s failed: %s", objID, reason)
	}
	if obj, err := e.Goals.GetObjective(objID); err == nil && obj.WebhookURL != "" {
		go fireGoalWebhook(obj.WebhookURL, objID, string(GoalFailed), reason, "")
	}
}

// fireGoalWebhook POSTs a goal terminal-state notification to the registered URL.
// Runs in a goroutine — never blocks the execution loop.
func fireGoalWebhook(url, goalID, status, reason, result string) {
	payload := map[string]string{
		"goal_id": goalID,
		"status":  status,
		"reason":  reason,
		"result":  result,
	}
	body, _ := json.Marshal(payload)
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		log.Printf("[GoalWebhook] bad URL for %s: %v", goalID, err)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("[GoalWebhook] delivery failed for %s: %v", goalID, err)
		return
	}
	resp.Body.Close()
	log.Printf("[GoalWebhook] %s → %s (%d)", goalID, url, resp.StatusCode)
}
