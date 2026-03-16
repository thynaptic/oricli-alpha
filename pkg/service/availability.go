package service

import (
	"context"
	"log"
	"strconv"
	"sync"
	"time"
)

// ModuleAvailabilityManager coordinates warmup, monitoring, recovery, and fallback routing
type ModuleAvailabilityManager struct {
	registry    *ModuleRegistry
	monitor     *ModuleMonitorService
	recovery    *ModuleRecoveryService
	classifier  *DegradedModeClassifier
	
	ensureAllOnline bool
	maxWait         time.Duration
	mu              sync.RWMutex
	running         bool
}

// NewModuleAvailabilityManager creates a new availability manager
func NewModuleAvailabilityManager(
	registry *ModuleRegistry,
	monitor *ModuleMonitorService,
	recovery *ModuleRecoveryService,
	classifier *DegradedModeClassifier,
) *ModuleAvailabilityManager {
	ensureAllOnline := getEnv("MAVAIA_ENSURE_ALL_MODULES_ONLINE", "true") == "true"
	maxWaitStr := getEnv("MAVAIA_MAX_WAIT_FOR_MODULE", "60.0")
	maxWaitSec, _ := strconv.ParseFloat(maxWaitStr, 64)

	return &ModuleAvailabilityManager{
		registry:        registry,
		monitor:         monitor,
		recovery:        recovery,
		classifier:      classifier,
		ensureAllOnline: ensureAllOnline,
		maxWait:         time.Duration(maxWaitSec * float64(time.Second)),
	}
}

// Start initiates the availability management loops
func (m *ModuleAvailabilityManager) Start(ctx context.Context) {
	m.mu.Lock()
	if m.running {
		m.mu.Unlock()
		return
	}
	m.running = true
	m.mu.Unlock()

	if m.ensureAllOnline {
		go m.ensureOnlineLoop(ctx)
	}
}

func (m *ModuleAvailabilityManager) ensureOnlineLoop(ctx context.Context) {
	intervalStr := getEnv("MAVAIA_ENSURE_ONLINE_INTERVAL", "30.0")
	intervalSec, _ := strconv.ParseFloat(intervalStr, 64)
	ticker := time.NewTicker(time.Duration(intervalSec * float64(time.Second)))
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			m.checkAndRecoverAll()
		}
	}
}

func (m *ModuleAvailabilityManager) checkAndRecoverAll() {
	modules := m.registry.ListModules()
	for _, name := range modules {
		status, ok := m.monitor.GetModuleStatus(name)
		if ok && (status.State == StateOffline || status.State == StateDegraded) {
			log.Printf("[Availability] Module %s is %s, triggering recovery", name, status.State)
			go m.recovery.RecoverModule(context.Background(), name)
		}
	}
}

// GetModuleOrFallback returns the primary module or a fallback if primary is degraded
func (m *ModuleAvailabilityManager) GetModuleOrFallback(name string, operation string) (ModuleInstance, string, bool, string, error) {
	status, ok := m.monitor.GetModuleStatus(name)
	
	if ok && status.State == StateOnline {
		instance, err := m.registry.GetModule(name)
		return instance, name, false, operation, err
	}

	// Primary is not online
	if m.ensureAllOnline && ok && (status.State == StateOffline || status.State == StateDegraded) {
		// In "ensure all online" mode, we might want to wait for recovery
		log.Printf("[Availability] Module %s is %s, waiting for recovery...", name, status.State)
		
		// Start recovery if not already in progress
		go m.recovery.RecoverModule(context.Background(), name)

		// Wait for module to come online (simplified)
		start := time.Now()
		for time.Since(start) < m.maxWait {
			time.Sleep(1 * time.Second)
			newStatus, _ := m.monitor.GetModuleStatus(name)
			if newStatus.State == StateOnline {
				instance, err := m.registry.GetModule(name)
				return instance, name, false, operation, err
			}
		}
	}

	// Use fallback if primary failed or wait timed out
	if m.classifier != nil {
		fallbackName := m.classifier.GetFallbackModule(name, operation)
		if fallbackName != "" {
			log.Printf("[Availability] Using fallback %s for %s", fallbackName, name)
			instance, err := m.registry.GetModule(fallbackName)
			if err == nil {
				mappedOp := m.classifier.GetFallbackOperation(name, operation, fallbackName)
				return instance, fallbackName, true, mappedOp, nil
			}
		}
	}

	// Final attempt: get primary anyway
	instance, err := m.registry.GetModule(name)
	return instance, name, false, operation, err
}
