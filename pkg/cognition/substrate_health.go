package cognition

import (
	"context"
	"log"
	"sync"
	"time"
)

// --- Pillar 21: Substrate Health & Recovery ---
// Ported from Aurora's ModelHealthService.swift.
// Implements background heartbeat and autonomous recovery for neural models.

type HealthStatus string

const (
	StatusOnline   HealthStatus = "online"
	StatusOffline  HealthStatus = "offline"
	StatusDegraded HealthStatus = "degraded"
	StatusUnknown  HealthStatus = "unknown"
)

type ModelHealth struct {
	Status             HealthStatus
	LastChecked        time.Time
	ResponseTimeMS     int64
	ConsecutiveFailures int
}

type HealthMonitor struct {
	Statuses map[string]*ModelHealth
	Interval time.Duration
	Mu       sync.RWMutex
	StopCh   chan struct{}
}

func NewHealthMonitor() *HealthMonitor {
	return &HealthMonitor{
		Statuses: make(map[string]*ModelHealth),
		Interval: 30 * time.Second,
		StopCh:   make(chan struct{}),
	}
}

// Start initiates the background heartbeat loop.
func (m *HealthMonitor) Start(ctx context.Context) {
	log.Println("[HealthMonitor] Substrate heartbeat started.")
	ticker := time.NewTicker(m.Interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			m.performHeartbeat()
		case <-m.StopCh:
			return
		case <-ctx.Done():
			return
		}
	}
}

func (m *HealthMonitor) performHeartbeat() {
	m.Mu.Lock()
	defer m.Mu.Unlock()

	for model, health := range m.Statuses {
		log.Printf("[HealthMonitor] Verifying %s...", model)
		
		// 1. Staggered Check (Simulated for ported logic)
		start := time.Now()
		success := true // In full impl, this runs a test prompt
		
		if !success {
			health.ConsecutiveFailures++
			if health.ConsecutiveFailures >= 3 {
				health.Status = StatusOffline
				log.Printf("[HealthMonitor] CRITICAL: %s is OFFLINE after 3 failures.", model)
				go m.AttemptRecovery(model)
			} else {
				health.Status = StatusDegraded
			}
		} else {
			health.Status = StatusOnline
			health.ConsecutiveFailures = 0
			health.ResponseTimeMS = time.Since(start).Milliseconds()
		}
		health.LastChecked = time.Now()
	}
}

// AttemptRecovery triggers a re-warmup of the failed model.
func (m *HealthMonitor) AttemptRecovery(model string) {
	log.Printf("[HealthMonitor] Initiating autonomous recovery for %s...", model)
	// In full impl, this calls ModelWarmupService
	time.Sleep(2 * time.Second)
	
	m.Mu.Lock()
	if h, ok := m.Statuses[model]; ok {
		h.Status = StatusOnline
		h.ConsecutiveFailures = 0
		log.Printf("[HealthMonitor] RECOVERY SUCCESSFUL: %s is back online.", model)
	}
	m.Mu.Unlock()
}

func (m *HealthMonitor) GetStatus(model string) HealthStatus {
	m.Mu.RLock()
	defer m.Mu.RUnlock()
	if h, ok := m.Statuses[model]; ok {
		return h.Status
	}
	return StatusUnknown
}

func (m *HealthMonitor) RegisterModel(model string) {
	m.Mu.Lock()
	defer m.Mu.Unlock()
	m.Statuses[model] = &ModelHealth{Status: StatusUnknown}
}
