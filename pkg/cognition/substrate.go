package cognition

import (
	"fmt"
	"log"
	"runtime"
	"sync"

	"github.com/shirou/gopsutil/v3/mem"
)

// --- Pillar 21: Substrate Awareness (Onboarding) ---
// Ported from Aurora's MavaiaOnboardingService.swift.
// Automatically detects hardware constraints and scales reasoning tiers.

type ResourceTier string

const (
	TierEdge     ResourceTier = "edge"     // Low power (< 8GB RAM)
	TierStandard ResourceTier = "standard" // Moderate (8-32GB RAM)
	TierServer   ResourceTier = "server"   // High power (> 32GB RAM)
)

type SubstrateSpecs struct {
	TotalRAM     uint64
	AvailableRAM uint64
	CPUCores     int
	Tier         ResourceTier
}

type SubstrateEngine struct {
	Specs SubstrateSpecs
	mu    sync.RWMutex
}

func NewSubstrateEngine() *SubstrateEngine {
	e := &SubstrateEngine{}
	e.RefreshSpecs()
	return e
}

// RefreshSpecs queries the OS for current hardware capabilities.
func (e *SubstrateEngine) RefreshSpecs() {
	e.mu.Lock()
	defer e.mu.Unlock()

	// 1. Detect RAM
	v, err := mem.VirtualMemory()
	if err != nil {
		log.Printf("[SubstrateEngine] Warning: Failed to detect RAM: %v", err)
		e.Specs.TotalRAM = 8 * 1024 * 1024 * 1024 // Fallback 8GB
	} else {
		e.Specs.TotalRAM = v.Total
		e.Specs.AvailableRAM = v.Available
	}

	// 2. Detect CPU
	e.Specs.CPUCores = runtime.NumCPU()

	// 3. Assign Tier (Ported heuristic)
	totalGB := e.Specs.TotalRAM / (1024 * 1024 * 1024)
	if totalGB > 32 {
		e.Specs.Tier = TierServer
	} else if totalGB >= 8 {
		e.Specs.Tier = TierStandard
	} else {
		e.Specs.Tier = TierEdge
	}

	log.Printf("[SubstrateEngine] Substrate identified: %d Cores, %d GB RAM. Assigned Tier: %s", 
		e.Specs.CPUCores, totalGB, e.Specs.Tier)
}

// GetBudgetMultiplier returns a scaling factor for MCTS iterations based on hardware.
func (e *SubstrateEngine) GetBudgetMultiplier() float64 {
	e.mu.RLock()
	defer e.mu.RUnlock()

	switch e.Specs.Tier {
	case TierServer:
		return 2.0 // Deep reasoning
	case TierStandard:
		return 1.0 // Normal
	case TierEdge:
		return 0.5 // snappy/reflex reasoning
	}
	return 1.0
}

func (e *SubstrateEngine) GetSummary() string {
	e.mu.RLock()
	defer e.mu.RUnlock()
	return fmt.Sprintf("Hardware: %s Tier (%d Cores, %d GB RAM)", 
		e.Specs.Tier, e.Specs.CPUCores, e.Specs.TotalRAM/(1024*1024*1024))
}
