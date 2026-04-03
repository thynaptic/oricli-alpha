// Package flowtriggers monitors context signals and fires reflection opportunities.
// Ported from FocusOS/Services/FlowTriggersService.swift
//
// Trigger sources:
//   drift  — DriftDetector publishes a drift event (ERI deviated from baseline)
//   idle   — No activity observed for IdleTimeoutMinutes (default 5)
//   evening — External notification (e.g., end-of-day ritual)
//   manual  — Caller invokes TriggerManual()
package flowtriggers

import (
	"sync"
	"time"

	"github.com/thynaptic/oricli-go/pkg/drift"
)

// TriggerType identifies what caused a reflection to be requested.
type TriggerType string

const (
	TriggerDrift   TriggerType = "drift"
	TriggerIdle    TriggerType = "idle"
	TriggerEvening TriggerType = "evening"
	TriggerManual  TriggerType = "manual"
)

// TriggerEvent is published when a reflection opportunity is detected.
type TriggerEvent struct {
	Type      TriggerType
	Timestamp time.Time
}

// Settings controls which trigger sources are active.
type Settings struct {
	Enabled            bool
	DriftEnabled       bool
	EveningEnabled     bool
	IdleEnabled        bool
	IdleTimeoutMinutes int // default 5
}

// DefaultSettings returns sane defaults (all triggers on, 5-min idle).
func DefaultSettings() Settings {
	return Settings{
		Enabled:            true,
		DriftEnabled:       true,
		EveningEnabled:     true,
		IdleEnabled:        true,
		IdleTimeoutMinutes: 5,
	}
}

// Service monitors sources and emits TriggerEvents on its channel.
type Service struct {
	Settings Settings

	mu           sync.Mutex
	events       chan TriggerEvent
	lastActivity time.Time
	stopCh       chan struct{}
	running      bool
}

// New creates a Service with default settings.
func New() *Service {
	return &Service{
		Settings:     DefaultSettings(),
		events:       make(chan TriggerEvent, 16),
		lastActivity: time.Now(),
		stopCh:       make(chan struct{}),
	}
}

// Start begins monitoring drift events and idle polling.
// driftEvents is the read-only channel from drift.Detector.Events().
// Safe to call multiple times — subsequent calls are no-ops until Stop().
func (s *Service) Start(driftEvents <-chan drift.Event) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.running {
		return
	}
	s.running = true
	s.lastActivity = time.Now()

	go s.runDriftWatcher(driftEvents)
	go s.runIdleWatcher()
}

// Stop shuts down all background goroutines.
func (s *Service) Stop() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if !s.running {
		return
	}
	close(s.stopCh)
	s.running = false
	// reset stop channel for potential restart
	s.stopCh = make(chan struct{})
}

// UpdateActivity resets the idle timer (call whenever the user interacts).
func (s *Service) UpdateActivity() {
	s.mu.Lock()
	s.lastActivity = time.Now()
	s.mu.Unlock()
}

// TriggerManual fires a manual reflection event.
func (s *Service) TriggerManual() {
	s.publish(TriggerManual)
}

// TriggerEvening fires an evening ritual reflection event.
func (s *Service) TriggerEvening() {
	if !s.Settings.EveningEnabled || !s.Settings.Enabled {
		return
	}
	s.publish(TriggerEvening)
}

// Events returns the read-only trigger channel.
// Consume this channel in FlowCompanionEngine.
func (s *Service) Events() <-chan TriggerEvent {
	return s.events
}

// --- background workers ---

func (s *Service) runDriftWatcher(driftEvents <-chan drift.Event) {
	if driftEvents == nil {
		return
	}
	for {
		select {
		case <-s.stopCh:
			return
		case _, ok := <-driftEvents:
			if !ok {
				return
			}
			if s.Settings.DriftEnabled && s.Settings.Enabled {
				s.publish(TriggerDrift)
			}
		}
	}
}

func (s *Service) runIdleWatcher() {
	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()
	triggered := false // prevent re-triggering until activity resets

	for {
		select {
		case <-s.stopCh:
			return
		case <-ticker.C:
			if !s.Settings.IdleEnabled || !s.Settings.Enabled {
				continue
			}
			s.mu.Lock()
			idleDur := time.Since(s.lastActivity)
			s.mu.Unlock()

			threshold := time.Duration(s.Settings.IdleTimeoutMinutes) * time.Minute
			if idleDur >= threshold && !triggered {
				triggered = true
				s.publish(TriggerIdle)
			} else if idleDur < threshold {
				triggered = false // reset after activity
			}
		}
	}
}

func (s *Service) publish(t TriggerType) {
	select {
	case s.events <- TriggerEvent{Type: t, Timestamp: time.Now()}:
	default:
		// channel full — drop to avoid blocking (non-critical)
	}
}
