package kernel

import (
	"context"
	"fmt"
	"log"
	"sync"

	"github.com/google/uuid"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// SharedBuffer represents a block of memory accessible by multiple processes.
type SharedBuffer struct {
	Name string
	Data []byte
	Mu   sync.Mutex
}

// MicroKernel is the Ring-0 overseer of the Oricli-Alpha OS.
type MicroKernel struct {
	processes     map[ProcessID]*AgentProcess
	sharedRegions map[string]*SharedBuffer
	syscallCount  map[ProcessID]int
	memory        *service.MemoryBridge
	ghost         *service.GhostClusterService
	precog        *service.MetacogDaemon
	Safety        *SafetyFramework
	mu            sync.RWMutex
}

// NewMicroKernel boots up the Hive OS core with a Precog scheduler and Safety Framework.
func NewMicroKernel(mem *service.MemoryBridge, ghost *service.GhostClusterService, precog *service.MetacogDaemon, safety *SafetyFramework) *MicroKernel {
	return &MicroKernel{
		processes:     make(map[ProcessID]*AgentProcess),
		sharedRegions: make(map[string]*SharedBuffer),
		syscallCount:  make(map[ProcessID]int),
		memory:        mem,
		ghost:         ghost,
		precog:        precog,
		Safety:        safety,
	}
}

// SpawnProcess registers and starts a new agent process, after Precog and Safety assessment.
func (k *MicroKernel) SpawnProcess(profile service.AgentProfile, initialTokens float64, intentPlan string) (ProcessID, error) {
	// 1. SAFETY CHECK: DEFCON & PID Limits
	if k.Safety != nil {
		if !k.Safety.CheckClearance(Defcon3) {
			return "", fmt.Errorf("kernel reject: DEFCON level %d prevents spawning new processes", k.Safety.Level)
		}
		
		k.mu.RLock()
		activeCount := len(k.processes)
		k.mu.RUnlock()
		
		if activeCount >= k.Safety.GetMaxPIDs() {
			return "", fmt.Errorf("kernel reject: maximum active processes reached (%d)", activeCount)
		}
	}

	// 2. PRE-CRIME ASSESSMENT
	if k.precog != nil {
		risk, reason := k.precog.AssessPlan(context.Background(), intentPlan)
		if risk > 0.7 {
			return "", fmt.Errorf("kernel reject: high risk score (%.2f). Reason: %s", risk, reason)
		}
		log.Printf("[Kernel] Plan verified by Precog (Risk: %.2f).", risk)
	}

	k.mu.Lock()
	defer k.mu.Unlock()

	proc, err := NewAgentProcess(profile, initialTokens)
	if err != nil {
		return "", fmt.Errorf("kernel failed to alloc process: %w", err)
	}

	k.processes[proc.PID] = proc
	proc.State = StateReady

	log.Printf("[Kernel] Spawned Process %s (Profile: %s, Tokens: %.2f)", proc.PID, profile.Name, initialTokens)

	return proc.PID, nil
}

// KillProcess forcefully terminates an agent process.
func (k *MicroKernel) KillProcess(pid ProcessID, reason string) error {
	k.mu.Lock()
	defer k.mu.Unlock()

	proc, exists := k.processes[pid]
	if !exists {
		return fmt.Errorf("process %s not found", pid)
	}

	proc.Terminate()
	proc.State = StateKilled
	log.Printf("[Kernel] KILLED Process %s. Reason: %s", pid, reason)

	delete(k.processes, pid)
	delete(k.syscallCount, pid)
	return nil
}

// GetProcess retrieves a process by PID.
func (k *MicroKernel) GetProcess(pid ProcessID) (*AgentProcess, bool) {
	k.mu.RLock()
	defer k.mu.RUnlock()
	proc, ok := k.processes[pid]
	return proc, ok
}

// Panic initiates an emergency shutdown of all agent activities.
func (k *MicroKernel) Panic(reason string) {
	log.Printf("[Kernel] !!! PANIC TRIGGERED !!! Reason: %s", reason)
	
	if k.Safety != nil {
		k.Safety.SetDefcon(Defcon1)
	}

	k.mu.Lock()
	for pid, proc := range k.processes {
		proc.Terminate()
		log.Printf("[Kernel] Emergency termination of PID %s", pid)
	}
	k.processes = make(map[ProcessID]*AgentProcess)
	k.mu.Unlock()
}

// ExecSyscall handles requests from AgentProcesses with dynamic throttling and safety enforcement.
func (k *MicroKernel) ExecSyscall(req SyscallRequest) SyscallResponse {
	// 1. SAFETY CHECK: Global Lock
	if k.Safety != nil && k.Safety.IsKernelLocked {
		return SyscallResponse{Success: false, Error: fmt.Errorf("kernel is locked (DEFCON 1)")}
	}

	var proc *AgentProcess
	var exists bool

	if req.PID == "KERNEL" {
		exists = true
		proc = nil 
	} else {
		k.mu.Lock()
		proc, exists = k.processes[req.PID]
		
		// 2. DYNAMIC THROTTLING
		k.syscallCount[req.PID]++
		count := k.syscallCount[req.PID]
		k.mu.Unlock()

		if !exists {
			return SyscallResponse{Success: false, Error: fmt.Errorf("invalid PID")}
		}

		if count > 100 { 
			log.Printf("[Kernel] THROTTLING Process %s: Syscall limit exceeded.", req.PID)
			k.KillProcess(req.PID, "Excessive syscall noise.")
			return SyscallResponse{Success: false, Error: fmt.Errorf("process terminated due to excessive syscalls")}
		}

		// 3. DEFCON Check for general Syscalls
		if k.Safety != nil && !k.Safety.CheckClearance(Defcon2) {
			return SyscallResponse{Success: false, Error: fmt.Errorf("syscall blocked by DEFCON %d", k.Safety.Level)}
		}

		// 4. Fee Evaluation
		if req.FeeOffer > 0 {
			k.mu.Lock()
			if proc.Tokens >= req.FeeOffer {
				proc.Tokens -= req.FeeOffer
			} else {
				k.mu.Unlock()
				return SyscallResponse{Success: false, Error: fmt.Errorf("insufficient funds for fee")}
			}
			k.mu.Unlock()
		}
	}

	// 5. Syscall Routing
	switch req.Call {
	case SysPanic:
		k.Panic("User or Agent initiated SysPanic")
		return SyscallResponse{Success: true}
	case SysSetDefcon:
		if req.PID != "KERNEL" {
			return SyscallResponse{Success: false, Error: fmt.Errorf("%w: only KERNEL can set DEFCON", ErrUnauthorized)}
		}
		level, _ := req.Args["level"].(int)
		k.Safety.SetDefcon(DefconLevel(level))
		return SyscallResponse{Success: true}
	case SysAllocGPU:
		if proc == nil && req.PID == "KERNEL" {
			return k.handleKernelAllocGPU(req)
		}
		return k.handleAllocGPU(proc, req)
	case SysQueryMemory:
		return k.handleQueryMemory(proc, req)
	case SysAllocSharedMem:
		return k.handleAllocSharedMem(proc, req)
	case SysMapSharedMem:
		return k.handleMapSharedMem(proc, req)
	case SysWriteSharedMem:
		return k.handleWriteSharedMem(proc, req)
	default:
		return SyscallResponse{Success: false, Error: fmt.Errorf("syscall not implemented")}
	}
}

func (k *MicroKernel) handleKernelAllocGPU(req SyscallRequest) SyscallResponse {
	// Internal allocations also check Defcon
	if k.Safety != nil && !k.Safety.CheckClearance(Defcon4) {
		return SyscallResponse{Success: false, Error: fmt.Errorf("autonomic GPU allocation blocked by DEFCON %d", k.Safety.Level)}
	}

	gpuType, _ := req.Args["gpu_type"].(string)
	count, _ := req.Args["count"].(int)
	
	// Check financial cap (simulated $2.50 per pod)
	if k.Safety != nil && !k.Safety.AuthorizeSpend(float64(count)*2.50) {
		return SyscallResponse{Success: false, Error: fmt.Errorf("budget exceeded")}
	}

	log.Printf("[Kernel] Ring 0 allocating %d x %s", count, gpuType)
	return SyscallResponse{
		Success: true,
		Data:    fmt.Sprintf("Kernel-Provisioned ghost cluster %s", uuid.New().String()[:8]),
	}
}

func (k *MicroKernel) handleAllocGPU(proc *AgentProcess, req SyscallRequest) SyscallResponse {
	// 1. DEFCON Check: Only allowed in DEFCON 4+
	if k.Safety != nil && !k.Safety.CheckClearance(Defcon4) {
		return SyscallResponse{Success: false, Error: fmt.Errorf("GPU allocation blocked by DEFCON %d", k.Safety.Level)}
	}

	// 2. Profile check
	allowed, reason := k.ProfileAllowed(proc.Profile, "hardware", "alloc_gpu")
	if !allowed {
		return SyscallResponse{Success: false, Error: fmt.Errorf("%w: %s", ErrUnauthorized, reason)}
	}

	// 3. Budget Check
	count, _ := req.Args["count"].(int)
	if k.Safety != nil && !k.Safety.AuthorizeSpend(float64(count)*2.50) {
		return SyscallResponse{Success: false, Error: fmt.Errorf("budget exceeded")}
	}

	gpuType, _ := req.Args["gpu_type"].(string)
	log.Printf("[Kernel] Process %s allocating %d x %s", proc.PID, count, gpuType)
	return SyscallResponse{
		Success: true,
		Data:    fmt.Sprintf("Provisioned ghost cluster %s", uuid.New().String()[:8]),
		FeePaid: req.FeeOffer,
	}
}

func (k *MicroKernel) handleQueryMemory(proc *AgentProcess, req SyscallRequest) SyscallResponse {
	allowed, reason := k.ProfileAllowed(proc.Profile, "memory", "read")
	if !allowed {
		return SyscallResponse{Success: false, Error: fmt.Errorf("%w: %s", ErrUnauthorized, reason)}
	}

	keyword, _ := req.Args["keyword"].(string)
	log.Printf("[Kernel] Process %s querying memory for '%s'", proc.PID, keyword)

	return SyscallResponse{
		Success: true,
		Data:    "Memory slice returned",
		FeePaid: req.FeeOffer,
	}
}

func (k *MicroKernel) handleWriteSharedMem(proc *AgentProcess, req SyscallRequest) SyscallResponse {
	name, _ := req.Args["name"].(string)
	sourcePath, _ := req.Args["path"].(string)

	k.mu.RLock()
	region, exists := k.sharedRegions[name]
	k.mu.RUnlock()

	if !exists {
		return SyscallResponse{Success: false, Error: fmt.Errorf("region not found")}
	}

	data, err := proc.Sandbox.ReadFile(sourcePath)
	if err != nil {
		return SyscallResponse{Success: false, Error: fmt.Errorf("failed to read source: %w", err)}
	}

	region.Mu.Lock()
	for i := range region.Data {
		region.Data[i] = 0
	}
	copy(region.Data, data)
	region.Mu.Unlock()

	return SyscallResponse{Success: true}
}

func (k *MicroKernel) handleAllocSharedMem(proc *AgentProcess, req SyscallRequest) SyscallResponse {
	name, _ := req.Args["name"].(string)
	size, _ := req.Args["size"].(int)

	if size <= 0 || size > 1024*1024*100 {
		return SyscallResponse{Success: false, Error: fmt.Errorf("invalid memory size")}
	}

	k.mu.Lock()
	if _, exists := k.sharedRegions[name]; exists {
		k.mu.Unlock()
		return SyscallResponse{Success: false, Error: fmt.Errorf("region already exists")}
	}

	region := &SharedBuffer{
		Name: name,
		Data: make([]byte, size),
	}
	k.sharedRegions[name] = region
	k.mu.Unlock()

	log.Printf("[Kernel] Process %s allocated shared region '%s' (%d bytes)", proc.PID, name, size)
	return SyscallResponse{Success: true, Data: name}
}

func (k *MicroKernel) handleMapSharedMem(proc *AgentProcess, req SyscallRequest) SyscallResponse {
	name, _ := req.Args["name"].(string)
	targetPath, _ := req.Args["path"].(string)

	k.mu.RLock()
	region, exists := k.sharedRegions[name]
	k.mu.RUnlock()

	if !exists {
		return SyscallResponse{Success: false, Error: fmt.Errorf("region not found")}
	}

	err := proc.Sandbox.WriteFile(targetPath, region.Data)
	if err != nil {
		return SyscallResponse{Success: false, Error: fmt.Errorf("mount failed: %w", err)}
	}

	log.Printf("[Kernel] Process %s mapped shared region '%s' to %s", proc.PID, name, targetPath)
	return SyscallResponse{Success: true}
}

func (k *MicroKernel) ProfileAllowed(p service.AgentProfile, module, op string) (bool, string) {
	for _, blocked := range p.BlockedModules {
		if blocked == module {
			return false, "module blocked"
		}
	}
	return true, ""
}
