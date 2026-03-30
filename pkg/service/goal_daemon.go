package service

// GoalDaemon — Sovereign Goal Engine background ticker
//
// Runs on a configurable interval and advances all active GoalDAGs.
//
// Each tick:
//  1. Load all active goals from GoalStore
//  2. For each goal: GoalExecutor.Tick → finds ready nodes → PAD dispatch → advances
//  3. If goal IsComplete: GoalAcceptor.Check → mark done/failed + build final answer
//
// Env vars:
//
//	ORICLI_GOALS_ENABLED=true  — enable the daemon (default: false)
//	ORICLI_GOAL_INTERVAL=15m   — tick interval (default: 15m)

import (
	"context"
	"log"
	"os"
	"time"

	"github.com/thynaptic/oricli-go/pkg/goal"
)

// GoalDaemon orchestrates the Sovereign Goal Engine tick loop.
type GoalDaemon struct {
	Executor *goal.GoalExecutor
	Acceptor *goal.GoalAcceptor
	Store    *goal.GoalStore

	interval time.Duration
	enabled  bool

	// ManualTick triggers an immediate advance cycle.
	ManualTick chan struct{}
	stop       chan struct{}
}

// NewGoalDaemon builds a GoalDaemon from env config.
func NewGoalDaemon(executor *goal.GoalExecutor, acceptor *goal.GoalAcceptor, store *goal.GoalStore) *GoalDaemon {
	enabled := os.Getenv("ORICLI_GOALS_ENABLED") == "true"
	interval := 15 * time.Minute
	if v := os.Getenv("ORICLI_GOAL_INTERVAL"); v != "" {
		if dur, err := time.ParseDuration(v); err == nil && dur > 0 {
			interval = dur
		}
	}
	return &GoalDaemon{
		Executor:   executor,
		Acceptor:   acceptor,
		Store:      store,
		interval:   interval,
		enabled:    enabled,
		ManualTick: make(chan struct{}, 1),
		stop:       make(chan struct{}),
	}
}

// Run starts the daemon loop. Blocking — call as goroutine.
func (d *GoalDaemon) Run() {
	if !d.enabled {
		log.Println("[GoalDaemon] disabled (ORICLI_GOALS_ENABLED != true)")
		return
	}
	log.Printf("[GoalDaemon] started — interval: %v", d.interval)

	ticker := time.NewTicker(d.interval)
	defer ticker.Stop()

	// One tick immediately at boot to pick up any goals that survived a restart.
	d.Tick()

	for {
		select {
		case <-ticker.C:
			d.Tick()
		case <-d.ManualTick:
			log.Println("[GoalDaemon] manual tick triggered")
			d.Tick()
		case <-d.stop:
			log.Println("[GoalDaemon] stopped")
			return
		}
	}
}

// Stop signals the daemon loop to exit.
func (d *GoalDaemon) Stop() {
	close(d.stop)
}

// Tick advances all active goals one cycle.
func (d *GoalDaemon) Tick() {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	defer cancel()

	if d.Store == nil {
		return
	}

	active, err := d.Store.ListActive(ctx)
	if err != nil {
		log.Printf("[GoalDaemon] list active error: %v", err)
		return
	}
	if len(active) == 0 {
		return
	}

	log.Printf("[GoalDaemon] tick — %d active goals", len(active))

	for _, g := range active {
		d.advanceGoal(ctx, g)
	}
}

// advanceGoal runs one executor tick on a goal and handles completion.
func (d *GoalDaemon) advanceGoal(ctx context.Context, g *goal.GoalDAG) {
	if d.Executor == nil {
		return
	}

	advanced, err := d.Executor.Tick(ctx, g)
	if err != nil {
		log.Printf("[GoalDaemon:%s] executor error: %v", g.ID[:8], err)
	}

	if !g.IsComplete() {
		if advanced {
			log.Printf("[GoalDaemon:%s] advanced — %d nodes remaining",
				g.ID[:8], d.pendingCount(g))
		}
		return
	}

	// All nodes settled — run the acceptor
	log.Printf("[GoalDaemon:%s] all nodes complete — running acceptor", g.ID[:8])

	if d.Acceptor != nil {
		result := d.Acceptor.Check(ctx, g)
		if result.Passed {
			g.FinalAnswer = d.Acceptor.BuildFinalAnswer(ctx, g)
			g.Status = goal.StatusDone
			log.Printf("[GoalDaemon:%s] DONE — score=%.2f", g.ID[:8], result.Score)
		} else {
			g.Status = goal.StatusFailed
			g.FinalAnswer = "Goal not fully satisfied: " + result.Rationale + "\nGaps: " + result.Gaps
			log.Printf("[GoalDaemon:%s] FAILED acceptor — score=%.2f: %s", g.ID[:8], result.Score, result.Rationale)
		}
	} else {
		g.FinalAnswer = g.AccumulatedResults()
		g.Status = goal.StatusDone
	}

	if err := d.Store.Update(ctx, g); err != nil {
		log.Printf("[GoalDaemon:%s] final update error: %v", g.ID[:8], err)
	}
}

func (d *GoalDaemon) pendingCount(g *goal.GoalDAG) int {
	n := 0
	for _, node := range g.Nodes {
		if node.Status == goal.StatusPending || node.Status == goal.StatusRunning {
			n++
		}
	}
	return n
}
