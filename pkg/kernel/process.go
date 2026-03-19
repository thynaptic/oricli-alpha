package kernel

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/thynaptic/oricli-go/pkg/gosh"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// ProcessState defines the current lifecycle stage of an agent process.
type ProcessState string

const (
	StateInit     ProcessState = "INIT"     // Booting up
	StateReady    ProcessState = "READY"    // Waiting for CPU/Task
	StateRunning  ProcessState = "RUNNING"  // Actively executing
	StateSleeping ProcessState = "SLEEPING" // Awaiting I/O or Hardware
	StateZombie   ProcessState = "ZOMBIE"   // Terminated, waiting for Kernel cleanup
	StateKilled   ProcessState = "KILLED"   // Forcefully terminated by Sentinel/Kernel
)

// ProcessID is a unique identifier for an agent process in the Hive OS.
type ProcessID string

// AgentProcess represents a sovereign agent managed by the Kernel.
type AgentProcess struct {
	PID           ProcessID
	Profile       service.AgentProfile
	State         ProcessState
	Sandbox       *gosh.Session
	Tokens        float64
	Priority      int
	StartTime     time.Time
	Ctx           context.Context
	cancelFunc    context.CancelFunc
}

// NewAgentProcess initializes a new process struct but does not start it.
func NewAgentProcess(profile service.AgentProfile, tokens float64) (*AgentProcess, error) {
	sandbox, err := gosh.NewOverlaySession(".")
	if err != nil {
		return nil, err
	}

	ctx, cancel := context.WithCancel(context.Background())

	return &AgentProcess{
		PID:        ProcessID(uuid.New().String()[:8]),
		Profile:    profile,
		State:      StateInit,
		Sandbox:    sandbox,
		Tokens:     tokens,
		Priority:   0,
		StartTime:  time.Now(),
		Ctx:        ctx,
		cancelFunc: cancel,
	}, nil
}

// Terminate safely shuts down the process and its sandbox.
func (p *AgentProcess) Terminate() {
	p.State = StateZombie
	p.cancelFunc()
}
