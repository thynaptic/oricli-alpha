package cognition

// ---------------------------------------------------------------------------
// Task Decomposer — pre-execution planning layer.
//
// IsMultiStep() detects clearly multi-step prompts in <1ms (pure heuristic).
// DecomposePrompt() builds a typed Task DAG from the prompt using pattern
// matching only — no LLM calls, no network I/O.
//
// Task types map to deterministic actions; LLM is only invoked in the final
// Generate step (if any), keeping Ollama free for the actual response.
// ---------------------------------------------------------------------------

import (
	"fmt"
	"regexp"
	"strings"
)

// ── Types ──────────────────────────────────────────────────────────────────

// TaskAction is the kind of work a task performs.
type TaskAction string

const (
	ActionResearch  TaskAction = "research"   // CuriosityDaemon + RAG — no LLM
	ActionFetch     TaskAction = "fetch"       // SearXNG SearchWithIntent — no LLM
	ActionSummarize TaskAction = "summarize"   // ExtractFacts TF-IDF — no LLM
	ActionCompare   TaskAction = "compare"     // dual research + diff score — no LLM
	ActionGenerate  TaskAction = "generate"    // final LLM text generation
	ActionSave      TaskAction = "save"        // MemoryBank write — no LLM
)

// TaskStatus tracks execution state.
type TaskStatus string

const (
	TaskPending TaskStatus = "pending"
	TaskRunning TaskStatus = "running"
	TaskDone    TaskStatus = "done"
	TaskFailed  TaskStatus = "failed"
)

// Task is a single unit in a pre-execution plan.
type Task struct {
	ID        string            `json:"id"`
	Title     string            `json:"title"`
	Action    TaskAction        `json:"action"`
	Args      map[string]string `json:"args"`
	DependsOn []string          `json:"depends_on"`
	Status    TaskStatus        `json:"status"`
	Result    string            `json:"result,omitempty"`
}

// ── IsMultiStep ────────────────────────────────────────────────────────────

// multiStepPatterns are the signal patterns that indicate a multi-step request.
// Deliberately conservative: only fire on clearly chained action prompts.
var multiStepPatterns = []*regexp.Regexp{
	// "research X and compare to Y"
	regexp.MustCompile(`(?i)\bresearch\b.{3,60}\b(compare|summarize|analyse|analyze|report)\b`),
	// "find X, summarize it and save"
	regexp.MustCompile(`(?i)\b(find|fetch|look up|search for)\b.{3,80}\b(summarize|compare|report|save|store)\b`),
	// explicit chain: "X, then Y" or "X and then Y"  with action verbs
	regexp.MustCompile(`(?i)\b(research|find|fetch|analyse|analyze|summarize|compare)\b.{0,60}\b(and then|then|after that|next)\b.{0,60}\b(research|find|summarize|compare|save|generate|write|report)\b`),
	// "compare X and Y" standalone
	regexp.MustCompile(`(?i)\bcompare\b.{3,80}\band\b`),
	// "summarize X and save / write a report"
	regexp.MustCompile(`(?i)\b(summarize|summarise)\b.{3,80}\b(save|store|write|report)\b`),
	// comma-separated action list: "research X, compare Y, save Z"
	regexp.MustCompile(`(?i)\b(research|find|fetch|summarize|compare|analyse|analyze)\b[^,]{3,60},\s*\b(research|find|fetch|summarize|compare|analyse|analyze|save|generate|write)\b`),
}

// IsMultiStep returns true if the prompt is a clearly multi-step request.
// Must complete in <1ms — pure regex, no allocations beyond the match check.
func IsMultiStep(prompt string) bool {
	if len(prompt) < 20 { // too short to be multi-step
		return false
	}
	for _, re := range multiStepPatterns {
		if re.MatchString(prompt) {
			return true
		}
	}
	return false
}

// ── DecomposePrompt ────────────────────────────────────────────────────────

var (
	reCompare   = regexp.MustCompile(`(?i)compare\s+(.+?)\s+(?:and|to|vs\.?|versus)\s+(.+?)(?:\s*[,.]|$)`)
	reResearch  = regexp.MustCompile(`(?i)(?:research|find out about|look up|investigate)\s+(.+?)(?:\s*[,;]|$|\s+and\s|\s+then\s)`)
	reFetch     = regexp.MustCompile(`(?i)(?:fetch|get|find|search for)\s+(.+?)(?:\s*[,;]|$|\s+and\s|\s+then\s)`)
	reSummarize = regexp.MustCompile(`(?i)(?:summarize|summarise|give me a summary of)\s+(.+?)(?:\s*[,;]|$|\s+and\s|\s+then\s)`)
	reSave      = regexp.MustCompile(`(?i)(?:save|store|write a report|write up|create a report)`)
)

// DecomposePrompt builds a Task DAG from the prompt using heuristic patterns.
// Returns nil if the prompt cannot be decomposed into a meaningful plan.
func DecomposePrompt(prompt string) []Task {
	lower := strings.ToLower(strings.TrimSpace(prompt))
	var tasks []Task
	idCounter := 0
	nextID := func(prefix string) string {
		idCounter++
		return fmt.Sprintf("%s_%d", prefix, idCounter)
	}

	// ── Pattern 1: "compare X and Y" ────────────────────────────────────────
	if m := reCompare.FindStringSubmatch(prompt); len(m) == 3 {
		sideA := strings.TrimSpace(m[1])
		sideB := strings.TrimSpace(m[2])
		idA := nextID("research")
		idB := nextID("research")
		idCmp := nextID("compare")
		tasks = append(tasks,
			Task{ID: idA, Title: fmt.Sprintf("Research: %s", sideA), Action: ActionResearch,
				Args: map[string]string{"topic": sideA}, Status: TaskPending},
			Task{ID: idB, Title: fmt.Sprintf("Research: %s", sideB), Action: ActionResearch,
				Args: map[string]string{"topic": sideB}, Status: TaskPending},
			Task{ID: idCmp, Title: fmt.Sprintf("Compare: %s vs %s", sideA, sideB), Action: ActionCompare,
				Args: map[string]string{"a": sideA, "b": sideB}, DependsOn: []string{idA, idB}, Status: TaskPending},
		)
		// Still check for save/generate suffix
		lastID := idCmp
		if reSave.MatchString(lower) {
			idSave := nextID("save")
			tasks = append(tasks, Task{ID: idSave, Title: "Save findings to memory", Action: ActionSave,
				Args: map[string]string{}, DependsOn: []string{lastID}, Status: TaskPending})
			lastID = idSave
		}
		tasks = append(tasks, Task{ID: nextID("generate"), Title: "Generate response", Action: ActionGenerate,
			Args: map[string]string{}, DependsOn: []string{lastID}, Status: TaskPending})
		return tasks
	}

	// ── Pattern 2: research → [summarize] → [save] chain ───────────────────
	var chainDeps []string

	if m := reResearch.FindStringSubmatch(prompt); len(m) == 2 {
		topic := strings.TrimSpace(m[1])
		id := nextID("research")
		tasks = append(tasks, Task{ID: id, Title: fmt.Sprintf("Research: %s", topic), Action: ActionResearch,
			Args: map[string]string{"topic": topic}, Status: TaskPending})
		chainDeps = []string{id}
	} else if m := reFetch.FindStringSubmatch(prompt); len(m) == 2 {
		topic := strings.TrimSpace(m[1])
		id := nextID("fetch")
		tasks = append(tasks, Task{ID: id, Title: fmt.Sprintf("Fetch: %s", topic), Action: ActionFetch,
			Args: map[string]string{"topic": topic}, Status: TaskPending})
		chainDeps = []string{id}
	}

	if m := reSummarize.FindStringSubmatch(prompt); len(m) == 2 && len(chainDeps) > 0 {
		topic := strings.TrimSpace(m[1])
		id := nextID("summarize")
		tasks = append(tasks, Task{ID: id, Title: fmt.Sprintf("Summarize: %s", topic), Action: ActionSummarize,
			Args: map[string]string{"topic": topic}, DependsOn: chainDeps, Status: TaskPending})
		chainDeps = []string{id}
	}

	if reSave.MatchString(lower) && len(chainDeps) > 0 {
		id := nextID("save")
		tasks = append(tasks, Task{ID: id, Title: "Save findings to memory", Action: ActionSave,
			Args: map[string]string{}, DependsOn: chainDeps, Status: TaskPending})
		chainDeps = []string{id}
	}

	if len(tasks) > 0 {
		tasks = append(tasks, Task{ID: nextID("generate"), Title: "Generate response", Action: ActionGenerate,
			Args: map[string]string{}, DependsOn: chainDeps, Status: TaskPending})
		return tasks
	}

	// ── Pattern 3: comma-separated verb list ────────────────────────────────
	// e.g. "research X, summarize it, compare with Y, save"
	commaPlans := splitCommaActions(prompt)
	if len(commaPlans) >= 2 {
		return commaPlans
	}

	return nil
}

// splitCommaActions handles "verb topic, verb topic, ..." structures.
func splitCommaActions(prompt string) []Task {
	parts := strings.Split(prompt, ",")
	if len(parts) < 2 {
		return nil
	}

	actionVerbs := map[string]TaskAction{
		"research":    ActionResearch,
		"find":        ActionFetch,
		"fetch":       ActionFetch,
		"search for":  ActionFetch,
		"look up":     ActionFetch,
		"summarize":   ActionSummarize,
		"summarise":   ActionSummarize,
		"compare":     ActionCompare,
		"save":        ActionSave,
		"store":       ActionSave,
		"write":       ActionSave,
		"generate":    ActionGenerate,
	}

	var tasks []Task
	counter := 0
	var lastIDs []string

	for _, part := range parts {
		part = strings.TrimSpace(part)
		lower := strings.ToLower(part)
		matched := false
		for verb, action := range actionVerbs {
			if strings.HasPrefix(lower, verb) {
				counter++
				topic := strings.TrimSpace(part[len(verb):])
				id := fmt.Sprintf("%s_%d", string(action), counter)
				title := strings.Title(string(action))
				if topic != "" {
					title = fmt.Sprintf("%s: %s", title, topic)
				}
				deps := append([]string{}, lastIDs...)
				t := Task{ID: id, Title: title, Action: action,
					Args:      map[string]string{"topic": topic},
					DependsOn: deps,
					Status:    TaskPending}
				tasks = append(tasks, t)
				lastIDs = []string{id}
				matched = true
				break
			}
		}
		if !matched && len(tasks) > 0 {
			// unrecognised phrase — treat as a generate step
			counter++
			id := fmt.Sprintf("generate_%d", counter)
			tasks = append(tasks, Task{ID: id, Title: fmt.Sprintf("Generate: %s", part),
				Action: ActionGenerate, Args: map[string]string{},
				DependsOn: append([]string{}, lastIDs...), Status: TaskPending})
			lastIDs = []string{id}
		}
	}

	// Ensure a generate tail exists
	if len(tasks) > 0 {
		last := tasks[len(tasks)-1]
		if last.Action != ActionGenerate {
			counter++
			tasks = append(tasks, Task{
				ID: fmt.Sprintf("generate_%d", counter), Title: "Generate response",
				Action: ActionGenerate, Args: map[string]string{},
				DependsOn: []string{last.ID}, Status: TaskPending,
			})
		}
	}

	if len(tasks) < 2 {
		return nil
	}
	return tasks
}
