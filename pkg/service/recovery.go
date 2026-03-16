package service

import (
	"context"
	"log"
	"math"
	"strconv"
	"sync"
	"time"
)

// RecoveryStatus represents the status of a recovery attempt
type RecoveryStatus string

const (
	RecoveryPending            RecoveryStatus = "pending"
	RecoveryInProgress         RecoveryStatus = "in_progress"
	RecoverySuccess            RecoveryStatus = "success"
	RecoveryFailed             RecoveryStatus = "failed"
	RecoveryMaxAttemptsReached RecoveryStatus = "max_attempts_reached"
)

// RecoveryAttempt records a single recovery attempt
type RecoveryAttempt struct {
	ModuleName      string         `json:"module_name"`
	AttemptNumber   int            `json:"attempt_number"`
	Status          RecoveryStatus `json:"status"`
	StartTime       time.Time      `json:"start_time"`
	EndTime         time.Time      `json:"end_time"`
	Duration        time.Duration  `json:"duration"`
	Error           string         `json:"error"`
	BackoffDuration time.Duration  `json:"backoff_duration"`
}

// ModuleRecoveryService manages automatic recovery of failed modules
type ModuleRecoveryService struct {
	registry    *ModuleRegistry
	monitor     *ModuleMonitorService
	recovering  map[string]bool
	history     map[string][]RecoveryAttempt
	mu          sync.Mutex
	
	enabled      bool
	maxAttempts  int
	backoffBase  float64
	backoffMax   time.Duration
	ensureOnline bool
}

// NewModuleRecoveryService creates a new recovery service
func NewModuleRecoveryService(registry *ModuleRegistry, monitor *ModuleMonitorService) *ModuleRecoveryService {
	enabled := getEnv("MAVAIA_RECOVERY_ENABLED", "true") == "true"
	maxAttempts, _ := strconv.Atoi(getEnv("MAVAIA_RECOVERY_MAX_ATTEMPTS", "-1"))
	backoffBase, _ := strconv.ParseFloat(getEnv("MAVAIA_RECOVERY_BACKOFF_BASE", "2.0"), 64)
	backoffMax, _ := strconv.ParseFloat(getEnv("MAVAIA_RECOVERY_BACKOFF_MAX", "300.0"), 64)
	ensureOnline := getEnv("MAVAIA_RECOVERY_ENSURE_ONLINE", "true") == "true"

	s := &ModuleRecoveryService{
		registry:     registry,
		monitor:      monitor,
		recovering:   make(map[string]bool),
		history:      make(map[string][]RecoveryAttempt),
		enabled:      enabled,
		maxAttempts:  maxAttempts,
		backoffBase:  backoffBase,
		backoffMax:   time.Duration(backoffMax * float64(time.Second)),
		ensureOnline: ensureOnline,
	}

	if monitor != nil {
		monitor.RegisterStatusCallback(s.onModuleStatusChange)
	}

	return s
}

func (s *ModuleRecoveryService) onModuleStatusChange(name string, newStatus ModuleStatus, prevStatus *ModuleStatus) {
	if !s.enabled {
		return
	}

	if newStatus.State == StateOffline || newStatus.State == StateDegraded {
		go s.RecoverModule(context.Background(), name)
	}
}

// RecoverModule attempts to recover a module
func (s *ModuleRecoveryService) RecoverModule(ctx context.Context, name string) {
	s.mu.Lock()
	if s.recovering[name] {
		s.mu.Unlock()
		return
	}
	s.recovering[name] = true
	attempts := len(s.history[name])
	s.mu.Unlock()

	defer func() {
		s.mu.Lock()
		s.recovering[name] = false
		s.mu.Unlock()
	}()

	if s.maxAttempts != -1 && attempts >= s.maxAttempts && !s.ensureOnline {
		log.Printf("[Recovery] Max attempts reached for %s", name)
		return
	}

	// Calculate backoff
	backoff := time.Duration(math.Pow(s.backoffBase, float64(attempts))) * time.Second
	if backoff > s.backoffMax {
		backoff = s.backoffMax
	}

	if attempts > 0 {
		time.Sleep(backoff)
	}

	startTime := time.Now()
	log.Printf("[Recovery] Attempting to recover module %s (attempt %d)", name, attempts+1)

	attempt := RecoveryAttempt{
		ModuleName:      name,
		AttemptNumber:   attempts + 1,
		Status:          RecoveryInProgress,
		StartTime:       startTime,
		BackoffDuration: backoff,
	}

	// Recovery logic: In Go backbone, we might trigger a Python sidecar restart 
	// or re-initialize the native module.
	err := s.performRecovery(ctx, name)

	attempt.EndTime = time.Now()
	attempt.Duration = attempt.EndTime.Sub(startTime)

	if err != nil {
		attempt.Status = RecoveryFailed
		attempt.Error = err.Error()
		log.Printf("[Recovery] Failed to recover module %s: %v", name, err)
		
		// If ensureOnline is true, retry
		if s.ensureOnline {
			go s.RecoverModule(ctx, name)
		}
	} else {
		attempt.Status = RecoverySuccess
		log.Printf("[Recovery] Successfully recovered module %s", name)
	}

	s.mu.Lock()
	s.history[name] = append(s.history[name], attempt)
	s.mu.Unlock()
}

func (s *ModuleRecoveryService) performRecovery(ctx context.Context, name string) error {
	instance, err := s.registry.GetModule(name)
	if err != nil {
		return err
	}

	// 1. Cleanup
	_ = instance.Cleanup(ctx)

	// 2. Initialize
	return instance.Initialize(ctx)
}
