package oracle

import (
	"context"
	"log"
)

// DaemonManager is a no-op stub retained for call-site compatibility.
// The Copilot SDK daemon is no longer used; Oracle calls provider APIs directly.
type DaemonManager struct{ port int }

func NewDaemonManager(port int) *DaemonManager { return &DaemonManager{port: port} }

func (m *DaemonManager) Start(_ context.Context) error {
	log.Printf("[Oracle:Manager] direct provider API mode — no daemon required")
	return nil
}

func (m *DaemonManager) Stop() error { return nil }
