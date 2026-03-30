package pad

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/google/uuid"
)

// ─────────────────────────────────────────────────────────────────────────────
// Interfaces
// ─────────────────────────────────────────────────────────────────────────────

// PADDistiller generates text via Ollama. Satisfied by *service.GenerationService.
type PADDistiller interface {
	Generate(prompt string, options map[string]interface{}) (map[string]interface{}, error)
}

// Blackboard is the shared memory workers read/write during a dispatch.
// Satisfied by *bus.SwarmBus.
type Blackboard interface {
	SetState(key string, val interface{})
	GetState(key string) interface{}
}

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

// Strategy hints what execution mode the decomposer recommends.
type Strategy string

const (
	StrategyParallel   Strategy = "parallel"
	StrategySequential Strategy = "sequential"
	StrategyHybrid     Strategy = "hybrid"
	StrategySingle     Strategy = "single"
)

// WorkerTask is what a single worker is assigned.
type WorkerTask struct {
	ID       string   `json:"id"`
	Goal     string   `json:"goal"`
	Tools    []string `json:"tools"`
	Priority int      `json:"priority"`
}

// DecompositionResult is the full output of TaskDecomposer.Decompose.
type DecompositionResult struct {
	Strategy     Strategy     `json:"strategy"`
	Tasks        []WorkerTask `json:"tasks"`
	Rationale    string       `json:"rationale"`
	DecomposedAt time.Time    `json:"decomposed_at"`
}

// ─────────────────────────────────────────────────────────────────────────────
// TaskDecomposer
// ─────────────────────────────────────────────────────────────────────────────

// TaskDecomposer uses an LLM to break a complex query into parallel sub-tasks.
type TaskDecomposer struct {
	Distiller  PADDistiller
	MaxWorkers int
}

// NewTaskDecomposer creates a decomposer with a hard cap on task count.
func NewTaskDecomposer(distiller PADDistiller, maxWorkers int) *TaskDecomposer {
	if maxWorkers < 1 {
		maxWorkers = 4
	}
	if maxWorkers > 8 {
		maxWorkers = 8
	}
	return &TaskDecomposer{Distiller: distiller, MaxWorkers: maxWorkers}
}

// Decompose breaks a query into N ≤ maxWorkers focused sub-tasks.
func (d *TaskDecomposer) Decompose(ctx context.Context, query string, maxWorkers int) (DecompositionResult, error) {
	if maxWorkers < 1 || maxWorkers > d.MaxWorkers {
		maxWorkers = d.MaxWorkers
	}

	result := DecompositionResult{DecomposedAt: time.Now().UTC()}

	if d.Distiller == nil {
		result.Strategy = StrategySingle
		result.Tasks = []WorkerTask{{ID: uuid.New().String(), Goal: query}}
		result.Rationale = "no distiller — single-task fallback"
		return result, nil
	}

	prompt := fmt.Sprintf(`You are a task decomposition engine for Oricli, a sovereign AI.

QUERY: "%s"
MAX PARALLEL WORKERS: %d

Decide whether this query benefits from parallel investigation.
- single: simple/direct query — one worker is enough
- parallel: broad research, multiple independent angles worth pursuing simultaneously

Decompose into at most %d focused sub-tasks. Each sub-task must be:
- Self-contained (worker has no context from siblings)
- Specific and answerable independently
- Non-overlapping with sibling tasks

Respond ONLY with valid JSON (no markdown, no explanation):
{
  "strategy": "parallel|single",
  "rationale": "one sentence why",
  "tasks": [
    {"goal": "specific sub-question or sub-task", "tools": []}
  ]
}`, query, maxWorkers, maxWorkers)

	raw, err := d.Distiller.Generate(prompt, map[string]interface{}{
		"temperature": 0.2,
		"num_predict": 512,
	})
	if err != nil {
		log.Printf("[PAD:Decomposer] LLM error, single-task fallback: %v", err)
		result.Strategy = StrategySingle
		result.Tasks = []WorkerTask{{ID: uuid.New().String(), Goal: query}}
		result.Rationale = "LLM unavailable — single-task fallback"
		return result, nil
	}

	text := extractPADText(raw)
	parsed, err := parseDecomposition(text)
	if err != nil {
		log.Printf("[PAD:Decomposer] parse error (%v), single-task fallback", err)
		result.Strategy = StrategySingle
		result.Tasks = []WorkerTask{{ID: uuid.New().String(), Goal: query}}
		result.Rationale = "parse error — single-task fallback"
		return result, nil
	}

	if len(parsed.Tasks) > maxWorkers {
		parsed.Tasks = parsed.Tasks[:maxWorkers]
	}
	for i := range parsed.Tasks {
		parsed.Tasks[i].ID = uuid.New().String()
	}
	if len(parsed.Tasks) == 1 {
		parsed.Strategy = StrategySingle
	}

	result.Strategy = parsed.Strategy
	result.Tasks = parsed.Tasks
	result.Rationale = parsed.Rationale
	return result, nil
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

type rawDecomposition struct {
	Strategy  string `json:"strategy"`
	Rationale string `json:"rationale"`
	Tasks     []struct {
		Goal  string   `json:"goal"`
		Tools []string `json:"tools"`
	} `json:"tasks"`
}

func parseDecomposition(text string) (DecompositionResult, error) {
	text = strings.TrimSpace(text)
	if i := strings.Index(text, "{"); i > 0 {
		text = text[i:]
	}
	if i := strings.LastIndex(text, "}"); i >= 0 && i < len(text)-1 {
		text = text[:i+1]
	}

	var raw rawDecomposition
	if err := json.Unmarshal([]byte(text), &raw); err != nil {
		return DecompositionResult{}, fmt.Errorf("unmarshal: %w", err)
	}

	strategy := Strategy(strings.ToLower(raw.Strategy))
	switch strategy {
	case StrategyParallel, StrategySequential, StrategyHybrid, StrategySingle:
	default:
		strategy = StrategySingle
	}

	tasks := make([]WorkerTask, 0, len(raw.Tasks))
	for _, t := range raw.Tasks {
		if strings.TrimSpace(t.Goal) == "" {
			continue
		}
		tasks = append(tasks, WorkerTask{Goal: t.Goal, Tools: t.Tools})
	}

	return DecompositionResult{
		Strategy:  strategy,
		Rationale: raw.Rationale,
		Tasks:     tasks,
	}, nil
}

func extractPADText(raw map[string]interface{}) string {
	if raw == nil {
		return ""
	}
	for _, key := range []string{"response", "content", "text"} {
		if v, ok := raw[key]; ok {
			if s, ok := v.(string); ok {
				return s
			}
		}
	}
	if msg, ok := raw["message"].(map[string]interface{}); ok {
		if c, ok := msg["content"].(string); ok {
			return c
		}
	}
	return ""
}
