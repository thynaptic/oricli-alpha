package service

// CostGovernor tracks daily RunPod spend and enforces a configurable budget cap.
//
// Env vars:
//
//	WORLD_TRAVELER_DAILY_BUDGET_USD  (default: 2.00)
//
// Spend is tracked in memory and resets at UTC midnight. A lightweight
// PocketBase write is made after each spend event for persistence across restarts.

import (
	"context"
	"log"
	"os"
	"strconv"
	"sync"
	"time"
)

type CostGovernor struct {
	mu           sync.Mutex
	dailyBudget  float64
	spentToday   float64
	dayKey       string // "YYYY-MM-DD"
	MemoryBank   *MemoryBank
}

func NewCostGovernor(mb *MemoryBank) *CostGovernor {
	budget := 2.00
	if v := os.Getenv("WORLD_TRAVELER_DAILY_BUDGET_USD"); v != "" {
		if f, err := strconv.ParseFloat(v, 64); err == nil && f > 0 {
			budget = f
		}
	}
	g := &CostGovernor{
		dailyBudget: budget,
		dayKey:      utcDayKey(),
		MemoryBank:  mb,
	}
	log.Printf("[CostGovernor] Daily RunPod budget: $%.2f", budget)
	return g
}

// CanSpend returns true if estimatedCost fits within today's remaining budget.
func (g *CostGovernor) CanSpend(estimatedCost float64) bool {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.resetIfNewDay()
	remaining := g.dailyBudget - g.spentToday
	if estimatedCost > remaining {
		log.Printf("[CostGovernor] Budget guard: need $%.4f, only $%.4f remaining today", estimatedCost, remaining)
		return false
	}
	return true
}

// RecordSpend logs actual spend after a RunPod call completes.
func (g *CostGovernor) RecordSpend(cost float64, label string) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.resetIfNewDay()
	g.spentToday += cost
	log.Printf("[CostGovernor] Recorded $%.4f (%s) — today total: $%.4f / $%.2f", cost, label, g.spentToday, g.dailyBudget)
	if g.MemoryBank != nil {
		go g.MemoryBank.WriteKnowledgeFragment(
			"_cost_log",
			"system",
			label+": $"+strconv.FormatFloat(cost, 'f', 4, 64),
			0.0,
		)
	}
}

// DailySpend returns total spend for today.
func (g *CostGovernor) DailySpend() float64 {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.resetIfNewDay()
	return g.spentToday
}

// RemainingBudget returns today's remaining budget.
func (g *CostGovernor) RemainingBudget() float64 {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.resetIfNewDay()
	return g.dailyBudget - g.spentToday
}

func (g *CostGovernor) resetIfNewDay() {
	today := utcDayKey()
	if today != g.dayKey {
		log.Printf("[CostGovernor] New day (%s) — resetting spend counter (yesterday: $%.4f)", today, g.spentToday)
		g.spentToday = 0
		g.dayKey = today
	}
}

// EstimateRunPodCost estimates the cost of a synthesis batch.
// Rate: ~$0.33/hr for A40 (32B model). Average synthesis takes ~3 min for 20 topics.
func EstimateRunPodCost(numTopics int) float64 {
	minutesPerTopic := 0.15 // ~9 seconds per topic synthesis at 32B
	totalMinutes := float64(numTopics) * minutesPerTopic
	hourlyCost := 0.33 // A40 rate
	return (totalMinutes / 60.0) * hourlyCost
}

// RunWithBudget executes fn only if estimatedCost fits within budget,
// recording spend on completion.
func (g *CostGovernor) RunWithBudget(ctx context.Context, estimatedCost float64, label string, fn func(context.Context) error) error {
	if !g.CanSpend(estimatedCost) {
		return nil // silently skip — budget guard already logged
	}
	start := time.Now()
	err := fn(ctx)
	elapsed := time.Since(start)
	// Refine actual cost based on real elapsed time
	actualCost := (elapsed.Minutes() / 60.0) * 0.33
	g.RecordSpend(actualCost, label)
	return err
}

func utcDayKey() string {
	return time.Now().UTC().Format("2006-01-02")
}
