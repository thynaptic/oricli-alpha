package main

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/kernel"
	"github.com/thynaptic/oricli-go/pkg/service"
)

func main() {
	fmt.Println("--- Oricli-Alpha Micro-Kernel OS Demo ---")

	// 1. Boot Kernel
	// (Simulating without actual memory/ghost instances for the demo structure)
	k := kernel.NewMicroKernel(nil, nil)
	fmt.Println("[System] Kernel booted successfully. Ring 0 active.")

	// 2. Spawn an Agent Process
	profile := service.AgentProfile{
		Name: "DataScientist_v1",
		BlockedModules: []string{"memory"}, // We will block memory to test Kernel security
	}
	
	pid, err := k.SpawnProcess(profile, 100.0) // Grant 100 Tokens
	if err != nil {
		log.Fatalf("Kernel Panic: %v", err)
	}

	fmt.Printf("\n[Agent %s] Booting up inside Gosh Sandbox...\n", pid)

	// 3. Agent requests GPU via Syscall (with a bribe)
	fmt.Printf("[Agent %s] Syscall: Requesting 1x RTX 4090. Offering 15 tokens for priority.\n", pid)
	res := k.ExecSyscall(kernel.SyscallRequest{
		PID:      pid,
		Call:     kernel.SysAllocGPU,
		Args:     map[string]interface{}{"gpu_type": "RTX 4090", "count": 1},
		FeeOffer: 15.0,
	})
	
	if res.Success {
		fmt.Printf("[Kernel] Syscall SUCCESS. Agent charged %.2f tokens. Data: %v\n", res.FeePaid, res.Data)
	}

	// 4. Agent attempts unauthorized memory read
	fmt.Printf("\n[Agent %s] Syscall: Querying Memory Graph for 'project_secrets'.\n", pid)
	res = k.ExecSyscall(kernel.SyscallRequest{
		PID:  pid,
		Call: kernel.SysQueryMemory,
		Args: map[string]interface{}{"keyword": "project_secrets"},
	})

	if !res.Success {
		fmt.Printf("[Kernel] Syscall DENIED. Error: %v\n", res.Error)
		
		// 5. Kernel reacts to unauthorized attempt
		fmt.Println("[Kernel] Security Violation Detected. Initiating Process Termination...")
		k.KillProcess(pid, "Attempted unauthorized memory read.")
	}

	fmt.Println("\n--- OS Demo Complete ---")
}
