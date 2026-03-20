package cognition

import (
	"context"
	"fmt"
	"math"
	"runtime"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// workerState is the shared mutable state for a parallel MCTS search.
// All fields that are read/written by multiple workers are either accessed
// under mu or are atomic; the remainder are written only before workers
// start and read-only during the search.
type workerState struct {
	mu       sync.RWMutex // write: expand, virtual-loss, backprop; read: future traversal-only paths
	root     *ThoughtNode
	cfg      MCTSConfig
	started  time.Time

	// Atomic counters — updated by workers without holding mu.
	iterationsRun int64
	expandedNodes int64
	prunedNodes   int64
	valueNetHits  int64
	activeEvals   int64 // workers currently evaluating (no lock held)

	// bestAnswer / bestScore — updated under mu (write lock).
	bestAnswer string
	bestScore  float64
}

// runWorker runs a continuous select → evaluate → backpropagate loop until the
// iteration budget is exhausted or ctx is cancelled.
//
// Each iteration:
//  1. Acquire write lock → select leaf (possibly expanding) → apply virtual loss → release.
//  2. Evaluate the leaf (no lock held — this is the slow LLM step).
//  3. Acquire write lock → backpropagate + update best → release.
//  4. Atomically consume one iteration from the budget.
//
// When selectAndMaybeExpand returns nil because all paths are temporarily
// blocked by in-flight evaluations (activeEvals > 0), the worker yields and
// retries without consuming budget. When nil is returned and no other workers
// are evaluating (activeEvals == 0), the tree is permanently exhausted.
func (e *MCTSEngine) runWorker(ctx context.Context, ws *workerState) {
	for {
		// Check budget atomically before taking the lock.
		remaining := ws.cfg.Iterations - int(atomic.LoadInt64(&ws.iterationsRun))
		if remaining <= 0 || ctx.Err() != nil {
			return
		}

		// ── 1. Select ────────────────────────────────────────────────────────
		ws.mu.Lock()
		node, expanded := e.selectAndMaybeExpand(ctx, ws.root, ws.cfg, nil)
		if node == nil {
			ws.mu.Unlock()
			// Distinguish permanent exhaustion from temporary blocking.
			if atomic.LoadInt64(&ws.activeEvals) == 0 {
				return // tree permanently exhausted; no one is evaluating
			}
			// Other workers are in-flight; yield and retry.
			runtime.Gosched()
			continue
		}
		if expanded {
			atomic.AddInt64(&ws.expandedNodes, 1)
		}
		vl := int(math.Ceil(maxFloatLocal(ws.cfg.VirtualLoss, 1.0)))
		node.VirtualVisits += vl
		ws.mu.Unlock()

		// ── 2. Evaluate (no lock) ────────────────────────────────────────────
		atomic.AddInt64(&ws.activeEvals, 1)
		evalCtx := ctx
		cancel := func() {}
		if ws.cfg.EvalTimeout > 0 {
			evalCtx, cancel = context.WithTimeout(ctx, ws.cfg.EvalTimeout)
		}
		r := e.evaluateNode(evalCtx, node, ws.cfg)
		cancel()
		atomic.AddInt64(&ws.activeEvals, -1)

		// ── 3. Backpropagate ─────────────────────────────────────────────────
		ws.mu.Lock()
		if node.VirtualVisits > 0 {
			node.VirtualVisits--
		}
		if r.err != nil {
			node.LastEvalErr = strings.TrimSpace(r.err.Error())
			neutral := 0.5
			if node.Parent != nil && node.Parent.Visits > 0 {
				neutral = node.Parent.AverageValue()
			}
			e.backpropagate(node, neutral)
		} else {
			node.Score = r.score
			node.Confidence = r.confidence
			if r.terminal {
				node.Terminal = true
			}
			if r.vnHit {
				atomic.AddInt64(&ws.valueNetHits, 1)
			}
			if r.prior > 0 {
				node.Prior = clamp01Local(r.prior)
			}
			if r.pruned {
				if !node.Pruned {
					atomic.AddInt64(&ws.prunedNodes, 1)
				}
				node.Pruned = true
				node.PruneReason = fmt.Sprintf("kill-switch: branch score %.2f < %.2f", r.score, ws.cfg.PruneThreshold)
			}
			e.backpropagate(node, r.score)
			candidate := strings.TrimSpace(r.candidate)
			if candidate == "" {
				candidate = strings.TrimSpace(node.Answer)
			}
			if r.score > ws.bestScore && candidate != "" {
				ws.bestScore = r.score
				ws.bestAnswer = candidate
			}
		}
		ws.mu.Unlock()

		atomic.AddInt64(&ws.iterationsRun, 1)
	}
}

// runParallelSearch executes the MCTS search using a worker pool. Called by
// SearchV2 when MaxConcurrency > 1 (and Deterministic is false).
//
// Returns (bestAnswer, bestScore, iterationsRun, expandedNodes, prunedNodes).
func (e *MCTSEngine) runParallelSearch(ctx context.Context, cfg MCTSConfig, root *ThoughtNode) (
	bestAnswer string, bestScore float64,
	iters, expanded, pruned int,
) {
	// Auto-enable virtual loss when running parallel workers to prevent multiple
	// workers selecting the same unvisited leaf.
	if cfg.VirtualLoss <= 0 {
		cfg.VirtualLoss = 1.0
	}

	ws := &workerState{
		root:       root,
		cfg:        cfg,
		started:    time.Now(),
		bestAnswer: strings.TrimSpace(root.Answer),
	}

	var wg sync.WaitGroup
	for i := 0; i < cfg.MaxConcurrency; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			e.runWorker(ctx, ws)
		}()
	}
	wg.Wait()

	ws.mu.RLock()
	ba, bs := ws.bestAnswer, ws.bestScore
	ws.mu.RUnlock()

	return ba, bs,
		int(atomic.LoadInt64(&ws.iterationsRun)),
		int(atomic.LoadInt64(&ws.expandedNodes)),
		int(atomic.LoadInt64(&ws.prunedNodes))
}
