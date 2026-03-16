package service

import (
	"context"
	"fmt"
	"strconv"
	"sync"
	"time"
)

// ModuleState represents the operational state of a module
type ModuleState string

const (
	StateOnline   ModuleState = "online"
	StateOffline  ModuleState = "offline"
	StateDegraded ModuleState = "degraded"
	StateUnknown  ModuleState = "unknown"
)

// ModuleStatus represents the status of a module
type ModuleStatus struct {
	ModuleName          string                 `json:"module_name"`
	State               ModuleState            `json:"state"`
	LastCheck           time.Time              `json:"last_check"`
	ResponseTime        time.Duration          `json:"response_time"`
	DegradationReason   string                 `json:"degradation_reason"`
	ConsecutiveFailures int                    `json:"consecutive_failures"`
	LastSuccess         time.Time              `json:"last_success"`
	Details             map[string]interface{} `json:"details"`
}

// ModuleMonitorService monitors the health of modules
type ModuleMonitorService struct {
	registry   *ModuleRegistry
	statuses   map[string]ModuleStatus
	mu         sync.RWMutex
	monitoring bool
	stopChan   chan struct{}
	
	interval       time.Duration
	timeout        time.Duration
	slowThreshold  time.Duration
	
	callbacks []func(string, ModuleStatus, *ModuleStatus)
}

// MonitorService is a type alias for backward compatibility
type MonitorService = ModuleMonitorService

// NewModuleMonitorService creates a new monitor service
func NewModuleMonitorService(registry *ModuleRegistry) *ModuleMonitorService {
	interval, _ := strconv.ParseFloat(getEnv("MAVAIA_MONITOR_INTERVAL", "30.0"), 64)
	timeout, _ := strconv.ParseFloat(getEnv("MAVAIA_MONITOR_TIMEOUT", "10.0"), 64)
	slowThreshold, _ := strconv.ParseFloat(getEnv("MAVAIA_MONITOR_SLOW_THRESHOLD", "5.0"), 64)

	return &ModuleMonitorService{
		registry:      registry,
		statuses:      make(map[string]ModuleStatus),
		stopChan:      make(chan struct{}),
		interval:      time.Duration(interval * float64(time.Second)),
		timeout:       time.Duration(timeout * float64(time.Second)),
		slowThreshold: time.Duration(slowThreshold * float64(time.Second)),
	}
}

// NewMonitorService creates a new monitor service (alias for NewModuleMonitorService)
func NewMonitorService() *ModuleMonitorService {
	// We need a registry for the new version, but the old version didn't have one.
	// For backward compatibility, we'll use a temporary empty registry if needed.
	return NewModuleMonitorService(NewModuleRegistry(""))
}

// Start starts the monitoring loop with a custom check function (backward compatibility)
func (m *ModuleMonitorService) Start(checkFn func()) {
	m.mu.Lock()
	if m.monitoring {
		m.mu.Unlock()
		return
	}
	m.monitoring = true
	m.mu.Unlock()

	go func() {
		ticker := time.NewTicker(m.interval)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				if checkFn != nil {
					checkFn()
				}
				m.checkAllModules()
			case <-m.stopChan:
				return
			}
		}
	}()
}

// UpdateStatus manually updates the status of a module (backward compatibility)
func (m *ModuleMonitorService) UpdateStatus(name string, state ModuleState, latency float64, reason string) {
	m.mu.Lock()
	prevStatus, hasPrev := m.statuses[name]
	
	status := ModuleStatus{
		ModuleName:        name,
		State:             state,
		LastCheck:         time.Now(),
		ResponseTime:      time.Duration(latency * float64(time.Millisecond)),
		DegradationReason: reason,
	}

	if state == StateOnline {
		status.ConsecutiveFailures = 0
		status.LastSuccess = time.Now()
	} else if hasPrev {
		status.ConsecutiveFailures = prevStatus.ConsecutiveFailures + 1
		status.LastSuccess = prevStatus.LastSuccess
	} else {
		status.ConsecutiveFailures = 1
	}

	m.statuses[name] = status
	m.mu.Unlock()

	// Trigger callbacks if state changed
	if !hasPrev || prevStatus.State != status.State {
		for _, cb := range m.callbacks {
			var prev *ModuleStatus
			if hasPrev {
				prev = &prevStatus
			}
			cb(name, status, prev)
		}
	}
}

// StartMonitoring starts the monitoring loop
func (m *ModuleMonitorService) StartMonitoring() {
	m.Start(nil)
}

// StopMonitoring stops the monitoring loop
func (m *ModuleMonitorService) StopMonitoring() {
	m.mu.Lock()
	if !m.monitoring {
		m.mu.Unlock()
		return
	}
	m.monitoring = false
	close(m.stopChan)
	m.mu.Unlock()
}

func (m *ModuleMonitorService) monitorLoop() {
	ticker := time.NewTicker(m.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			m.checkAllModules()
		case <-m.stopChan:
			return
		}
	}
}

func (m *ModuleMonitorService) checkAllModules() {
	moduleNames := m.registry.ListModules()
	for _, name := range moduleNames {
		m.CheckModule(context.Background(), name)
	}
}

// CheckModule performs a health check on a specific module
func (m *ModuleMonitorService) CheckModule(ctx context.Context, name string) ModuleStatus {
	m.mu.RLock()
	prevStatus, hasPrev := m.statuses[name]
	m.mu.RUnlock()

	startTime := time.Now()
	instance, err := m.registry.GetModule(name)
	
	status := ModuleStatus{
		ModuleName: name,
		LastCheck:  time.Now(),
	}

	if err != nil {
		status.State = StateOffline
		status.DegradationReason = fmt.Sprintf("failed to get module: %v", err)
		if hasPrev {
			status.ConsecutiveFailures = prevStatus.ConsecutiveFailures + 1
			status.LastSuccess = prevStatus.LastSuccess
		} else {
			status.ConsecutiveFailures = 1
		}
	} else {
		// Attempt a ping/health_check operation
		ctx, cancel := context.WithTimeout(ctx, m.timeout)
		defer cancel()

		_, err := instance.Execute(ctx, "health_check", nil)
		responseTime := time.Since(startTime)
		status.ResponseTime = responseTime

		if err != nil {
			status.State = StateOffline
			status.DegradationReason = fmt.Sprintf("operation failed: %v", err)
			status.ConsecutiveFailures = prevStatus.ConsecutiveFailures + 1
			status.LastSuccess = prevStatus.LastSuccess
		} else {
			if responseTime > m.slowThreshold {
				status.State = StateDegraded
				status.DegradationReason = fmt.Sprintf("slow response: %v", responseTime)
			} else {
				status.State = StateOnline
			}
			status.ConsecutiveFailures = 0
			status.LastSuccess = time.Now()
		}
	}

	m.mu.Lock()
	m.statuses[name] = status
	m.mu.Unlock()

	// Trigger callbacks if state changed
	if !hasPrev || prevStatus.State != status.State {
		for _, cb := range m.callbacks {
			var prev *ModuleStatus
			if hasPrev {
				prev = &prevStatus
			}
			cb(name, status, prev)
		}
	}

	return status
}

// RegisterStatusCallback registers a function to be called on status changes
func (m *ModuleMonitorService) RegisterStatusCallback(cb func(string, ModuleStatus, *ModuleStatus)) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.callbacks = append(m.callbacks, cb)
}

// GetModuleStatus returns the current status of a module
func (m *ModuleMonitorService) GetModuleStatus(name string) (ModuleStatus, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	status, ok := m.statuses[name]
	return status, ok
}

// GetModuleState returns the current state of a module
func (m *ModuleMonitorService) GetModuleState(name string) ModuleState {
	m.mu.RLock()
	defer m.mu.RUnlock()
	status, ok := m.statuses[name]
	if !ok {
		return StateUnknown
	}
	return status.State
}

// ListStatuses returns all module statuses
func (m *ModuleMonitorService) ListStatuses() map[string]ModuleStatus {
	m.mu.RLock()
	defer m.mu.RUnlock()
	
	res := make(map[string]ModuleStatus)
	for k, v := range m.statuses {
		res[k] = v
	}
	return res
}
