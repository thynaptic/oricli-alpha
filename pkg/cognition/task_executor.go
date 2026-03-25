package cognition

// ---------------------------------------------------------------------------
// Task Executor — runs a Task DAG produced by DecomposePrompt().
//
// Execution model:
//   - Tasks with no pending dependencies run in parallel.
//   - Results from completed tasks are passed as context to dependent tasks.
//   - The SSE emitter is a simple callback so the executor has no import
//     dependency on the HTTP layer.
//   - LLM (Generate action) is only called for the final synthesis step.
// ---------------------------------------------------------------------------

import (
	"context"
	"fmt"
	"strings"
	"sync"

	"github.com/thynaptic/oricli-go/pkg/searchintent"
)

// ── SSE Emitter ────────────────────────────────────────────────────────────

// TaskSSEEmitter is the callback the executor uses to push SSE events.
// The server layer provides a concrete implementation.
type TaskSSEEmitter func(eventType string, payload interface{})

// ── Services interface ─────────────────────────────────────────────────────

// TaskServices bundles the deterministic backend services the executor needs.
// All fields are optional — executor degrades gracefully if nil.
type TaskServices struct {
	// Searcher is used for Research and Fetch actions.
	Searcher interface {
		SearchWithIntent(q searchintent.SearchQuery) (string, error)
	}
	// MemoryBank for RAG context injection and Save actions.
	MemoryBank MemoryBankIface
	// Generator is only used for ActionGenerate.
	Generator interface {
		Generate(prompt string, opts map[string]interface{}) (map[string]interface{}, error)
	}
}

// MemoryFragment is a minimal interface over the service layer type.
type MemoryFragment interface {
	GetContent() string
}

// MemoryBankAdapter wraps the concrete service.MemoryBank so it satisfies
// TaskServices.MemoryBank without importing the service package from cognition.
type MemoryBankIface interface {
	WriteKnowledgeFragment(topic, intent, content string, importance float64)
	QuerySimilarStrings(ctx context.Context, query string, topN int) ([]string, error)
}

// ── Executor ───────────────────────────────────────────────────────────────

// TaskExecutor runs a DAG of Tasks to completion.
type TaskExecutor struct {
	svc     TaskServices
	emitSSE TaskSSEEmitter
}

// NewTaskExecutor creates an executor with the given services and SSE emitter.
func NewTaskExecutor(svc TaskServices, emitter TaskSSEEmitter) *TaskExecutor {
	return &TaskExecutor{svc: svc, emitSSE: emitter}
}

// Run executes tasks in dependency order. Parallel-safe tasks run concurrently.
// Returns the accumulated context string for use in the final Generate step,
// and any error from the Generate step itself.
func (e *TaskExecutor) Run(ctx context.Context, tasks []Task) (string, error) {
	if len(tasks) == 0 {
		return "", nil
	}

	// Emit the full plan immediately so the UI can render the card.
	e.emitSSE("task_plan", planPayload(tasks))

	// Build an index and a results map.
	index := make(map[string]*Task, len(tasks))
	for i := range tasks {
		index[tasks[i].ID] = &tasks[i]
	}

	results := make(map[string]string, len(tasks)) // taskID → output
	var mu sync.Mutex

	// Iterative wave executor: process until all tasks are done or failed.
	for {
		ready := readyTasks(tasks, results)
		if len(ready) == 0 {
			break
		}

		var wg sync.WaitGroup
		for _, t := range ready {
			t := t
			wg.Add(1)
			go func() {
				defer wg.Done()
				e.runTask(ctx, t, results, &mu)
			}()
		}
		wg.Wait()

		// If every remaining task is either done or failed, we're finished.
		allSettled := true
		for _, t := range tasks {
			if t.Status == TaskPending || t.Status == TaskRunning {
				allSettled = false
				break
			}
		}
		if allSettled {
			break
		}
	}

	// Collect all non-Generate results as accumulated context.
	var contextParts []string
	var generateResult string
	for _, t := range tasks {
		mu.Lock()
		r := results[t.ID]
		mu.Unlock()
		if t.Action == ActionGenerate {
			generateResult = r
		} else if r != "" {
			contextParts = append(contextParts, fmt.Sprintf("[%s]\n%s", t.Title, r))
		}
	}
	if generateResult != "" {
		return generateResult, nil
	}
	return strings.Join(contextParts, "\n\n"), nil
}

// runTask executes a single task and updates its status via SSE.
func (e *TaskExecutor) runTask(ctx context.Context, t *Task, results map[string]string, mu *sync.Mutex) {
	t.Status = TaskRunning
	e.emitSSE("task_update", taskUpdatePayload(t.ID, TaskRunning, ""))

	result, err := e.executeAction(ctx, t, results, mu)

	mu.Lock()
	if err != nil {
		t.Status = TaskFailed
		t.Result = err.Error()
		results[t.ID] = ""
	} else {
		t.Status = TaskDone
		t.Result = result
		results[t.ID] = result
	}
	mu.Unlock()

	status := TaskDone
	snippet := result
	if len(snippet) > 200 {
		snippet = snippet[:200] + "…"
	}
	if err != nil {
		status = TaskFailed
		snippet = err.Error()
	}
	e.emitSSE("task_update", taskUpdatePayload(t.ID, status, snippet))
}

// executeAction dispatches to the correct deterministic backend.
func (e *TaskExecutor) executeAction(ctx context.Context, t *Task, results map[string]string, mu *sync.Mutex) (string, error) {
	topic := t.Args["topic"]

	switch t.Action {

	case ActionResearch:
		return e.doResearch(ctx, topic)

	case ActionFetch:
		return e.doFetch(topic)

	case ActionSummarize:
		// Use accumulated context from dependencies as the raw text.
		raw := e.depContext(t, results, mu)
		if raw == "" {
			// Fallback: fetch first.
			var err error
			raw, err = e.doFetch(topic)
			if err != nil {
				return "", err
			}
		}
		return ExtractFacts(topic, raw, searchintent.IntentTopic), nil

	case ActionCompare:
		// Both dependency results should be in results already.
		raw := e.depContext(t, results, mu)
		if raw == "" {
			return "", fmt.Errorf("no dependency results for compare")
		}
		// Simple diff: return both sides labelled.
		return raw, nil

	case ActionSave:
		raw := e.depContext(t, results, mu)
		topic := "task_result"
		for _, v := range t.Args {
			if v != "" {
				topic = v
				break
			}
		}
		if e.svc.MemoryBank != nil && raw != "" {
			e.svc.MemoryBank.WriteKnowledgeFragment(topic, "task", raw, 0.7)
		}
		return "Saved.", nil

	case ActionGenerate:
		// Build a synthesis prompt from all dep results.
		depCtx := e.depContext(t, results, mu)
		if e.svc.Generator == nil {
			return depCtx, nil // no generator — return raw context
		}
		prompt := buildSynthesisPrompt(depCtx)
		res, err := e.svc.Generator.Generate(prompt, map[string]interface{}{
			"model": "ministral-3:3b",
			"options": map[string]interface{}{
				"num_predict": 512,
				"temperature": 0.5,
			},
		})
		if err != nil {
			return "", err
		}
		text, _ := res["text"].(string)
		return text, nil
	}

	return "", fmt.Errorf("unknown action: %s", t.Action)
}

// doResearch fetches via SearXNG with intent classification, falls back to
// MemoryBank RAG, and runs the TF-IDF extractor — no LLM.
func (e *TaskExecutor) doResearch(ctx context.Context, topic string) (string, error) {
	if e.svc.Searcher != nil {
		intent := searchintent.ClassifySearchIntent(topic)
		sq := searchintent.BuildSearchQuery(topic, intent)
		text, err := e.svc.Searcher.SearchWithIntent(sq)
		if err == nil && strings.TrimSpace(text) != "" {
			return ExtractFacts(topic, text, intent), nil
		}
	}
	// RAG fallback
	if e.svc.MemoryBank != nil {
		frags, err := e.svc.MemoryBank.QuerySimilarStrings(ctx, topic, 3)
		if err == nil && len(frags) > 0 {
			raw := strings.Join(frags, "\n")
			return ExtractFacts(topic, raw, searchintent.IntentTopic), nil
		}
	}
	return "", fmt.Errorf("no results for: %s", topic)
}

// doFetch does a raw SearXNG search, returns snippet text.
func (e *TaskExecutor) doFetch(topic string) (string, error) {
	if e.svc.Searcher == nil {
		return "", fmt.Errorf("no searcher configured")
	}
	intent := searchintent.ClassifySearchIntent(topic)
	sq := searchintent.BuildSearchQuery(topic, intent)
	return e.svc.Searcher.SearchWithIntent(sq)
}
// depContext collects results from all dependency tasks as a single string.
func (e *TaskExecutor) depContext(t *Task, results map[string]string, mu *sync.Mutex) string {
	mu.Lock()
	defer mu.Unlock()
	var parts []string
	for _, depID := range t.DependsOn {
		if r := results[depID]; r != "" {
			parts = append(parts, r)
		}
	}
	return strings.Join(parts, "\n\n")
}

// ── Helpers ────────────────────────────────────────────────────────────────

// readyTasks returns tasks whose dependencies are all Done (or have no deps)
// and which are still Pending.
func readyTasks(tasks []Task, results map[string]string) []*Task {
	var ready []*Task
	for i := range tasks {
		t := &tasks[i]
		if t.Status != TaskPending {
			continue
		}
		allDone := true
		for _, dep := range t.DependsOn {
			if _, ok := results[dep]; !ok {
				allDone = false
				break
			}
		}
		if allDone {
			ready = append(ready, t)
		}
	}
	return ready
}

func buildSynthesisPrompt(context string) string {
	if strings.TrimSpace(context) == "" {
		return "Summarise the findings."
	}
	return fmt.Sprintf("Using only the research findings below, write a clear and concise response.\n\nFINDINGS:\n%s", context)
}

// ── SSE payload helpers ────────────────────────────────────────────────────

type taskPlanPayload struct {
	Tasks []taskPlanItem `json:"tasks"`
}

type taskPlanItem struct {
	ID        string     `json:"id"`
	Title     string     `json:"title"`
	Action    TaskAction `json:"action"`
	DependsOn []string   `json:"depends_on"`
	Status    TaskStatus `json:"status"`
}

func planPayload(tasks []Task) taskPlanPayload {
	items := make([]taskPlanItem, len(tasks))
	for i, t := range tasks {
		deps := t.DependsOn
		if deps == nil {
			deps = []string{}
		}
		items[i] = taskPlanItem{
			ID:        t.ID,
			Title:     t.Title,
			Action:    t.Action,
			DependsOn: deps,
			Status:    t.Status,
		}
	}
	return taskPlanPayload{Tasks: items}
}

type taskUpdatePayloadT struct {
	ID      string     `json:"id"`
	Status  TaskStatus `json:"status"`
	Snippet string     `json:"snippet,omitempty"`
}

func taskUpdatePayload(id string, status TaskStatus, snippet string) taskUpdatePayloadT {
	return taskUpdatePayloadT{ID: id, Status: status, Snippet: snippet}
}
