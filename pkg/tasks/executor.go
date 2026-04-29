package tasks

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// StepUpdate is emitted during execution so callers can stream SSE or log progress.
type StepUpdate struct {
	StepID  string     `json:"step_id"`
	Status  TaskStatus `json:"status"`
	Snippet string     `json:"snippet,omitempty"`
}

// ExecuteFunc is the dispatch signature for running a single step.
// Implementations in the API layer wire this to the real service backends
// (search, generation, webhooks, etc.).
type ExecuteFunc func(ctx context.Context, step Step) (string, error)

// Executor runs a task's step DAG against a Store, persisting status as it goes.
type Executor struct {
	store   *Store
	dispatch ExecuteFunc
	emit    func(StepUpdate)
}

// NewExecutor creates an Executor. emit may be nil (no streaming needed).
func NewExecutor(store *Store, dispatch ExecuteFunc, emit func(StepUpdate)) *Executor {
	if emit == nil {
		emit = func(StepUpdate) {}
	}
	return &Executor{store: store, dispatch: dispatch, emit: emit}
}

// Run executes all steps in the task identified by taskID in dependency order.
// Marks the task done/failed in the store when complete. Safe to call in a goroutine.
func (e *Executor) Run(ctx context.Context, taskID, tenantID string) error {
	task, err := e.store.GetTask(ctx, taskID, tenantID)
	if err != nil {
		return fmt.Errorf("executor: load task %s: %w", taskID, err)
	}

	_ = e.store.UpdateTask(ctx, taskID, tenantID, map[string]interface{}{"status": string(TaskRunning)})

	results := make(map[string]string, len(task.Steps))
	var mu sync.Mutex

	for {
		ready := readySteps(task.Steps, results)
		if len(ready) == 0 {
			break
		}

		var wg sync.WaitGroup
		for _, step := range ready {
			step := step
			wg.Add(1)
			go func() {
				defer wg.Done()
				e.runStep(ctx, &step, results, &mu)
			}()
		}
		wg.Wait()

		// Refresh step list from DB so status is authoritative.
		task.Steps, err = e.store.ListSteps(ctx, taskID)
		if err != nil {
			break
		}

		// Re-build results map from DB state.
		mu.Lock()
		for _, s := range task.Steps {
			if s.Status == TaskDone {
				results[s.ID] = s.Result
			}
		}
		mu.Unlock()

		if allSettled(task.Steps) {
			break
		}
	}

	finalStatus := TaskDone
	for _, s := range task.Steps {
		if s.Status == TaskFailed {
			finalStatus = TaskFailed
			break
		}
	}

	updates := map[string]interface{}{"status": string(finalStatus)}
	if finalStatus == TaskDone {
		now := time.Now().UTC()
		updates["resolved_at"] = now
	}
	_ = e.store.UpdateTask(ctx, taskID, tenantID, updates)
	return nil
}

func (e *Executor) runStep(ctx context.Context, step *Step, results map[string]string, mu *sync.Mutex) {
	_ = e.store.UpdateStep(ctx, step.ID, TaskRunning, "")
	e.emit(StepUpdate{StepID: step.ID, Status: TaskRunning})

	result, err := e.dispatch(ctx, *step)

	status := TaskDone
	if err != nil {
		status = TaskFailed
		result = err.Error()
	}
	_ = e.store.UpdateStep(ctx, step.ID, status, result)

	snippet := result
	if len(snippet) > 200 {
		snippet = snippet[:200] + "…"
	}
	e.emit(StepUpdate{StepID: step.ID, Status: status, Snippet: snippet})

	mu.Lock()
	if status == TaskDone {
		results[step.ID] = result
	}
	mu.Unlock()
}

// readySteps returns steps that are still pending and whose dependencies are all done.
func readySteps(steps []Step, results map[string]string) []Step {
	var ready []Step
	for _, s := range steps {
		if s.Status != TaskPending {
			continue
		}
		allDone := true
		for _, dep := range s.DependsOn {
			if _, ok := results[dep]; !ok {
				allDone = false
				break
			}
		}
		if allDone {
			ready = append(ready, s)
		}
	}
	return ready
}

func allSettled(steps []Step) bool {
	for _, s := range steps {
		if s.Status == TaskPending || s.Status == TaskRunning {
			return false
		}
	}
	return true
}
