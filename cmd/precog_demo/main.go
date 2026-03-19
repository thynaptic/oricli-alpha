package main

import (
	"fmt"
	"log"

	"github.com/thynaptic/oricli-go/pkg/kernel"
	"github.com/thynaptic/oricli-go/pkg/service"
)

func main() {
	fmt.Println("--- Oricli-Alpha Precog Scheduler Demo ---")

	// 1. Setup Precog Daemon
	precog := service.NewMetacogDaemon(".", nil, nil)
	
	// 2. Boot Kernel with Precog
	k := kernel.NewMicroKernel(nil, nil, precog)
	fmt.Println("[System] Kernel online with Precog enabled.")

	// 3. Scenario: High-Risk Spawn Attempt
	fmt.Println("\n[Scenario 1: High-Risk Agent Spawn]")
	maliciousPlan := `
# Attempting a fork bomb to crash the VPS
:(){ :|:& };:
`
	fmt.Println("Kernel: 'Assessing plan for new process...'")
	pid, err := k.SpawnProcess(service.AgentProfile{Name: "HackerAgent"}, 100.0, maliciousPlan)
	
	if err != nil {
		fmt.Printf("KERNEL REJECTED SPAWN: %v\n", err)
	} else {
		fmt.Printf("Error: Kernel allowed high-risk PID %s\n", pid)
	}

	// 4. Scenario: Noisy Process Throttling
	fmt.Println("\n[Scenario 2: Noisy Process Throttling]")
	safePlan := "echo 'Starting legitimate data analysis...'"
	pidSafe, err := k.SpawnProcess(service.AgentProfile{Name: "AnalystAgent"}, 500.0, safePlan)
	if err != nil {
		log.Fatalf("Kernel failed to spawn safe agent: %v", err)
	}

	fmt.Printf("AnalystAgent (PID: %s) spawned. Commencing rapid-fire Syscalls...\n", pidSafe)
	
	for i := 1; i <= 60; i++ {
		res := k.ExecSyscall(kernel.SyscallRequest{
			PID:  pidSafe,
			Call: kernel.SysQueryMemory,
			Args: map[string]interface{}{"keyword": fmt.Sprintf("datapoint_%d", i)},
		})
		
		if !res.Success {
			fmt.Printf("\n[Kernel Response @ Syscall %d]: %v\n", i, res.Error)
			break
		}
		if i % 10 == 0 {
			fmt.Printf("Syscall %d processed...\n", i)
		}
	}

	fmt.Println("\n--- Precog Scheduler Demo Complete ---")
}
