package pad

import (
	"context"
	"log"
	"sync"
	"time"
)

const (
	DefaultWorkerConcurrency = 4
	MaxWorkerConcurrency     = 8
	DispatchTimeout          = 3 * time.Minute
)

// WorkerPool manages a semaphore-controlled pool of goroutines.
// Hard cap: 8 concurrent workers. Default: 4.
type WorkerPool struct {
	Concurrency int
	Distiller   PADDistiller
	Blackboard  Blackboard
	sem         chan struct{}
}

// NewWorkerPool creates a pool with the given concurrency cap.
func NewWorkerPool(distiller PADDistiller, blackboard Blackboard, concurrency int) *WorkerPool {
	if concurrency < 1 {
		concurrency = DefaultWorkerConcurrency
	}
	if concurrency > MaxWorkerConcurrency {
		concurrency = MaxWorkerConcurrency
	}
	return &WorkerPool{
		Concurrency: concurrency,
		Distiller:   distiller,
		Blackboard:  blackboard,
		sem:         make(chan struct{}, concurrency),
	}
}

// DispatchAll fans out tasks in parallel, bounded by the semaphore.
// Returns all results (including errored ones) once every goroutine completes
// or the dispatch timeout fires.
func (p *WorkerPool) DispatchAll(ctx context.Context, tasks []WorkerTask) []WorkerResult {
	if len(tasks) == 0 {
		return nil
	}

	dispatchCtx, cancel := context.WithTimeout(ctx, DispatchTimeout)
	defer cancel()

	results := make([]WorkerResult, len(tasks))
	var wg sync.WaitGroup

	for i, task := range tasks {
		wg.Add(1)
		go func(idx int, t WorkerTask) {
			defer wg.Done()

			// Acquire semaphore slot
			select {
			case p.sem <- struct{}{}:
				defer func() { <-p.sem }()
			case <-dispatchCtx.Done():
				results[idx] = WorkerResult{
					TaskID: t.ID,
					Goal:   t.Goal,
					Error:  "dispatch timeout waiting for slot",
				}
				return
			}

			worker := NewWorker(p.Distiller, p.Blackboard)
			results[idx] = worker.Run(dispatchCtx, t)
		}(i, task)
	}

	// Wait with timeout awareness
	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()

	select {
	case <-done:
		log.Printf("[PAD:Pool] all %d workers done", len(tasks))
	case <-dispatchCtx.Done():
		log.Printf("[PAD:Pool] dispatch timeout — collecting partial results")
	}

	return results
}
