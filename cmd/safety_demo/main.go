package main

import (
	"fmt"

	"github.com/thynaptic/oricli-go/pkg/kernel"
	"github.com/thynaptic/oricli-go/pkg/service"
)

func main() {
	fmt.Println("--- Oricli-Alpha Autonomous Safety Framework Demo ---")

	// 1. Setup Safety Framework with a tight budget ($10.00)
	safety := kernel.NewSafetyFramework(10.0)
	k := kernel.NewMicroKernel(nil, nil, nil, safety)
	fmt.Println("[System] Kernel booted at DEFCON 5. Daily Budget: $10.00")

	// 2. Spawn an Agent Process
	profile := service.AgentProfile{Name: "ResourceAgent"}
	pid, _ := k.SpawnProcess(profile, 1000.0, "echo 'Testing safety guardrails...'")

	// SCENARIO 1: Normal Allocation
	fmt.Println("\n[Scenario 1: Normal GPU Allocation]")
	fmt.Printf("[Agent %s] Requesting 1x GPU ($2.50)...\n", pid)
	res := k.ExecSyscall(kernel.SyscallRequest{
		PID:  pid,
		Call: kernel.SysAllocGPU,
		Args: map[string]interface{}{"gpu_type": "RTX 4090", "count": 1},
	})
	if res.Success {
		fmt.Println("[Kernel] Syscall SUCCESS. Budget remaining: $7.50")
	}

	// SCENARIO 2: Budget Exhaustion
	fmt.Println("\n[Scenario 2: Budget Hard-Cap]")
	fmt.Printf("[Agent %s] Requesting 4x GPUs ($10.00). Total would be $12.50.\n", pid)
	res = k.ExecSyscall(kernel.SyscallRequest{
		PID:  pid,
		Call: kernel.SysAllocGPU,
		Args: map[string]interface{}{"gpu_type": "RTX 4090", "count": 4},
	})
	if !res.Success {
		fmt.Printf("[Kernel] Syscall BLOCKED: %v\n", res.Error)
	}

	// SCENARIO 3: Panic Button (DEFCON 1)
	fmt.Println("\n[Scenario 3: Big Red Button (SysPanic)]")
	fmt.Println("[User] Triggering SysPanic Syscall...")
	k.ExecSyscall(kernel.SyscallRequest{
		PID:  "KERNEL", // Kernel-level panic
		Call: kernel.SysPanic,
	})

	fmt.Println("\n[Scenario 4: Post-Panic Quarantine]")
	fmt.Printf("[Agent %s] Attempting any syscall after panic...\n", pid)
	res = k.ExecSyscall(kernel.SyscallRequest{
		PID:  pid,
		Call: kernel.SysQueryMemory,
		Args: map[string]interface{}{"keyword": "test"},
	})
	if !res.Success {
		fmt.Printf("[Kernel] Syscall DENIED: %v\n", res.Error)
	}

	fmt.Println("\n--- Safety Framework Demo Complete ---")
}
