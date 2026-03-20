package kernel

import (
	"fmt"
	"log"
	"sync"

	"github.com/thynaptic/oricli-go/pkg/core/model"
)

// SharedBuffer represents a block of memory accessible by multiple processes.
type SharedBuffer struct {
	Name string
	Data []byte
	Mu   sync.Mutex
}

// MicroKernel is the Ring-0 overseer of the Oricli-Alpha OS.
// It manages process lifecycles, memory allocation, and hardware abstraction.
type MicroKernel struct {
	Processes     map[ProcessID]*AgentProcess
	Buffers       map[string]*SharedBuffer
	SwarmBus      interface{} // interface to avoid circular dependency if needed
	Safety        *SafetyFramework
	Ghost         interface{} // GhostClusterService
	Precog        interface{} // MetacogDaemon
	mu            sync.RWMutex
}

func NewMicroKernel(mb interface{}, ghost interface{}, precog interface{}, safety *SafetyFramework) *MicroKernel {
	return &MicroKernel{
		Processes: make(map[ProcessID]*AgentProcess),
		Buffers:   make(map[string]*SharedBuffer),
		Safety:    safety,
		Ghost:     ghost,
		Precog:    precog,
	}
}

// SpawnProcess creates a new sovereign execution context.
func (k *MicroKernel) SpawnProcess(profile model.AgentProfile, initialTokens float64, intentPlan string) (ProcessID, error) {
	k.mu.Lock()
	defer k.mu.Unlock()

	// 1. Safety Check (Spend Cap)
	if !k.Safety.AuthorizeSpend(initialTokens) {
		return "", fmt.Errorf("spawn rejected: insufficient safety budget")
	}

	// 2. Resource Allocation
	proc, err := NewAgentProcess(profile, initialTokens)
	if err != nil {
		return "", err
	}

	k.Processes[proc.ID] = proc
	log.Printf("[Kernel] Process %s spawned for agent: %s", proc.ID, profile.Name)
	return proc.ID, nil
}

// AllocateBuffer provides a process with shared memory.
func (k *MicroKernel) AllocateBuffer(name string, size int) (*SharedBuffer, error) {
	k.mu.Lock()
	defer k.mu.Unlock()

	if _, exists := k.Buffers[name]; exists {
		return nil, fmt.Errorf("buffer %s already exists", name)
	}

	buf := &SharedBuffer{
		Name: name,
		Data: make([]byte, size),
	}
	k.Buffers[name] = buf
	return buf, nil
}

// TerminateProcess gracefully shuts down an agent context.
func (k *MicroKernel) TerminateProcess(pid ProcessID) error {
	k.mu.Lock()
	defer k.mu.Unlock()

	proc, ok := k.Processes[pid]
	if !ok {
		return fmt.Errorf("process %s not found", pid)
	}

	proc.Status = StatusTerminated
	delete(k.Processes, pid)
	log.Printf("[Kernel] Process %s terminated.", pid)
	return nil
}

// ExecSyscall handles incoming Ring-0 requests from processes.
func (k *MicroKernel) ExecSyscall(req SyscallRequest) SyscallResponse {
	// 1. Identity Verification
	k.mu.RLock()
	_, ok := k.Processes[req.PID]
	k.mu.RUnlock()

	if !ok {
		return SyscallResponse{Success: false, Error: fmt.Errorf("invalid process ID")}
	}

	// 2. Permission Check (Simplified for now)
	// In full implementation, we would check proc.Profile for blocked modules/ops

	// 3. Dispatch
	switch req.Call {
	case SysQueryMemory:
		return k.handleQueryMemory(req)
	case SysWriteMemory:
		return k.handleWriteMemory(req)
	case SysAllocGPU:
		return k.handleAllocGhost(req)
	case SysSendMessage:
		return k.handleSendMessage(req)
	default:
		return SyscallResponse{Success: false, Error: fmt.Errorf("unknown syscall ID: %d", req.Call)}
	}
}

func (k *MicroKernel) handleQueryMemory(req SyscallRequest) SyscallResponse {
	return SyscallResponse{Success: true, Data: "Memory queried successfully (Stub)"}
}

func (k *MicroKernel) handleWriteMemory(req SyscallRequest) SyscallResponse {
	return SyscallResponse{Success: true, Data: "Memory written successfully (Stub)"}
}

func (k *MicroKernel) handleAllocGhost(req SyscallRequest) SyscallResponse {
	return SyscallResponse{Success: true, Data: "Ghost Cluster allocated (Stub)"}
}

func (k *MicroKernel) handleSendMessage(req SyscallRequest) SyscallResponse {
	return SyscallResponse{Success: true, Data: "Message sent (Stub)"}
}

func (k *MicroKernel) ProfileAllowed(p model.AgentProfile, module, op string) (bool, string) {
	for _, blocked := range p.BlockedModules {
		if blocked == module {
			return false, "module blocked"
		}
	}
	return true, ""
}
