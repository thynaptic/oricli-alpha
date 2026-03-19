package kernel

import (
	"fmt"
)

// SyscallID represents the type of kernel request.
type SyscallID int

const (
	// Memory/Data
	SysQueryMemory SyscallID = iota
	SysWriteMemory
	
	// Infrastructure
	SysAllocGPU
	SysFreeGPU
	
	// Inter-Process Communication
	SysSendMessage
	SysAllocSharedMem
	SysMapSharedMem
	SysWriteSharedMem
	
	// Economic
	SysTransferTokens
	
	// Safety & Global State
	SysPanic      // Instantly drop to DEFCON 1
	SysSetDefcon  // Manually change DEFCON level
)

// SyscallRequest is the payload an AgentProcess sends to the Kernel.
type SyscallRequest struct {
	PID      ProcessID
	Call     SyscallID
	Args     map[string]interface{}
	FeeOffer float64 // Agents can bribe the scheduler for faster syscalls
}

// SyscallResponse is what the Kernel returns.
type SyscallResponse struct {
	Success bool
	Data    interface{}
	Error   error
	FeePaid float64
}

// SyscallInterface defines how processes interact with Ring 0.
type SyscallInterface interface {
	ExecSyscall(req SyscallRequest) SyscallResponse
}

// ErrUnauthorized indicates a process tried to exceed its permissions.
var ErrUnauthorized = fmt.Errorf("kernel panic: unauthorized syscall attempt")
