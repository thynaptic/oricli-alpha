package cognition

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/bus"
)

// --- Pillar 16: Self-Chaining Execution (DAG Runner) ---
// Ported from Aurora's SelfChainingExecutor.swift.
// Implements parallel/sequential module orchestration with dependency tracking.

type ModuleStep struct {
	ID           string                 `json:"id"`
	ModuleName   string                 `json:"module_name"`
	Dependencies []string               `json:"dependencies"`
	Params       map[string]interface{} `json:"params"`
	Result       string                 `json:"result,omitempty"`
	Success      bool                   `json:"success"`
}

type ChainedReasoning struct {
	ID      string       `json:"id"`
	Steps   []ModuleStep `json:"steps"`
	Context string       `json:"context"`
}

type ChainingExecutor struct {
	Bus *bus.SwarmBus
}

func NewChainingExecutor(b *bus.SwarmBus) *ChainingExecutor {
	return &ChainingExecutor{Bus: b}
}

// ExecuteChain runs a reasoning DAG using goroutines for parallel branches.
func (e *ChainingExecutor) ExecuteChain(ctx context.Context, chain *ChainedReasoning) error {
	log.Printf("[ChainingExecutor] Executing reasoning chain %s with %d steps", chain.ID, len(chain.Steps))

	// 1. Build adjacency list and in-degree map for topological sort
	adj := make(map[string][]string)
	inDegree := make(map[string]int)
	stepsByID := make(map[string]*ModuleStep)

	for i := range chain.Steps {
		step := &chain.Steps[i]
		stepsByID[step.ID] = step
		inDegree[step.ID] = len(step.Dependencies)
		for _, dep := range step.Dependencies {
			adj[dep] = append(adj[dep], step.ID)
		}
	}

	// 2. Multi-threaded execution loop
	completedCount := 0
	mu := sync.Mutex{}
	cond := sync.NewCond(&mu)

	for completedCount < len(chain.Steps) {
		mu.Lock()
		
		// Find ready steps (in-degree == 0 and not yet executed)
		var readySteps []*ModuleStep
		for i := range chain.Steps {
			step := &chain.Steps[i]
			if inDegree[step.ID] == 0 && !step.Success && step.Result == "" {
				readySteps = append(readySteps, step)
				inDegree[step.ID] = -1 // Mark as "in progress"
			}
		}
		mu.Unlock()

		if len(readySteps) == 0 {
			// Wait for a step to complete
			mu.Lock()
			cond.Wait()
			mu.Unlock()
			continue
		}

		// Execute ready steps in parallel
		var wg sync.WaitGroup
		for _, step := range readySteps {
			wg.Add(1)
			go func(s *ModuleStep) {
				defer wg.Done()
				
				// Execute via Swarm Bus (Simulated for ported logic)
				start := time.Now()
				time.Sleep(10 * time.Millisecond) // Simulated execution delay
				res := "Simulated success for " + s.ModuleName
				var err error = nil
				duration := time.Since(start)

				mu.Lock()
				if err != nil {
					s.Success = false
					s.Result = fmt.Sprintf("Error: %v", err)
				} else {
					s.Success = true
					s.Result = fmt.Sprintf("%v", res)
				}

				// Update dependents
				for _, dependentID := range adj[s.ID] {
					inDegree[dependentID]--
				}
				completedCount++
				
				log.Printf("[ChainingExecutor] Step %s (%s) completed in %v", s.ID, s.ModuleName, duration)
				cond.Broadcast()
				mu.Unlock()
			}(step)
		}
		wg.Wait()
	}

	return nil
}

// AggregateResult flattens the chain results for final synthesis.
func (chain *ChainedReasoning) AggregateResult() string {
	var aggregated string
	for _, s := range chain.Steps {
		if s.Success {
			aggregated += fmt.Sprintf("### Module: %s\n%s\n\n", s.ModuleName, s.Result)
		}
	}
	return aggregated
}
