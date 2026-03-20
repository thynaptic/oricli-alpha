package kernel

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/thynaptic/oricli-go/pkg/core/model"
)

type ProcessID string
type ProcessStatus string

const (
	StatusRunning    ProcessStatus = "running"
	StatusSuspended  ProcessStatus = "suspended"
	StatusTerminated ProcessStatus = "terminated"
)

// AgentProcess represents a sovereign execution context within the Hive OS.
type AgentProcess struct {
	ID            ProcessID
	Status        ProcessStatus
	Profile       model.AgentProfile
	Tokens        float64 // Metacog Tokens (Budget)
	SharedBuffers map[string]*SharedBuffer
	CreatedAt     time.Time
	Context       context.Context
	Cancel        context.CancelFunc
}

func NewAgentProcess(profile model.AgentProfile, tokens float64) (*AgentProcess, error) {
	ctx, cancel := context.WithCancel(context.Background())
	return &AgentProcess{
		ID:            ProcessID(uuid.New().String()[:8]),
		Status:        StatusRunning,
		Profile:       profile,
		Tokens:        tokens,
		SharedBuffers: make(map[string]*SharedBuffer),
		CreatedAt:     time.Now(),
		Context:       ctx,
		Cancel:        cancel,
	}, nil
}

func (p *AgentProcess) UseTokens(amount float64) error {
	if p.Tokens < amount {
		return fmt.Errorf("insufficient metacog tokens: required %.2f, available %.2f", amount, p.Tokens)
	}
	p.Tokens -= amount
	return nil
}
