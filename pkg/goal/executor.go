package goal

import (
	"context"
	"fmt"
	"log"
	"time"
)

// PADDispatcher is the interface the executor uses to run sub-goals.
// Satisfied by *service.PADService.
type PADDispatcher interface {
	Dispatch(ctx context.Context, query string, maxWorkers int) (PADSession, error)
}

// PADSession is a minimal view of the dispatch result to avoid import cycles.
type PADSession struct {
	ID        string
	Synthesis string
	Status    string
}

// SentinelChallenger is the interface for the AdversarialSentinel.
// Satisfied by *sentinel.AdversarialSentinel — defined here to avoid import cycles.
type SentinelChallenger interface {
	Challenge(ctx context.Context, query, plan string) SentinelReport
}

// SentinelReport is a minimal view of a sentinel challenge result.
type SentinelReport struct {
	Passed     bool
	Blocked    bool
	Violations []SentinelViolation
	RevisedPlan string
}

// SentinelViolation is a single flaw found by the sentinel.
type SentinelViolation struct {
	Type        string
	Description string
	Severity    string
}

// GoalExecutor drives one execution tick of a GoalDAG:
// finds ready nodes → fires PAD dispatches → stores results → advances DAG.
type GoalExecutor struct {
	PAD      PADDispatcher
	Store    *GoalStore
	Sentinel SentinelChallenger // optional — nil means sentinel checks are skipped
}

// NewGoalExecutor creates an executor.
func NewGoalExecutor(pad PADDispatcher, store *GoalStore) *GoalExecutor {
	return &GoalExecutor{PAD: pad, Store: store}
}

// Tick advances one cycle of a goal. Returns (advanced, error).
// advanced is true if at least one node was completed in this tick.
func (e *GoalExecutor) Tick(ctx context.Context, goal *GoalDAG) (bool, error) {
	if goal.Status == StatusDone || goal.Status == StatusCancelled || goal.Status == StatusFailed {
		return false, nil
	}

	ready := goal.ReadyNodes()
	if len(ready) == 0 {
		if goal.IsComplete() {
			// All nodes settled — let daemon handle acceptor check
			return false, nil
		}
		log.Printf("[GoalExecutor:%s] no ready nodes (waiting on deps)", goal.ID[:8])
		return false, nil
	}

	goal.TickCount++
	advanced := false

	for _, node := range ready {
		if err := goal.MarkRunning(node.ID); err != nil {
			log.Printf("[GoalExecutor] mark running error: %v", err)
			continue
		}
		// Persist running state immediately
		_ = e.Store.Update(ctx, goal)

		log.Printf("[GoalExecutor:%s] dispatching node %s: %.60s...", goal.ID[:8], node.ID[:8], node.Description)

		// Build context-enriched query: inject accumulated results from done nodes
		query := e.buildNodeQuery(goal, node)

		// Adversarial Sentinel pre-flight: challenge the plan before dispatching.
		if e.Sentinel != nil {
			sentinelCtx, sentinelCancel := context.WithTimeout(ctx, 30*time.Second)
			report := e.Sentinel.Challenge(sentinelCtx, goal.Objective, query)
			sentinelCancel()
			if report.Blocked {
				log.Printf("[GoalExecutor:%s] Sentinel BLOCKED node %s — %d critical violation(s)",
					goal.ID[:8], node.ID[:8], len(report.Violations))
				errMsg := "sentinel blocked: "
				for i, v := range report.Violations {
					if i > 0 {
						errMsg += "; "
					}
					errMsg += v.Description
				}
				_ = goal.FailNode(node.ID, errMsg)
				_ = e.Store.Update(ctx, goal)
				continue
			}
			// Non-blocking violations: log as warnings, use revised plan if provided
			if !report.Passed && report.RevisedPlan != "" {
				log.Printf("[GoalExecutor:%s] Sentinel WARNING on node %s — using revised plan",
					goal.ID[:8], node.ID[:8])
				query = report.RevisedPlan
			}
		}

		nodeCtx, cancel := context.WithTimeout(ctx, 5*time.Minute)
		session, err := e.PAD.Dispatch(nodeCtx, query, 3)
		cancel()

		if err != nil {
			log.Printf("[GoalExecutor:%s] node %s dispatch error: %v", goal.ID[:8], node.ID[:8], err)
			_ = goal.FailNode(node.ID, fmt.Sprintf("dispatch error: %v", err))
		} else {
			_ = goal.Advance(node.ID, session.Synthesis, session.ID)
			advanced = true
			log.Printf("[GoalExecutor:%s] node %s done (%d chars)", goal.ID[:8], node.ID[:8], len(session.Synthesis))
		}

		// Persist after each node to survive crashes
		if updateErr := e.Store.Update(ctx, goal); updateErr != nil {
			log.Printf("[GoalExecutor] store update error: %v", updateErr)
		}
	}

	return advanced, nil
}

// buildNodeQuery enriches the node description with context from already-done sibling nodes.
func (e *GoalExecutor) buildNodeQuery(goal *GoalDAG, node *SubGoal) string {
	// Collect results from the node's direct dependencies
	doneSet := make(map[string]string)
	for _, n := range goal.Nodes {
		if n.Status == StatusDone {
			doneSet[n.ID] = n.Result
		}
	}

	query := node.Description

	var priorContext string
	for _, depID := range node.DependsOn {
		if result, ok := doneSet[depID]; ok && result != "" {
			// Find the dep node for its description
			for _, n := range goal.Nodes {
				if n.ID == depID {
					priorContext += fmt.Sprintf("\n\n[Prior finding — %s]:\n%s", n.Description, result)
					break
				}
			}
		}
	}

	if priorContext != "" {
		query = fmt.Sprintf("%s\n\nPRIOR CONTEXT FROM DEPENDENCIES:%s", node.Description, priorContext)
	}

	return query
}
