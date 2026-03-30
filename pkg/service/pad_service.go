package service

// PADService orchestrates the full Parallel Agent Dispatch pipeline:
//
//	Decompose → WorkerPool.DispatchAll → Synthesizer.Merge → SessionStore.Save
//
// Env:
//
//	ORICLI_PAD_ENABLED=true   — enables the service (default: false)
//	ORICLI_PAD_MAX_WORKERS=4  — default worker concurrency (default: 4, max: 8)

import (
	"context"
	"fmt"
	"log"
	"os"
	"strconv"
	"sync/atomic"
	"time"

	"github.com/google/uuid"
	"github.com/thynaptic/oricli-go/pkg/pad"
)

// PADStats tracks dispatch activity.
type PADStats struct {
	TotalDispatches int64 `json:"total_dispatches"`
	SinglePath      int64 `json:"single_path"`    // queries that didn't fan out
	ParallelPath    int64 `json:"parallel_path"`  // queries that fanned out
	WorkersSpawned  int64 `json:"workers_spawned"`
	WorkerErrors    int64 `json:"worker_errors"`
	SynthesisRuns   int64 `json:"synthesis_runs"`
	CritiqueRuns    int64 `json:"critique_runs"`
	RetryRounds     int64 `json:"retry_rounds"`
}

// PADService is the sovereign parallel dispatch orchestrator.
type PADService struct {
	Decomposer  *pad.TaskDecomposer
	Pool        *pad.WorkerPool
	Synthesizer *pad.Synthesizer
	Sessions    *pad.SessionStore
	Blackboard  pad.Blackboard
	Critic      *pad.Critic
	EvalLoop    *pad.EvaluationLoop

	Enabled    bool
	MaxWorkers int
	stats      PADStats
}

// NewPADService wires all PAD components together.
func NewPADService(
	decomposer *pad.TaskDecomposer,
	pool *pad.WorkerPool,
	synthesizer *pad.Synthesizer,
	sessions *pad.SessionStore,
	blackboard pad.Blackboard,
) *PADService {
	enabled := os.Getenv("ORICLI_PAD_ENABLED") == "true"
	maxWorkers := pad.DefaultWorkerConcurrency
	if v := os.Getenv("ORICLI_PAD_MAX_WORKERS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			maxWorkers = n
		}
	}
	if maxWorkers > pad.MaxWorkerConcurrency {
		maxWorkers = pad.MaxWorkerConcurrency
	}

	return &PADService{
		Decomposer:  decomposer,
		Pool:        pool,
		Synthesizer: synthesizer,
		Sessions:    sessions,
		Blackboard:  blackboard,
		Enabled:     enabled,
		MaxWorkers:  maxWorkers,
	}
}

// EnableCritique wires the Critic and EvaluationLoop into an existing PADService.
// Called from the boot block after NewPADService.
func (p *PADService) EnableCritique(distiller pad.PADDistiller) {
	p.Critic = pad.NewCritic(distiller)
	p.EvalLoop = pad.NewEvaluationLoop(p.Pool, p.Synthesizer, p.Critic)
	log.Printf("[PAD] Critic + EvaluationLoop wired — threshold=%.2f max_rounds=2", pad.CriticThreshold)
}

// Dispatch is the main entry point. It decomposes the query, fans out to workers,
// synthesizes results, persists the session, and returns it.
func (p *PADService) Dispatch(ctx context.Context, query string, maxWorkers int) (*pad.DispatchSession, error) {
	if !p.Enabled {
		return nil, fmt.Errorf("PAD disabled — set ORICLI_PAD_ENABLED=true")
	}
	if maxWorkers < 1 || maxWorkers > pad.MaxWorkerConcurrency {
		maxWorkers = p.MaxWorkers
	}

	atomic.AddInt64(&p.stats.TotalDispatches, 1)

	session := &pad.DispatchSession{
		ID:        uuid.New().String(),
		Query:     query,
		Status:    pad.StatusRunning,
		StartedAt: time.Now().UTC(),
	}

	// ── Stage 1: Decompose ────────────────────────────────────────────────────
	var decomp pad.DecompositionResult
	var err error
	if p.Decomposer != nil {
		decomp, err = p.Decomposer.Decompose(ctx, query, maxWorkers)
		if err != nil {
			log.Printf("[PAD] decompose error: %v — single-task fallback", err)
		}
	}
	if len(decomp.Tasks) == 0 {
		decomp = pad.DecompositionResult{
			Strategy:  pad.StrategySingle,
			Tasks:     []pad.WorkerTask{{ID: uuid.New().String(), Goal: query}},
			Rationale: "fallback single task",
		}
	}

	session.Strategy = decomp.Strategy
	session.Tasks = decomp.Tasks
	session.WorkerCount = len(decomp.Tasks)

	if decomp.Strategy == pad.StrategySingle {
		atomic.AddInt64(&p.stats.SinglePath, 1)
	} else {
		atomic.AddInt64(&p.stats.ParallelPath, 1)
	}

	atomic.AddInt64(&p.stats.WorkersSpawned, int64(len(decomp.Tasks)))
	log.Printf("[PAD] session %s — strategy=%s workers=%d", session.ID[:8], decomp.Strategy, len(decomp.Tasks))

	// ── Stage 2: Dispatch ─────────────────────────────────────────────────────
	// Use a fresh context for the pool — independent of the HTTP request context
	// so workers are not constrained by the client connection deadline.
	poolCtx, poolCancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer poolCancel()

	var results []pad.WorkerResult
	if p.Pool != nil {
		results = p.Pool.DispatchAll(poolCtx, decomp.Tasks)
	} else {
		// No pool — single inline execution
		if len(decomp.Tasks) > 0 {
			w := pad.NewWorker(nil, p.Blackboard)
			results = []pad.WorkerResult{w.Run(poolCtx, decomp.Tasks[0])}
		}
	}

	// Count errors
	for _, r := range results {
		if r.Error != "" {
			atomic.AddInt64(&p.stats.WorkerErrors, 1)
		}
	}
	session.Results = results

	// ── Stage 3: Synthesize ───────────────────────────────────────────────────
	var synthesis string
	if p.Synthesizer != nil {
		atomic.AddInt64(&p.stats.SynthesisRuns, 1)
		synthesis = p.Synthesizer.Merge(ctx, query, results)
	} else {
		// No synthesizer — concatenate outputs
		for _, r := range results {
			if r.Error == "" {
				synthesis += r.Output + "\n\n"
			}
		}
	}
	session.Synthesis = synthesis
	session.Status = pad.StatusDone
	session.CompletedAt = time.Now().UTC()
	session.DurationMS = session.CompletedAt.Sub(session.StartedAt).Milliseconds()

	// ── Stage 4: Persist ──────────────────────────────────────────────────────
	if p.Sessions != nil {
		if err := p.Sessions.Save(ctx, session); err != nil {
			log.Printf("[PAD] session save error: %v", err)
		}
	}

	log.Printf("[PAD] session %s complete — %dms, %d workers, synthesis: %d chars",
		session.ID[:8], session.DurationMS, session.WorkerCount, len(synthesis))
	return session, nil
}

// Stats returns a snapshot of dispatch activity.
func (p *PADService) Stats() PADStats {
	return PADStats{
		TotalDispatches: atomic.LoadInt64(&p.stats.TotalDispatches),
		SinglePath:      atomic.LoadInt64(&p.stats.SinglePath),
		ParallelPath:    atomic.LoadInt64(&p.stats.ParallelPath),
		WorkersSpawned:  atomic.LoadInt64(&p.stats.WorkersSpawned),
		WorkerErrors:    atomic.LoadInt64(&p.stats.WorkerErrors),
		SynthesisRuns:   atomic.LoadInt64(&p.stats.SynthesisRuns),
		CritiqueRuns:    atomic.LoadInt64(&p.stats.CritiqueRuns),
		RetryRounds:     atomic.LoadInt64(&p.stats.RetryRounds),
	}
}

// DispatchWithCritique runs Dispatch + Critic evaluation loop.
// Falls back to regular Dispatch if EvalLoop is not wired.
func (p *PADService) DispatchWithCritique(ctx context.Context, query string, maxWorkers int) (*pad.DispatchSession, *pad.CriticReport, error) {
	if p.EvalLoop == nil {
		// Graceful fallback
		session, err := p.Dispatch(ctx, query, maxWorkers)
		return session, nil, err
	}

	if !p.Enabled {
		return nil, nil, fmt.Errorf("PAD disabled — set ORICLI_PAD_ENABLED=true")
	}
	if maxWorkers < 1 || maxWorkers > pad.MaxWorkerConcurrency {
		maxWorkers = p.MaxWorkers
	}

	atomic.AddInt64(&p.stats.TotalDispatches, 1)
	atomic.AddInt64(&p.stats.CritiqueRuns, 1)

	session := &pad.DispatchSession{
		ID:        uuid.New().String(),
		Query:     query,
		Status:    pad.StatusRunning,
		StartedAt: time.Now().UTC(),
	}

	// ── Stage 1: Decompose ────────────────────────────────────────────────────
	var decomp pad.DecompositionResult
	var err error
	if p.Decomposer != nil {
		decomp, err = p.Decomposer.Decompose(ctx, query, maxWorkers)
		if err != nil {
			log.Printf("[PAD+Critic] decompose error: %v — single-task fallback", err)
		}
	}
	if len(decomp.Tasks) == 0 {
		decomp = pad.DecompositionResult{
			Strategy:  pad.StrategySingle,
			Tasks:     []pad.WorkerTask{{ID: uuid.New().String(), Goal: query}},
			Rationale: "fallback single task",
		}
	}

	session.Strategy = decomp.Strategy
	session.Tasks = decomp.Tasks
	session.WorkerCount = len(decomp.Tasks)

	if decomp.Strategy == pad.StrategySingle {
		atomic.AddInt64(&p.stats.SinglePath, 1)
	} else {
		atomic.AddInt64(&p.stats.ParallelPath, 1)
	}
	atomic.AddInt64(&p.stats.WorkersSpawned, int64(len(decomp.Tasks)))

	// ── Stage 2: EvaluationLoop (Dispatch + Critique + Retry) ─────────────────
	poolCtx, poolCancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer poolCancel()

	evalResult := p.EvalLoop.Run(poolCtx, decomp.Tasks, query)

	atomic.AddInt64(&p.stats.RetryRounds, int64(evalResult.RoundsUsed-1))
	atomic.AddInt64(&p.stats.SynthesisRuns, 1)

	for _, r := range evalResult.AllResults {
		if r.Error != "" {
			atomic.AddInt64(&p.stats.WorkerErrors, 1)
		}
	}

	session.Results = evalResult.AllResults
	session.Synthesis = evalResult.Synthesis
	session.Status = pad.StatusDone
	session.CompletedAt = time.Now().UTC()
	session.DurationMS = session.CompletedAt.Sub(session.StartedAt).Milliseconds()

	if p.Sessions != nil {
		if err := p.Sessions.Save(ctx, session); err != nil {
			log.Printf("[PAD+Critic] session save error: %v", err)
		}
	}

	log.Printf("[PAD+Critic] session %s — rounds=%d pass=%v workers=%d %dms",
		session.ID[:8], evalResult.RoundsUsed, evalResult.LastReport.OverallPass,
		session.WorkerCount, session.DurationMS)

	report := evalResult.LastReport
	return session, &report, nil
}
