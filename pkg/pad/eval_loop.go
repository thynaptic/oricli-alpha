package pad

import (
	"context"
	"log"
)

// ─────────────────────────────────────────────────────────────────────────────
// EvaluationLoop
// ─────────────────────────────────────────────────────────────────────────────

const maxCriticRounds = 2

// EvaluationLoop wraps a WorkerPool + Critic for multi-round, self-correcting
// PAD execution. Only failing workers are re-dispatched each round.
type EvaluationLoop struct {
	Pool   *WorkerPool
	Synth  *Synthesizer
	Critic *Critic
}

// NewEvaluationLoop creates the loop wired to an existing pool, synthesizer, and critic.
func NewEvaluationLoop(pool *WorkerPool, synth *Synthesizer, critic *Critic) *EvaluationLoop {
	return &EvaluationLoop{
		Pool:   pool,
		Synth:  synth,
		Critic: critic,
	}
}

// EvalResult is the final output of a critiqued dispatch.
type EvalResult struct {
	Synthesis  string
	AllResults []WorkerResult
	LastReport CriticReport
	RoundsUsed int
}

// Run dispatches the tasks, critiques results, and surgically re-dispatches
// failing workers up to maxCriticRounds times.
//
// tasks: the full set of WorkerTasks from the decomposer.
// query: original user query (used by the critic for context).
func (el *EvaluationLoop) Run(ctx context.Context, tasks []WorkerTask, query string) EvalResult {
	var allGood []WorkerResult   // accumulates passing workers across rounds
	remaining := tasks
	var lastReport CriticReport

	for round := 1; round <= maxCriticRounds; round++ {
		if len(remaining) == 0 {
			break
		}

		log.Printf("[EvalLoop] round %d — dispatching %d worker(s)", round, len(remaining))

		// Inject critic hint into prompts for retry rounds
		if round > 1 && len(lastReport.WorkerScores) > 0 {
			remaining = injectHints(remaining, lastReport.WorkerScores)
		}

		roundResults := el.Pool.DispatchAll(ctx, remaining)

		// Evaluate this round's results
		report := el.Critic.Evaluate(ctx, query, roundResults, round)
		lastReport = report

		// Partition: passing → allGood, failing → rebuild remaining tasks
		var failedIDs []string
		for _, ws := range report.WorkerScores {
			if !ws.Pass {
				failedIDs = append(failedIDs, ws.TaskID)
			}
		}
		failSet := make(map[string]bool, len(failedIDs))
		for _, id := range failedIDs {
			failSet[id] = true
		}

		for _, r := range roundResults {
			if !failSet[r.TaskID] {
				allGood = append(allGood, r)
			}
		}

		// Build next round's task list from original tasks that matched failed IDs
		nextTasks := make([]WorkerTask, 0)
		for _, t := range tasks {
			if failSet[t.ID] {
				nextTasks = append(nextTasks, t)
			}
		}
		remaining = nextTasks

		if report.OverallPass {
			// All workers passed — no retry needed
			allGood = append(allGood, roundResults...)
			allGood = deduplicate(allGood)
			break
		}

		if round == maxCriticRounds {
			// Final round — accept remaining results regardless of score
			log.Printf("[EvalLoop] max rounds reached — accepting %d remaining result(s) as-is", len(roundResults))
			for _, r := range roundResults {
				if failSet[r.TaskID] {
					allGood = append(allGood, r)
				}
			}
		}
	}

	synthesis := el.Synth.Merge(ctx, query, allGood)
	return EvalResult{
		Synthesis:  synthesis,
		AllResults: allGood,
		LastReport: lastReport,
		RoundsUsed: lastReport.Round,
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

// injectHints appends the critic's weakness hint to the prompt of each failing task.
func injectHints(tasks []WorkerTask, scores []WorkerScore) []WorkerTask {
	hintMap := make(map[string]string, len(scores))
	for _, ws := range scores {
		if !ws.Pass && ws.WeaknessHint != "" {
			hintMap[ws.TaskID] = ws.WeaknessHint
		}
	}
	result := make([]WorkerTask, len(tasks))
	copy(result, tasks)
	for i, t := range result {
		if hint, ok := hintMap[t.ID]; ok {
			result[i].Goal = t.Goal + "\n\n[Critic feedback — address this on retry]: " + hint
		}
	}
	return result
}

// deduplicate removes duplicate results keeping last occurrence per TaskID.
func deduplicate(results []WorkerResult) []WorkerResult {
	seen := make(map[string]int, len(results))
	out := make([]WorkerResult, 0, len(results))
	for _, r := range results {
		if idx, ok := seen[r.TaskID]; ok {
			out[idx] = r // overwrite with later result
		} else {
			seen[r.TaskID] = len(out)
			out = append(out, r)
		}
	}
	return out
}
