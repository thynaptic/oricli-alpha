package kernel

import (
	"log"
	"sync"
)

// DefconLevel represents the current threat and autonomy level of the OS.
type DefconLevel int

const (
	Defcon5 DefconLevel = 5 // Normal Operations: Full Autonomy, Auto-Scaling allowed.
	Defcon4 DefconLevel = 4 // Elevated: No Auto-Scaling, max 10 active PIDs.
	Defcon3 DefconLevel = 3 // Restricted: No new GPU allocations, max 5 active PIDs.
	Defcon2 DefconLevel = 2 // Quarantine: All agents suspended, No Syscalls allowed.
	Defcon1 DefconLevel = 1 // PANIC: Kill all agents, Vanish all Ghost Clusters, Lock Kernel.
)

// SafetyFramework enforces global constraints and threat levels on the MicroKernel.
type SafetyFramework struct {
	Level           DefconLevel
	MaxDailySpend   float64
	CurrentSpend    float64
	MaxActivePIDs   int
	IsKernelLocked  bool
	mu              sync.RWMutex
}

// NewSafetyFramework initializes the system at DEFCON 5 (Normal).
func NewSafetyFramework(maxSpend float64) *SafetyFramework {
	return &SafetyFramework{
		Level:         Defcon5,
		MaxDailySpend: maxSpend,
		CurrentSpend:  0.0,
		MaxActivePIDs: 100, 
	}
}

// SetDefcon changes the global threat level and logs the transition.
func (s *SafetyFramework) SetDefcon(newLevel DefconLevel) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if newLevel < Defcon1 || newLevel > Defcon5 {
		return
	}

	oldLevel := s.Level
	s.Level = newLevel
	log.Printf("[SAFETY] DEFCON LEVEL CHANGED: %d -> %d", oldLevel, newLevel)

	if newLevel == Defcon1 {
		s.IsKernelLocked = true
		log.Println("[SAFETY] CRITICAL: KERNEL IS LOCKED. ALL SYSTEMS HALTED.")
	}
}

// AuthorizeSpend checks if a financial or token operation exceeds hard caps.
func (s *SafetyFramework) AuthorizeSpend(amount float64) bool {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.IsKernelLocked {
		return false
	}

	if s.CurrentSpend+amount > s.MaxDailySpend {
		log.Printf("[SAFETY] BLOCKED: Spend of %.2f exceeds daily cap of %.2f (Current: %.2f)", amount, s.MaxDailySpend, s.CurrentSpend)
		return false
	}

	s.CurrentSpend += amount
	return true
}

// CheckClearance ensures the current DEFCON level permits an action.
func (s *SafetyFramework) CheckClearance(requiredLevel DefconLevel) bool {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if s.IsKernelLocked {
		return false
	}

	// Lower Defcon number = Higher restriction. 
	return s.Level >= requiredLevel
}

// GetMaxPIDs returns the current limit based on DEFCON level.
func (s *SafetyFramework) GetMaxPIDs() int {
	s.mu.RLock()
	defer s.mu.RUnlock()

	switch s.Level {
	case Defcon5:
		return s.MaxActivePIDs
	case Defcon4:
		return 10
	case Defcon3:
		return 5
	case Defcon2, Defcon1:
		return 0
	default:
		return 0
	}
}
